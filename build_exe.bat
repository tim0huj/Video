@echo off
setlocal

echo ============================================
echo  Video OCR Extractor - Windows EXE Builder
echo ============================================
echo.

where python >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python not found on PATH. Install Python 3.10 or 3.11 first.
    exit /b 1
)

if not exist ".venv_build" (
    echo [0/3] Creating build virtual environment...
    python -m venv .venv_build
)
call .venv_build\Scripts\activate.bat

echo [1/3] Installing dependencies...
python -m pip install --upgrade pip >nul
pip install -r requirements.txt
pip install -r requirements-build.txt

echo.
echo [2/3] Running PyInstaller (this can take a few minutes)...
pyinstaller --noconfirm --clean ^
  --name VideoOCRExtractor ^
  --onedir ^
  --add-data "app.py;." ^
  --add-data ".streamlit;.streamlit" ^
  --collect-all streamlit ^
  --collect-all streamlit_drawable_canvas ^
  --collect-all cv2 ^
  --collect-all pandas ^
  --collect-metadata streamlit ^
  --hidden-import pytesseract ^
  --hidden-import openpyxl ^
  --hidden-import fpdf ^
  launcher.py

if errorlevel 1 (
    echo.
    echo [ERROR] PyInstaller build failed. See the log above.
    call .venv_build\Scripts\deactivate.bat
    exit /b 1
)

echo.
echo [3/3] Build complete!
echo   Executable : dist\VideoOCRExtractor\VideoOCRExtractor.exe
echo.
echo IMPORTANT: OCR requires the Tesseract engine, which is NOT bundled
echo automatically. Do ONE of the following before running the exe:
echo   1. Install Tesseract-OCR for Windows system-wide:
echo      https://github.com/UB-Mannheim/tesseract/wiki
echo   2. Copy your Tesseract-OCR install folder into
echo      dist\VideoOCRExtractor\ and rename it to "tesseract"
echo      (so dist\VideoOCRExtractor\tesseract\tesseract.exe exists)
echo   3. Set a TESSERACT_CMD environment variable pointing at tesseract.exe
echo.
echo Distribute the WHOLE "dist\VideoOCRExtractor" folder, not just the .exe.

call .venv_build\Scripts\deactivate.bat
endlocal
pause
