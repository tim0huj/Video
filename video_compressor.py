# -*- coding: utf-8 -*-
"""
Video Compressor for OCR  v1.0
────────────────────────────────
OCR용 영상 압축 도구 (오디오 제거 + 해상도/용량 축소)

- ffmpeg 내장 (imageio-ffmpeg) → 별도 설치 불필요
- 파일을 exe 아이콘 위로 드래그해도 실행됨
- 출력: 원본과 같은 폴더에  <원본이름>_compressed.mp4
"""

import os
import re
import sys
import queue
import threading
import subprocess
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

try:
    import imageio_ffmpeg
    FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
except Exception:
    FFMPEG = "ffmpeg"  # 폴백: PATH에 있는 ffmpeg 사용

VIDEO_EXTS = (".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v", ".wmv", ".ts")

# Windows에서 콘솔 창 숨김 플래그
CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0

RES_OPTIONS = {
    "1280px (720p급, 권장)": 1280,
    "1920px (1080p급, 작은 글자용)": 1920,
    "960px (더 작게)": 960,
    "원본 해상도 유지": 0,
}

TIME_RE = re.compile(r"time=(\d+):(\d+):(\d+(?:\.\d+)?)")
DUR_RE = re.compile(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)")


def hms_to_sec(h, m, s):
    return int(h) * 3600 + int(m) * 60 + float(s)


def probe_duration(path: str) -> float:
    """ffmpeg stderr에서 영상 길이(초)를 파싱."""
    try:
        proc = subprocess.run(
            [FFMPEG, "-hide_banner", "-i", path],
            capture_output=True, text=True, errors="replace",
            creationflags=CREATE_NO_WINDOW,
        )
        m = DUR_RE.search(proc.stderr or "")
        if m:
            return hms_to_sec(*m.groups())
    except Exception:
        pass
    return 0.0


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Video Compressor for OCR  v1.0")
        self.geometry("640x560")
        self.minsize(600, 520)
        self.resizable(True, True)

        self.files: list[str] = []
        self.msg_q: queue.Queue = queue.Queue()
        self.worker: threading.Thread | None = None
        self.stop_flag = threading.Event()
        self.current_proc: subprocess.Popen | None = None

        self._build_ui()

        # exe 아이콘 위로 드래그된 파일 처리
        argv_files = [a for a in sys.argv[1:]
                      if os.path.isfile(a) and a.lower().endswith(VIDEO_EXTS)]
        if argv_files:
            self.add_files(argv_files)

        self.after(100, self._poll_queue)

    # ── UI ────────────────────────────────
    def _build_ui(self):
        pad = dict(padx=10, pady=4)

        # 파일 목록
        frm_files = ttk.LabelFrame(self, text=" 1. 영상 파일 ")
        frm_files.pack(fill="both", expand=False, **pad)

        self.listbox = tk.Listbox(frm_files, height=6, selectmode="extended")
        self.listbox.pack(fill="both", expand=True, side="left", padx=(8, 0), pady=8)
        sb = ttk.Scrollbar(frm_files, command=self.listbox.yview)
        sb.pack(side="left", fill="y", pady=8)
        self.listbox.config(yscrollcommand=sb.set)

        btns = ttk.Frame(frm_files)
        btns.pack(side="left", fill="y", padx=8, pady=8)
        ttk.Button(btns, text="파일 추가", command=self.pick_files).pack(fill="x", pady=2)
        ttk.Button(btns, text="선택 제거", command=self.remove_selected).pack(fill="x", pady=2)
        ttk.Button(btns, text="전체 비우기", command=self.clear_files).pack(fill="x", pady=2)

        # 설정
        frm_opt = ttk.LabelFrame(self, text=" 2. 압축 설정 ")
        frm_opt.pack(fill="x", **pad)

        row1 = ttk.Frame(frm_opt); row1.pack(fill="x", padx=8, pady=4)
        ttk.Label(row1, text="해상도(가로 기준):").pack(side="left")
        self.res_var = tk.StringVar(value=list(RES_OPTIONS.keys())[0])
        ttk.Combobox(row1, textvariable=self.res_var,
                     values=list(RES_OPTIONS.keys()),
                     state="readonly", width=28).pack(side="left", padx=6)

        row2 = ttk.Frame(frm_opt); row2.pack(fill="x", padx=8, pady=4)
        ttk.Label(row2, text="압축 강도 (CRF):").pack(side="left")
        self.crf_var = tk.IntVar(value=26)
        self.crf_scale = ttk.Scale(row2, from_=20, to=32, variable=self.crf_var,
                                   command=lambda v: self.crf_lbl.config(
                                       text=f"{int(float(v))}"))
        self.crf_scale.pack(side="left", fill="x", expand=True, padx=6)
        self.crf_lbl = ttk.Label(row2, text="26", width=3)
        self.crf_lbl.pack(side="left")
        ttk.Label(row2, text="(낮을수록 고화질·큰 용량)").pack(side="left", padx=4)

        row3 = ttk.Frame(frm_opt); row3.pack(fill="x", padx=8, pady=4)
        self.audio_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(row3, text="오디오 제거 (OCR엔 불필요)",
                        variable=self.audio_var).pack(side="left")

        row4 = ttk.Frame(frm_opt); row4.pack(fill="x", padx=8, pady=4)
        ttk.Label(row4, text="구간 자르기(선택)  시작(초):").pack(side="left")
        self.t_start = tk.StringVar(value="")
        ttk.Entry(row4, textvariable=self.t_start, width=8).pack(side="left", padx=4)
        ttk.Label(row4, text="종료(초):").pack(side="left")
        self.t_end = tk.StringVar(value="")
        ttk.Entry(row4, textvariable=self.t_end, width=8).pack(side="left", padx=4)
        ttk.Label(row4, text="비워두면 전체").pack(side="left", padx=4)

        # 실행
        frm_run = ttk.LabelFrame(self, text=" 3. 실행 ")
        frm_run.pack(fill="both", expand=True, **pad)

        rbtns = ttk.Frame(frm_run); rbtns.pack(fill="x", padx=8, pady=6)
        self.run_btn = ttk.Button(rbtns, text="▶  압축 시작", command=self.start)
        self.run_btn.pack(side="left", fill="x", expand=True)
        self.stop_btn = ttk.Button(rbtns, text="■ 중지", command=self.stop,
                                   state="disabled")
        self.stop_btn.pack(side="left", padx=(6, 0))

        self.prog = ttk.Progressbar(frm_run, maximum=100)
        self.prog.pack(fill="x", padx=8, pady=(0, 4))
        self.status = ttk.Label(frm_run, text="대기 중")
        self.status.pack(anchor="w", padx=8)

        self.log = tk.Text(frm_run, height=8, state="disabled",
                           font=("Consolas", 9))
        self.log.pack(fill="both", expand=True, padx=8, pady=6)

    # ── 파일 관리 ─────────────────────────
    def pick_files(self):
        paths = filedialog.askopenfilenames(
            title="영상 파일 선택",
            filetypes=[("Video", " ".join("*" + e for e in VIDEO_EXTS)),
                       ("All files", "*.*")])
        if paths:
            self.add_files(paths)

    def add_files(self, paths):
        for p in paths:
            p = os.path.abspath(p)
            if p not in self.files:
                self.files.append(p)
                size_mb = os.path.getsize(p) / 1024 / 1024
                self.listbox.insert("end", f"{os.path.basename(p)}  ({size_mb:,.0f} MB)")

    def remove_selected(self):
        for idx in reversed(self.listbox.curselection()):
            self.listbox.delete(idx)
            del self.files[idx]

    def clear_files(self):
        self.listbox.delete(0, "end")
        self.files.clear()

    # ── 실행 제어 ─────────────────────────
    def start(self):
        if not self.files:
            messagebox.showwarning("알림", "먼저 영상 파일을 추가하세요.")
            return
        try:
            ts = float(self.t_start.get()) if self.t_start.get().strip() else None
            te = float(self.t_end.get()) if self.t_end.get().strip() else None
        except ValueError:
            messagebox.showerror("오류", "구간 시작/종료는 숫자(초)로 입력하세요.")
            return
        if ts is not None and te is not None and te <= ts:
            messagebox.showerror("오류", "종료 시간이 시작 시간보다 커야 합니다.")
            return

        self.stop_flag.clear()
        self.run_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        self.prog["value"] = 0

        cfg = dict(
            width=RES_OPTIONS[self.res_var.get()],
            crf=int(self.crf_var.get()),
            no_audio=self.audio_var.get(),
            t_start=ts, t_end=te,
            files=list(self.files),
        )
        self.worker = threading.Thread(target=self._work, args=(cfg,), daemon=True)
        self.worker.start()

    def stop(self):
        self.stop_flag.set()
        proc = self.current_proc
        if proc and proc.poll() is None:
            try:
                proc.kill()
            except Exception:
                pass
        self._log("사용자 요청으로 중지했습니다.")

    # ── 워커 스레드 ───────────────────────
    def _work(self, cfg):
        total = len(cfg["files"])
        done = 0
        for src in cfg["files"]:
            if self.stop_flag.is_set():
                break
            name = os.path.basename(src)
            base, _ = os.path.splitext(src)
            dst = base + "_compressed.mp4"

            duration = probe_duration(src)
            if cfg["t_start"] is not None or cfg["t_end"] is not None:
                seg_start = cfg["t_start"] or 0.0
                seg_end = cfg["t_end"] if cfg["t_end"] is not None else duration
                seg_len = max(seg_end - seg_start, 0.001)
            else:
                seg_len = duration or 0.001

            cmd = [FFMPEG, "-hide_banner", "-y"]
            if cfg["t_start"] is not None:
                cmd += ["-ss", str(cfg["t_start"])]
            cmd += ["-i", src]
            if cfg["t_end"] is not None:
                cmd += ["-to", str(cfg["t_end"] - (cfg["t_start"] or 0.0))]
            if cfg["width"]:
                cmd += ["-vf", f"scale={cfg['width']}:-2"]
            cmd += ["-c:v", "libx264", "-crf", str(cfg["crf"]),
                    "-preset", "fast", "-pix_fmt", "yuv420p",
                    "-movflags", "+faststart"]
            if cfg["no_audio"]:
                cmd += ["-an"]
            else:
                cmd += ["-c:a", "aac", "-b:a", "96k"]
            cmd += [dst]

            self._status(f"[{done + 1}/{total}] {name} 압축 중...")
            self._log(f"▶ {name}")

            try:
                self.current_proc = subprocess.Popen(
                    cmd, stderr=subprocess.PIPE, stdout=subprocess.DEVNULL,
                    text=True, errors="replace", bufsize=1,
                    creationflags=CREATE_NO_WINDOW,
                )
                for line in self.current_proc.stderr:
                    if self.stop_flag.is_set():
                        break
                    m = TIME_RE.search(line)
                    if m:
                        cur = hms_to_sec(*m.groups())
                        file_pct = min(cur / seg_len, 1.0)
                        overall = (done + file_pct) / total * 100
                        self._prog(overall)
                self.current_proc.wait()
                rc = self.current_proc.returncode
            except Exception as e:
                self._log(f"  ✗ 실행 오류: {e}")
                rc = -1
            finally:
                self.current_proc = None

            if self.stop_flag.is_set():
                if os.path.exists(dst):
                    try:
                        os.remove(dst)
                    except OSError:
                        pass
                break

            if rc == 0 and os.path.exists(dst):
                src_mb = os.path.getsize(src) / 1024 / 1024
                dst_mb = os.path.getsize(dst) / 1024 / 1024
                ratio = (1 - dst_mb / src_mb) * 100 if src_mb else 0
                self._log(f"  ✓ 완료: {os.path.basename(dst)}  "
                          f"{src_mb:,.0f} MB → {dst_mb:,.0f} MB  (-{ratio:.0f}%)")
            else:
                self._log(f"  ✗ 실패 (종료 코드 {rc}) — 원본 코덱/경로를 확인하세요.")

            done += 1
            self._prog(done / total * 100)

        self.msg_q.put(("done", None))

    # ── 스레드 → UI 메시지 ────────────────
    def _log(self, text):
        self.msg_q.put(("log", text))

    def _status(self, text):
        self.msg_q.put(("status", text))

    def _prog(self, pct):
        self.msg_q.put(("prog", pct))

    def _poll_queue(self):
        try:
            while True:
                kind, payload = self.msg_q.get_nowait()
                if kind == "log":
                    self.log.config(state="normal")
                    self.log.insert("end", payload + "\n")
                    self.log.see("end")
                    self.log.config(state="disabled")
                elif kind == "status":
                    self.status.config(text=payload)
                elif kind == "prog":
                    self.prog["value"] = payload
                elif kind == "done":
                    self.status.config(text="완료 — 원본과 같은 폴더에 "
                                            "_compressed.mp4 로 저장됨")
                    self.run_btn.config(state="normal")
                    self.stop_btn.config(state="disabled")
        except queue.Empty:
            pass
        self.after(100, self._poll_queue)


if __name__ == "__main__":
    App().mainloop()
