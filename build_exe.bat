@echo off
echo === B30 Controller - Build EXE ===
echo.

echo [1/3] Upgrading pip...
py -m pip install --upgrade pip

echo [2/3] Installing dependencies...
py -m pip install pyinstaller openpyxl pymodbus Pillow

echo [3/3] Building EXE (onefile, all libs inside)...
if exist dist rmdir /s /q dist
if exist build rmdir /s /q build
if exist B30Controller.spec del /q B30Controller.spec

py -m PyInstaller --noconfirm --clean --onefile --windowed --name B30Controller --icon B30.ico --hidden-import pymodbus.client --hidden-import openpyxl --collect-submodules openpyxl gui_controller_modern.py

if errorlevel 1 (
  echo.
  echo Build FAILED - see errors above
  pause
  exit /b 1
)

echo.
echo ===============================
echo Build OK: D:\Projects\dist\B30Controller.exe
echo Icon: B30.ico embedded
echo Size about 80-120 MB is normal
echo Test: dist\B30Controller.exe
echo For installer: open installer.iss in Inno Setup and Compile
echo ===============================
pause
