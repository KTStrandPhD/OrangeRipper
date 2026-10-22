@echo off
echo ========================================
echo Packaging OrangeRipper for Windows...
echo ========================================

:: Clean old build artifacts, PyInstaller cache, and bytecode
echo Cleaning old build artifacts and caches...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist __pycache__ rmdir /s /q __pycache__
if exist ripperCore\__pycache__ rmdir /s /q ripperCore\__pycache__
if exist gui\__pycache__ rmdir /s /q gui\__pycache__
if exist services\__pycache__ rmdir /s /q services\__pycache__

:: Check if the local virtual environment exists
if not exist ".venv\Scripts\pyinstaller.exe" (
    echo [NOTICE] PyInstaller not found in .venv. Setting up virtual environment and dependencies...
    if not exist ".venv" python -m venv .venv
    call .venv\Scripts\pip install --upgrade pip
)

:: Install all project requirements + pyinstaller + discid + PyQt6
echo Installing/verifying dependencies...
if exist "requirements.txt" (
    call .venv\Scripts\pip install -r requirements.txt
)
call .venv\Scripts\pip install pyinstaller discid PyQt6

:: Run PyInstaller with explicit module/path collection and app icon
.venv\Scripts\pyinstaller main.py ^
    --noconfirm ^
    --onedir ^
    --windowed ^
    --name OrangeRipper ^
    --icon=assets\app.ico ^
    --add-data "assets;assets" ^
    --clean ^
    --paths . ^
    --hidden-import=ripperCore.ripper ^
    --hidden-import=ripperCore.encoder ^
    --collect-submodules ripperCore ^
    --collect-all ripperCore ^
    --collect-all gui

:: Forcefully copy discid.dll straight into dist\OrangeRipper\
echo Injecting discid.dll into build output...
if exist "discid.dll" (
    copy /y "discid.dll" "dist\OrangeRipper\"
) else if exist ".venv\Lib\site-packages\discid\discid.dll" (
    copy /y ".venv\Lib\site-packages\discid\discid.dll" "dist\OrangeRipper\"
) else if exist "bin\discid.dll" (
    copy /y "bin\discid.dll" "dist\OrangeRipper\"
) else (
    echo [!] WARNING: Could not find discid.dll to inject!
)

:: Also place a copy inside dist\OrangeRipper\discid
if not exist "dist\OrangeRipper\discid" mkdir "dist\OrangeRipper\discid"
if exist "discid.dll" (
    copy /y "discid.dll" "dist\OrangeRipper\discid\"
) else if exist ".venv\Lib\site-packages\discid\discid.dll" (
    copy /y ".venv\Lib\site-packages\discid\discid.dll" "dist\OrangeRipper\discid\"
)

:: Ensure bin folder binaries (ffmpeg.exe, lame.exe, libmpg123-0.dll, flac.exe) are copied to dist\OrangeRipper\bin
echo Injecting bin/ binaries into build output...
if not exist "dist\OrangeRipper\bin" mkdir "dist\OrangeRipper\bin"

if exist "bin\ffmpeg.exe" (
    copy /y "bin\ffmpeg.exe" "dist\OrangeRipper\bin\"
    echo [+] Injected ffmpeg.exe into dist\OrangeRipper\bin\
) else (
    echo [!] WARNING: Could not find bin\ffmpeg.exe to inject!
)

if exist "bin\lame.exe" (
    copy /y "bin\lame.exe" "dist\OrangeRipper\bin\"
    echo [+] Injected lame.exe into dist\OrangeRipper\bin\
) else (
    echo [!] WARNING: Could not find bin\lame.exe to inject!
)

if exist "bin\libmpg123-0.dll" (
    copy /y "bin\libmpg123-0.dll" "dist\OrangeRipper\bin\"
    echo [+] Injected libmpg123-0.dll into dist\OrangeRipper\bin\
) else (
    echo [!] WARNING: Could not find bin\libmpg123-0.dll to inject!
)

if exist "bin\flac.exe" (
    copy /y "bin\flac.exe" "dist\OrangeRipper\bin\"
    echo [+] Injected flac.exe into dist\OrangeRipper\bin\
) else (
    echo [!] WARNING: Could not find bin\flac.exe to inject!
)

:: Automatically run install.py to check dependencies and generate shortcuts
echo Running installation and shortcut setup...
python install.py

echo ========================================
echo Packaging and setup complete!
echo ========================================
pause
