@echo off
set PFX_FILE=%1
set PFX_FILE_PWD=
set /P PFX_FILE_PWD=PFX File Password: %=%
if %errorlevel% neq 0 exit /b %errorlevel%

@echo Building EXE
pyinstaller --noconfirm "packaging\batch-media-compressor.spec"
if %errorlevel% neq 0 exit /b %errorlevel%

@echo Signing EXE
"C:\Program Files (x86)\Windows Kits\10\App Certification Kit\signtool.exe" sign /f %PFX_FILE% /p "%PFX_FILE_PWD%" /t http://timestamp.sectigo.com /v "dist\Batch Media Compressor.exe"
if %errorlevel% neq 0 exit /b %errorlevel%

@echo Building Setup File
"C:\Program Files (x86)\Inno Setup 6\iscc.exe" "packaging\win_setup.iss"
if %errorlevel% neq 0 exit /b %errorlevel%

echo Done
