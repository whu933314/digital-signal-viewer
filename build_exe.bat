@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
rem Digital Signal Viewer build script (PyInstaller); version comes from APP_VERSION in signal_viewer.py. Needs the plotkit\ package next to signal_viewer.py.
rem   build_exe.bat          -> --onefile --windowed, output dist\SignalViewer.exe
rem   build_exe.bat onedir   -> --onedir  --windowed, output dist\SignalViewer\SignalViewer.exe

set MODE=onefile
if /i "%~1"=="onedir" set MODE=onedir

python -c "import PyInstaller" 2>nul
if errorlevel 1 (
  echo [build_exe] PyInstaller not found. Run: pip install pyinstaller
  exit /b 1
)
if not exist README.md (
  echo [build_exe] README.md not found next to signal_viewer.py
  exit /b 1
)
if not exist README.en.md (
  echo [build_exe] README.en.md not found next to signal_viewer.py
  exit /b 1
)
if not exist assets\SignalViewer.ico (
  echo [build_exe] assets\SignalViewer.ico not found. Run: python tools\make_icon.py
  exit /b 1
)
if not exist plotkit\__init__.py (
  echo [build_exe] plotkit\ package not found next to signal_viewer.py
  exit /b 1
)

python -c "import tkinterdnd2" >nul 2>&1 || echo [build_exe] WARNING: tkinterdnd2 not installed - drag and drop will be unavailable in the exe. Run: pip install tkinterdnd2
rem Windows version resource (Properties > Details: File/Product version = APP_VERSION) from tools\make_version_file.py
python tools\make_version_file.py build_version_info.txt
if errorlevel 1 (
  echo [build_exe] tools\make_version_file.py FAILED
  exit /b 1
)

set EXCL=--exclude-module PyQt5 --exclude-module PyQt6 --exclude-module PySide2 --exclude-module PySide6 --exclude-module IPython --exclude-module scipy --exclude-module pandas

echo [build_exe] mode=%MODE%
python -m PyInstaller --noconfirm --clean --%MODE% --windowed --name SignalViewer --add-data "README.md;." --add-data "README.en.md;." --add-data "assets\SignalViewer-256.png;assets" --icon assets\SignalViewer.ico --version-file build_version_info.txt --hidden-import plotkit --collect-submodules plotkit %EXCL% signal_viewer.py
if errorlevel 1 (
  echo [build_exe] build FAILED
  exit /b 1
)
if /i "%MODE%"=="onedir" (
  echo [build_exe] done: dist\SignalViewer\SignalViewer.exe
) else (
  echo [build_exe] done: dist\SignalViewer.exe
)
endlocal
