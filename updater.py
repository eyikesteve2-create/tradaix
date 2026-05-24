"""
updater.py — Système de mise à jour automatique TradAIx via GitHub
Au démarrage, vérifie si une nouvelle version est disponible et met à jour les fichiers.
"""

import os
import sys
import json
import shutil
import requests
import zipfile
import io
from datetime import datetime

# ─────────────────────────────────────────────
# CONFIGURATION — À MODIFIER SELON TON REPO
# ─────────────────────────────────────────────
GITHUB_USER    = "eyikesteve2-create"           # Ton nom d'utilisateur GitHub
GITHUB_REPO    = "tradaix"           # Nom du dépôt GitHub
GITHUB_BRANCH  = "main"              # Branche principale
VERSION_FILE   = "version.json"      # Fichier de version local
TIMEOUT        = 10                  # Secondes avant abandon

# Fichiers à mettre à jour (les autres sont ignorés)
FICHIERS_MAJ = [
    "app.py", "db.py", "function.py", "messagerie.py",
    "tradaix_auth.py", "dashboard.py", "taches_email.py",
    "notes.py", "inspinote.py", "Splash.py", "launcher_exe.py",
]

# ─────────────────────────────────────────────
# URLS GITHUB
# ─────────────────────────────────────────────
def url_version():
    return f"https://raw.githubusercontent.com/{GITHUB_USER}/{GITHUB_REPO}/{GITHUB_BRANCH}/version.json"

def url_fichier(nom):
    return f"https://raw.githubusercontent.com/{GITHUB_USER}/{GITHUB_REPO}/{GITHUB_BRANCH}/{nom}"


# ─────────────────────────────────────────────
# LIRE LA VERSION LOCALE
# ─────────────────────────────────────────────
def lire_version_locale() -> str:
    dossier = os.path.dirname(os.path.abspath(sys.argv[0]))
    chemin  = os.path.join(dossier, VERSION_FILE)
    try:
        with open(chemin, "r") as f:
            data = json.load(f)
            return data.get("version", "0.0.0")
    except:
        return "0.0.0"

def sauver_version_locale(version: str):
    dossier = os.path.dirname(os.path.abspath(sys.argv[0]))
    chemin  = os.path.join(dossier, VERSION_FILE)
    with open(chemin, "w") as f:
        json.dump({
            "version":      version,
            "derniere_maj": datetime.now().strftime("%Y-%m-%d %H:%M"),
        }, f, indent=2)


# ─────────────────────────────────────────────
# VÉRIFIER LA VERSION DISTANTE
# ─────────────────────────────────────────────
def lire_version_distante() -> dict | None:
    try:
        r = requests.get(url_version(), timeout=TIMEOUT)
        if r.status_code == 200:
            return r.json()
    except:
        pass
    return None


# ─────────────────────────────────────────────
# COMPARER LES VERSIONS
# ─────────────────────────────────────────────
def version_plus_recente(v_locale: str, v_distante: str) -> bool:
    try:
        loc  = tuple(int(x) for x in v_locale.split("."))
        dist = tuple(int(x) for x in v_distante.split("."))
        return dist > loc
    except:
        return False


# ─────────────────────────────────────────────
# TÉLÉCHARGER ET REMPLACER UN FICHIER
# ─────────────────────────────────────────────
def mettre_a_jour_fichier(nom: str, dossier: str) -> bool:
    try:
        r = requests.get(url_fichier(nom), timeout=TIMEOUT)
        if r.status_code == 200:
            chemin = os.path.join(dossier, nom)
            # Backup de l'ancien fichier
            if os.path.exists(chemin):
                shutil.copy2(chemin, chemin + ".bak")
            with open(chemin, "wb") as f:
                f.write(r.content)
            return True
    except:
        pass
    return False


# ─────────────────────────────────────────────
# MISE À JOUR COMPLÈTE
# ─────────────────────────────────────────────
def verifier_et_mettre_a_jour(callback=None) -> dict:
    """
    Vérifie et applique la mise à jour.
    callback(message) est appelé pour afficher la progression.
    Retourne {"maj": True/False, "version": "x.x.x", "message": "..."}
    """
    def log(msg):
        if callback:
            callback(msg)

    dossier    = os.path.dirname(os.path.abspath(sys.argv[0]))
    v_locale   = lire_version_locale()

    log(f"Version actuelle : {v_locale}")
    log("Vérification des mises à jour...")

    # Récupérer version distante
    info_distante = lire_version_distante()
    if not info_distante:
        return {"maj": False, "version": v_locale, "message": "Impossible de vérifier (pas de connexion)."}

    v_distante = info_distante.get("version", "0.0.0")
    notes_maj  = info_distante.get("notes", "")

    if not version_plus_recente(v_locale, v_distante):
        return {"maj": False, "version": v_locale, "message": f"TradAIx est à jour (v{v_locale})."}

    # Nouvelle version disponible
    log(f"Nouvelle version disponible : v{v_distante}")
    log(f"Notes : {notes_maj}")
    log("Téléchargement en cours...")

    fichiers_maj   = 0
    fichiers_erreur = []

    for nom in FICHIERS_MAJ:
        log(f"Mise à jour : {nom}...")
        if mettre_a_jour_fichier(nom, dossier):
            fichiers_maj += 1
        else:
            fichiers_erreur.append(nom)

    # Mettre à jour version.json local
    sauver_version_locale(v_distante)

    msg = f"Mise à jour v{v_distante} appliquée ({fichiers_maj} fichiers)."
    if fichiers_erreur:
        msg += f" Échec : {', '.join(fichiers_erreur)}"

    log(msg)
    return {
        "maj":      True,
        "version":  v_distante,
        "notes":    notes_maj,
        "message":  msg,
        "erreurs":  fichiers_erreur,
    }
