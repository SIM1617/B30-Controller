@echo off
chcp 65001 >nul
echo === B30 Controller - Secure Build ===
echo.

echo [1/4] Installing tools...
py -m pip install --upgrade pip
py -m pip install pyinstaller openpyxl pymodbus pyarmor Pillow --quiet

echo.
echo [2/4] Obfuscating source with PyArmor...
if exist dist_obf rmdir /s /q dist_obf
pyarmor gen gui_controller_modern.py -O dist_obf
if errorlevel 1 (
  echo [!] PyArmor failed - building without obfuscation
  if not exist dist_obf mkdir dist_obf
  copy /y gui_controller_modern.py dist_obf\gui_controller_modern.py >nul
) else (
  echo [+] Obfuscation OK
)

echo.
echo [3/4] Building EXE with PyInstaller (onefile, windowed)...
if exist dist rmdir /s /q dist
if exist build rmdir /s /q build
if exist B30Controller.spec del /q B30Controller.spec

py -m PyInstaller --noconfirm --clean --onefile --windowed --name B30Controller --icon B30.ico --hidden-import pymodbus.client --hidden-import openpyxl --collect-submodules openpyxl dist_obf\gui_controller_modern.py

if errorlevel 1 (
  echo [X] Build FAILED
  pause
  exit /b 1
)

echo.
echo ===============================
echo [+] Build OK: D:\Projects\dist\B30Controller.exe
echo     Icon B30.ico embedded
echo     Size 80-120 MB is normal (all libs inside)
echo.
echo Test: dist\B30Controller.exe
echo Installer: Open installer.iss in Inno Setup and Compile
echo ===============================
pause
