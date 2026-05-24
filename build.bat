@echo off
title TradAIx - Compilation EXE
color 0A

echo.
echo  =========================================
echo    TradAIx Enterprise - Compilation EXE
echo  =========================================
echo.

cd /d C:\Users\EVERMATE\Documents\TRADAIX

echo  [1/7] Nettoyage...
if exist dist   rmdir /s /q dist
if exist build  rmdir /s /q build
echo  OK

echo.
echo  [2/7] Mise a jour PyInstaller...
pip install pyinstaller pywebview --upgrade --quiet
echo  OK

echo.
echo  [3/7] Compilation EXE...
pyinstaller tradaix.spec --clean --noconfirm

echo.
echo  [4/7] Copie des fichiers Python...
if exist "dist\TradAIx\TradAIx.exe" (
    copy .env                      dist\TradAIx\ /Y >nul
    copy serviceAccountKey.json    dist\TradAIx\ /Y >nul
    copy logo_tradaix_mascotte.png dist\TradAIx\ /Y >nul
    copy TradAIx.ico               dist\TradAIx\ /Y >nul
    copy app.py                    dist\TradAIx\ /Y >nul
    copy function.py               dist\TradAIx\ /Y >nul
    copy tradaix_auth.py           dist\TradAIx\ /Y >nul
    copy dashboard.py              dist\TradAIx\ /Y >nul
    copy messagerie.py             dist\TradAIx\ /Y >nul
    copy taches_email.py           dist\TradAIx\ /Y >nul
    copy db.py                     dist\TradAIx\ /Y >nul
    copy notes.py                  dist\TradAIx\ /Y >nul
    copy inspinote.py              dist\TradAIx\ /Y >nul
    copy Splash.py                 dist\TradAIx\ /Y >nul
    echo  Fichiers Python copies.

    echo.
    echo  [5/7] Copie du dossier inspinote...
    if exist inspinote (
        xcopy inspinote dist\TradAIx\inspinote\ /E /I /Y >nul
        echo  Dossier inspinote copie.
    ) else (
        mkdir dist\TradAIx\inspinote
        echo  Dossier inspinote cree vide.
    )

    echo.
    echo  [6/7] Creation de l'environnement Python embarque...
    python -m venv dist\TradAIx\venv
    echo  Installation des dependances dans le venv...
    dist\TradAIx\venv\Scripts\pip install --upgrade pip --quiet
    dist\TradAIx\venv\Scripts\pip install ^
        streamlit ^
        langchain-groq ^
        langchain-community ^
        langchain-text-splitters ^
        pypdf ^
        python-docx ^
        python-dotenv ^
        requests ^
        pillow ^
        plotly ^
        pandas ^
        pywebview ^
        firebase-admin ^
        --quiet
    echo  Environnement Python embarque OK.

    echo.
    echo  [7/7] Verification finale...
    echo  Contenu de dist\TradAIx\ :
    dir dist\TradAIx\ /b

    echo.
    echo  =========================================
    echo    SUCCESS ! TradAIx.exe est pret !
    echo  =========================================
    echo.
    echo  Dossier a distribuer : TRADAIX\dist\TradAIx\
    echo  Copiez ce dossier sur n'importe quelle machine Windows.
    echo  Aucune installation requise sur la machine cible.
    echo.
) else (
    echo.
    echo  ERREUR : TradAIx.exe introuvable dans dist\TradAIx\
    echo  Verifiez les logs de compilation ci-dessus.
)

pause
