import streamlit as st
import hashlib
from datetime import datetime
from db import get_db

# ─────────────────────────────────────────────
# HASH MOT DE PASSE
# ─────────────────────────────────────────────
def hasher_mdp(mdp: str) -> str:
    sel = "TradAIx_2026_Cameroun"
    return hashlib.sha256(f"{sel}{mdp}{sel}".encode()).hexdigest()

# ─────────────────────────────────────────────
# INSCRIPTION
# ─────────────────────────────────────────────
def inscrire_utilisateur(nom: str, email: str, mdp: str) -> dict:
    try:
        db  = get_db()
        res = db.table("utilisateurs").select("email").eq("email", email).execute()
        if res.data:
            return {"succes": False, "erreur": "Cet email est déjà utilisé."}
        db.table("utilisateurs").insert({
            "email":    email,
            "nom":      nom,
            "mdp_hash": hasher_mdp(mdp),
            "role":     "membre",
            "en_ligne": True,
        }).execute()
        return {"succes": True, "nom": nom, "email": email, "uid": email}
    except Exception as e:
        return {"succes": False, "erreur": f"Erreur : {e}"}

# ─────────────────────────────────────────────
# CONNEXION
# ─────────────────────────────────────────────
def connecter_utilisateur(email: str, mdp: str) -> dict:
    try:
        db  = get_db()
        res = db.table("utilisateurs").select("*").eq("email", email).execute()
        if not res.data:
            return {"succes": False, "erreur": "Aucun compte trouvé avec cet email."}
        user = res.data[0]
        if user["mdp_hash"] != hasher_mdp(mdp):
            return {"succes": False, "erreur": "Mot de passe incorrect."}
        db.table("utilisateurs").update({"en_ligne": True}).eq("email", email).execute()
        return {"succes": True, "nom": user["nom"], "email": email, "uid": email}
    except Exception as e:
        return {"succes": False, "erreur": f"Erreur : {e}"}

# ─────────────────────────────────────────────
# DÉCONNEXION
# ─────────────────────────────────────────────
def deconnecter_utilisateur():
    email = st.session_state.get("user_email")
    if email:
        try:
            get_db().table("utilisateurs").update({"en_ligne": False}).eq("email", email).execute()
        except:
            pass
    for cle in ["user_email", "user_nom", "user_uid", "connecte"]:
        st.session_state.pop(cle, None)

# ─────────────────────────────────────────────
# CSS
# ─────────────────────────────────────────────
def inject_css_auth():
    st.markdown("""
    <style>
    .auth-logo {
        text-align: center;
        font-family: Arial Black, sans-serif;
        font-size: 2.4em;
        font-weight: 900;
        color: #CC0000;
        margin-bottom: 4px;
    }
    .auth-subtitle {
        text-align: center;
        color: #888;
        font-size: 13px;
        margin-bottom: 28px;
    }
    .user-badge {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        background: #FFF0F0;
        border: 1px solid #FFCCCC;
        border-radius: 20px;
        padding: 6px 14px;
        font-size: 13px;
        color: #CC0000;
        font-weight: 500;
    }
    .avatar-circle {
        width: 28px; height: 28px;
        border-radius: 50%;
        background: #CC0000;
        color: white;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        font-size: 12px;
        font-weight: 700;
    }
    </style>
    """, unsafe_allow_html=True)

# ─────────────────────────────────────────────
# PAGE AUTHENTIFICATION
# ─────────────────────────────────────────────
def page_authentification():
    inject_css_auth()
    col_l, col_c, col_r = st.columns([1, 2, 1])
    with col_c:
        st.markdown('<div class="auth-logo">Trad<span style="color:#1E3A8A">AI</span>x</div>',
                    unsafe_allow_html=True)
        st.markdown('<div class="auth-subtitle">Intelligence Collaborative</div>',
                    unsafe_allow_html=True)
        onglet = st.radio("Mode", ["🔐 Se connecter", "✨ Créer un compte"],
                          horizontal=True, label_visibility="collapsed")
        st.markdown("---")

        if onglet == "🔐 Se connecter":
            email = st.text_input("📧 Email", placeholder="votre@email.com", key="login_email")
            mdp   = st.text_input("🔒 Mot de passe", type="password", key="login_mdp")
            if st.button("Se connecter", use_container_width=True, type="primary"):
                if not email or not mdp:
                    st.error("Veuillez remplir tous les champs.")
                else:
                    with st.spinner("Connexion..."):
                        res = connecter_utilisateur(email.strip(), mdp)
                    if res["succes"]:
                        st.session_state.connecte   = True
                        st.session_state.user_email = res["email"]
                        st.session_state.user_nom   = res["nom"]
                        st.session_state.user_uid   = res["uid"]
                        st.success(f"Bienvenue, {res['nom']} !")
                        st.rerun()
                    else:
                        st.error(res["erreur"])
        else:
            nom  = st.text_input("👤 Nom complet", placeholder="Jean Dupont", key="reg_nom")
            email= st.text_input("📧 Email", placeholder="votre@email.com", key="reg_email")
            mdp  = st.text_input("🔒 Mot de passe", type="password",
                                  placeholder="Minimum 6 caractères", key="reg_mdp")
            mdp2 = st.text_input("🔒 Confirmer", type="password", key="reg_mdp2")
            if st.button("Créer mon compte", use_container_width=True, type="primary"):
                if not all([nom, email, mdp, mdp2]):
                    st.error("Veuillez remplir tous les champs.")
                elif mdp != mdp2:
                    st.error("Les mots de passe ne correspondent pas.")
                elif len(mdp) < 6:
                    st.error("Mot de passe trop court (minimum 6 caractères).")
                else:
                    with st.spinner("Création du compte..."):
                        res = inscrire_utilisateur(nom.strip(), email.strip(), mdp)
                    if res["succes"]:
                        st.session_state.connecte   = True
                        st.session_state.user_email = res["email"]
                        st.session_state.user_nom   = res["nom"]
                        st.session_state.user_uid   = res["uid"]
                        st.success(f"Compte créé ! Bienvenue, {nom} 🎉")
                        st.rerun()
                    else:
                        st.error(res["erreur"])

# ─────────────────────────────────────────────
# BADGE SIDEBAR
# ─────────────────────────────────────────────
def afficher_badge_utilisateur():
    nom      = st.session_state.get("user_nom", "Utilisateur")
    email    = st.session_state.get("user_email", "")
    initiale = nom[0].upper() if nom else "U"
    with st.sidebar:
        st.markdown(f"""
        <div class="user-badge">
            <div class="avatar-circle">{initiale}</div>
            <div>
                <div style="font-weight:600">{nom}</div>
                <div style="font-size:11px;color:#888">{email}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("")
        if st.button("🚪 Se déconnecter", use_container_width=True):
            deconnecter_utilisateur()
            st.rerun()

# ─────────────────────────────────────────────
# VÉRIFICATION SESSION
# ─────────────────────────────────────────────
def verifier_session() -> bool:
    if st.session_state.get("connecte"):
        return True
    page_authentification()
    return False
