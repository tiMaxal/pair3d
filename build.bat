@echo off
setlocal

echo.
echo === pair3d Build Script ===
echo Options:
echo   build.bat exe    - Build Windows .exe with PyInstaller
echo   build.bat deb    - Build Debian .deb package (requires WSL or Linux)
echo   build.bat wheel  - Build Python wheel (.whl) and sdist
echo   build.bat clean  - Remove build artifacts
echo.

if "%1"=="exe" (
    echo Building pair3d.exe with PyInstaller...
    pyinstaller --clean pair3d.spec
    goto :EOF
)

if "%1"=="deb" (
    echo Building Debian package...
    python setup.py --command-packages=stdeb.command bdist_deb
    goto :EOF
)

if "%1"=="wheel" (
    echo Building wheel and sdist...
    python -m build
    goto :EOF
)

if "%1"=="clean" (
    echo Cleaning up...
    rmdir /s /q build dist __pycache__ deb_dist >nul 2>&1
    del /q *.spec *.egg-info >nul 2>&1
    goto :EOF
)

echo No valid option provided. Use: exe | deb | wheel | clean
