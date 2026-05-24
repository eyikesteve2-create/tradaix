import subprocess
import sys
import os
import socket
import time
import threading
import webview

PORT = 8501
URL  = f"http://localhost:{PORT}"

# ─────────────────────────────────────────────
# TROUVER LE BON PYTHON (venv embarqué ou système)
# ─────────────────────────────────────────────
def trouver_python() -> str:
    dossier = os.path.dirname(os.path.abspath(sys.argv[0]))

    # 1. Python du venv embarqué dans le dossier de l'exe
    venv_python = os.path.join(dossier, "venv", "Scripts", "python.exe")
    if os.path.exists(venv_python):
        return venv_python

    # 2. Python courant (si lancé via python)
    if os.path.exists(sys.executable):
        return sys.executable

    # 3. Python installé sur le système
    candidats = [
        r"C:\Users\EVERMATE\AppData\Local\Programs\Python\Python311\python.exe",
        r"C:\Python311\python.exe",
        r"C:\Python312\python.exe",
        r"C:\Python313\python.exe",
        "python",
        "python3",
    ]
    for p in candidats:
        try:
            res = subprocess.run([p, "--version"], capture_output=True, timeout=3)
            if res.returncode == 0:
                return p
        except:
            continue
    return None


# ─────────────────────────────────────────────
# RACCOURCI BUREAU
# ─────────────────────────────────────────────
def creer_raccourci_bureau():
    try:
        bureau    = os.path.join(os.path.expanduser("~"), "Desktop")
        raccourci = os.path.join(bureau, "TradAIx.lnk")
        if os.path.exists(raccourci):
            return
        dossier = os.path.dirname(os.path.abspath(sys.argv[0]))
        exe     = os.path.join(dossier, "TradAIx.exe")
        icone   = os.path.join(dossier, "TradAIx.ico")
        ps = f"""
$s = New-Object -comObject WScript.Shell
$l = $s.CreateShortcut("{raccourci}")
$l.TargetPath = "{exe}"
$l.WorkingDirectory = "{dossier}"
$l.Description = "TradAIx — Intelligence Collaborative"
$l.IconLocation = "{icone}"
$l.Save()
"""
        subprocess.run(
            ["powershell", "-Command", ps],
            capture_output=True,
            creationflags=subprocess.CREATE_NO_WINDOW,
            timeout=10
        )
    except Exception:
        pass


# ─────────────────────────────────────────────
# VÉRIFIER SI STREAMLIT TOURNE DÉJÀ
# ─────────────────────────────────────────────
def port_libre() -> bool:
    try:
        s = socket.create_connection(("localhost", PORT), timeout=1)
        s.close()
        return False
    except:
        return True

def attendre_streamlit(timeout: int = 90) -> bool:
    debut = time.time()
    while time.time() - debut < timeout:
        try:
            s = socket.create_connection(("localhost", PORT), timeout=1)
            s.close()
            return True
        except:
            time.sleep(0.5)
    return False


# ─────────────────────────────────────────────
# LANCER STREAMLIT EN ARRIÈRE-PLAN
# ─────────────────────────────────────────────
def lancer_streamlit():
    if not port_libre():
        return None

    dossier    = os.path.dirname(os.path.abspath(sys.argv[0]))
    app_py     = os.path.join(dossier, "app.py")
    python_exe = trouver_python()

    if not python_exe or not os.path.exists(app_py):
        return None

    cmd = [
        python_exe, "-m", "streamlit", "run", app_py,
        "--server.port",                    str(PORT),
        "--server.headless",                "true",
        "--server.address",                 "localhost",
        "--browser.gatherUsageStats",       "false",
        "--theme.primaryColor",             "#CC0000",
        "--theme.backgroundColor",          "#FFFFFF",
        "--theme.secondaryBackgroundColor", "#F0F2F6",
        "--theme.textColor",                "#1E293B",
    ]

    return subprocess.Popen(
        cmd,
        cwd=dossier,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NO_WINDOW
    )


# ─────────────────────────────────────────────
# THREAD : LANCER STREAMLIT PUIS CHARGER L'URL
# ─────────────────────────────────────────────
def demarrer_app(window):
    lancer_streamlit()
    if attendre_streamlit(timeout=90):
        window.load_url(URL)
    else:
        window.load_html("""
        <html><body style='font-family:Arial;text-align:center;padding:60px;background:#fff'>
            <h2 style='color:#CC0000'>Erreur de demarrage</h2>
            <p>TradAIx n'a pas pu demarrer.<br>
            Verifiez que le dossier venv est bien present.</p>
        </body></html>
        """)


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
def main():
    threading.Thread(target=creer_raccourci_bureau, daemon=True).start()

    window = webview.create_window(
        title        = "TradAIx",
        url          = "about:blank",
        width        = 1280,
        height       = 800,
        min_size     = (900, 600),
        resizable    = True,
        text_select  = True,
        confirm_close= True,
    )

    threading.Thread(
        target=demarrer_app,
        args=(window,),
        daemon=True
    ).start()

    webview.start(
        debug        = False,
        private_mode = False,
        storage_path = os.path.join(os.path.expanduser("~"), ".tradaix_cache"),
    )

if __name__ == "__main__":
    main()
