# 🎬 Video OCR Extractor v2.1

비디오의 특정 영역을 지정하여 초 단위로 텍스트/숫자를 추출하고 표로 저장하는 앱입니다.
Streamlit Cloud 배포 없이, **Windows에서 .exe 하나로 완전히 로컬에서** 실행할 수 있습니다.

---

## ✨ 주요 기능

- 🎥 비디오 업로드 (MP4, MOV, AVI, WebM)
- 🖱️ 드래그로 OCR 영역 선택 (캔버스 인터페이스)
- 🔢 숫자 특화 OCR (LCD 디스플레이, 계기판 등)
- 📊 결과를 **CSV / Excel / PDF / TSV** 로 내보내기
- 🔍 실시간 전처리 미리보기
- 💻 인터넷 없이 로컬에서 동작 (업로드 파일은 서버로 전송되지 않음)

---

## 🖥️ Windows .exe로 빌드하기 (로컬 환경)

패키징된 `.exe`는 브라우저에서 열리는 로컬 웹 앱(`http://localhost:8501`)을 실행합니다.
비디오/영상 데이터는 실행 중인 PC 안에서만 처리되며 외부로 전송되지 않습니다.

### 1) 사전 준비 (빌드 PC에만 필요)

- Windows 10/11
- [Python 3.10 또는 3.11](https://www.python.org/downloads/) (PATH에 추가 체크)
- [Tesseract-OCR for Windows](https://github.com/UB-Mannheim/tesseract/wiki) 설치
  - 설치 중 "Additional language data" 에서 **Korean** 체크(한국어 인식 필요 시)
  - 기본 설치 경로: `C:\Program Files\Tesseract-OCR\tesseract.exe`

### 2) 빌드

이 저장소를 내려받은 뒤, 폴더에서 더블클릭하거나 명령 프롬프트로 실행:

```bat
build_exe.bat
```

내부적으로 다음을 수행합니다:
1. 빌드 전용 가상환경(`.venv_build`) 생성
2. `requirements.txt` + PyInstaller 설치
3. `launcher.py`를 PyInstaller로 패키징 (Streamlit/캔버스 컴포넌트 리소스 포함)

빌드가 끝나면 다음 위치에 실행 파일이 생성됩니다.

```
dist\VideoOCRExtractor\VideoOCRExtractor.exe
```

> **폴더 전체(`dist\VideoOCRExtractor`)를 배포하세요.** `.exe` 하나만 옮기면
> 함께 생성된 리소스 파일이 없어 실행되지 않습니다.

### 3) 실행

`VideoOCRExtractor.exe`를 더블클릭하면 콘솔 창이 뜨고 잠시 후 기본 브라우저에
앱이 자동으로 열립니다 (`http://localhost:8501`). 앱을 종료하려면 콘솔 창을 닫으세요.

### Tesseract 인식 우선순위

앱은 실행 시 다음 순서로 Tesseract 엔진을 자동으로 찾습니다.

1. 환경변수 `TESSERACT_CMD` (tesseract.exe의 전체 경로)
2. exe 옆의 `tesseract\tesseract.exe` 폴더 (Tesseract-OCR 설치 폴더를 통째로 복사 후 `tesseract`로 이름 변경)
3. 기본 설치 경로 `C:\Program Files\Tesseract-OCR\tesseract.exe`
4. 시스템 PATH에 등록된 `tesseract`

찾지 못하면 앱 상단에 경고가 표시되고 OCR 실행 버튼이 비활성화됩니다.

### 문제 해결

- **Windows Defender/백신 경고**: PyInstaller로 만든 exe는 서명이 없어 오탐될 수 있습니다.
  회사/개인 환경에서 신뢰할 수 있는 배포망을 통해서만 공유하세요.
- **실행 시 콘솔이 바로 꺼짐**: 명령 프롬프트에서 직접 실행해 에러 로그를 확인하세요.
- **포트 충돌**: 이미 8501 포트를 쓰는 앱이 있다면 종료 후 다시 실행하세요.

---

## 💻 개발 환경에서 직접 실행 (스크립트로)

### Windows
```bat
pip install -r requirements.txt
:: Tesseract-OCR for Windows 설치 필요: https://github.com/UB-Mannheim/tesseract/wiki
streamlit run app.py
```

### macOS
```bash
brew install tesseract tesseract-lang
pip install -r requirements.txt
streamlit run app.py
```

### Linux (Ubuntu/Debian)
```bash
sudo apt-get install tesseract-ocr tesseract-ocr-kor tesseract-ocr-eng
pip install -r requirements.txt
streamlit run app.py
```

---

## ☁️ Streamlit Cloud 배포 (선택 사항)

1. 이 레포를 GitHub에 Push
2. [share.streamlit.io](https://share.streamlit.io) 접속
3. **New app** → Repository 선택
4. Main file path: `app.py`
5. **Deploy** 클릭 (`packages.txt`가 시스템 패키지를 자동 설치)

---

## 📁 파일 구조

```
video-ocr-extractor/
├── app.py                  # 메인 Streamlit 앱
├── launcher.py             # .exe 빌드용 진입점 (streamlit CLI 부팅)
├── build_exe.bat           # Windows .exe 빌드 스크립트 (PyInstaller)
├── requirements.txt        # Python 런타임 패키지
├── requirements-build.txt  # 빌드 전용 패키지 (PyInstaller)
├── packages.txt            # 시스템 패키지 (Streamlit Cloud용)
├── .streamlit/
│   └── config.toml         # 테마 및 서버 설정
└── README.md
```

---

## ⚙️ OCR 설정 가이드

| 설정 | 권장값 | 용도 |
|------|--------|------|
| 언어 | 영어 | 숫자 추출 시 정확도 높음 |
| OCR 모드 | 숫자 위주 | 소수점·부호 포함 숫자 |
| 이미지 확대 | 3× | 작은 글씨 인식률 향상 |
| 전처리 | 반전+대비 | 밝은 LCD 디스플레이 |

---

## 📦 사용 라이브러리

- [Streamlit](https://streamlit.io) — UI 프레임워크
- [OpenCV](https://opencv.org) — 비디오 프레임 추출
- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) — 문자 인식 엔진
- [streamlit-drawable-canvas](https://github.com/andfanilo/streamlit-drawable-canvas) — 영역 선택
- [openpyxl](https://openpyxl.readthedocs.io) — Excel 생성
- [fpdf2](https://py-fpdf2.readthedocs.io) — PDF 생성
- [PyInstaller](https://pyinstaller.org) — Windows .exe 패키징
