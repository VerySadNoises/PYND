@echo off
chcp 65001 >nul
echo === Installation de l'environnement VN Engine ===
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo Python non detecte. Installation via winget...
    winget install --id Python.Python.3.13 -e --accept-source-agreements --accept-package-agreements
    if errorlevel 1 (
        echo [ERREUR] Installation automatique impossible.
        echo Installez Python manuellement : https://www.python.org/downloads/
        echo Cochez bien "Add Python to PATH" lors de l'installation.
        pause
        exit /b 1
    )
    echo Python installe. Relancez ce script pour continuer.
    pause
    exit /b 0
)

python -m ensurepip --upgrade >nul 2>&1
python -m pip install --upgrade pip
if errorlevel 1 (
    echo [ERREUR] pip introuvable. Assurez-vous que Python est installe et dans le PATH.
    pause
    exit /b 1
)

echo.
echo Installation des dependances...
pip install --upgrade -r requirements.txt
if errorlevel 1 (
    echo [ERREUR] L'installation a echoue.
    pause
    exit /b 1
)

echo.
echo Installation terminee.
pause
