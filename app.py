import streamlit as st
import os
import pandas as pd
import plotly.express as px
from PIL import Image
from dotenv import load_dotenv

from function      import preparer_moteur_ia, analyser_et_resoudre, extraire_taches_pour_dashboard
from messagerie    import module_messagerie
from tradaix_auth  import verifier_session, afficher_badge_utilisateur
from dashboard     import module_dashboard
from taches_email  import module_taches_email
from notes         import module_notes

# --- CONFIGURATION ---
load_dotenv()
st.set_page_config(page_title="TradAIx", layout="wide", page_icon="🤖")

st.markdown("""
    <style>
    .main-title { font-size: 2.8em; color: #1E3A8A; font-weight: bold; margin-bottom: 0px; }
    .stTabs [data-baseweb="tab-list"] { gap: 20px; }
    .report-box { padding: 20px; border-radius: 10px; background-color: #f0f2f6; border-left: 5px solid #1E3A8A; }
    </style>
""", unsafe_allow_html=True)

# --- SESSION STATE ---
if 'liste_taches'    not in st.session_state: st.session_state.liste_taches    = []
if 'messages'        not in st.session_state: st.session_state.messages        = []
if 'vectorstore'     not in st.session_state: st.session_state.vectorstore     = None
if 'dernier_rapport' not in st.session_state: st.session_state.dernier_rapport = None
if 'nb_fichiers'     not in st.session_state: st.session_state.nb_fichiers     = 1

# --- AUTHENTIFICATION ---
if not verifier_session():
    st.stop()

afficher_badge_utilisateur()

# --- EN-TÊTE ---
col_logo, col_title = st.columns([1, 5])
with col_logo:
    try:
        image = Image.open('logo_tradaix_mascotte.png')
        st.image(image, use_column_width=True)
    except Exception:
        st.info("📌 Logo TradAIx")

with col_title:
    nom_user = st.session_state.get("user_nom", "")
    st.markdown('<p class="main-title">TradAIx</p>', unsafe_allow_html=True)
    st.write(f"Bonjour **{nom_user}** — Solutions d'IA pour la gestion administrative et le suivi d'objectifs")

# --- ONGLETS ---
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "🔍 Analyse & Solutions",
    "💬 Chat Interactif",
    "📊 Dashboard & Objectifs",
    "📨 Messagerie",
    "📧 Tâches Email",
    "📓 Notes",
])

# ─────────────────────────────────────────────
# ONGLET 1 : ANALYSE
# ─────────────────────────────────────────────
with tab1:
    st.subheader("Analyse de Documents & Génération d'Actions")
    col_in, col_out = st.columns([1, 2])

    with col_in:
        col_titre, col_plus = st.columns([4, 1])
        with col_titre:
            st.markdown("**📂 Documents à analyser**")
        with col_plus:
            if st.button("➕", help="Ajouter un document (max 5)", use_container_width=True):
                if st.session_state.nb_fichiers < 5:
                    st.session_state.nb_fichiers += 1

        fichiers = []
        for i in range(st.session_state.nb_fichiers):
            col_up, col_del = st.columns([5, 1])
            with col_up:
                label = f"Document {i+1}" if st.session_state.nb_fichiers > 1 else "Charger un document (PDF, CSV, TXT)"
                f_up = st.file_uploader(label, type=["pdf","csv","txt"], key=f"uploader_{i}")
                if f_up:
                    fichiers.append(f_up)
            with col_del:
                if st.session_state.nb_fichiers > 1:
                    st.markdown("<br>", unsafe_allow_html=True)
                    if st.button("🗑️", key=f"del_up_{i}"):
                        st.session_state.nb_fichiers -= 1
                        st.rerun()

        if fichiers:
            st.success(f"✅ {len(fichiers)} fichier(s) : {', '.join([f.name for f in fichiers])}")

        st.markdown("---")
        question_analyser = st.text_input(
            "Que voulez-vous analyser ?",
            placeholder="Ex: Résume les points clés et liste les actions."
        )

        if st.button("🚀 Lancer l'Analyse", use_container_width=True, type="primary"):
            if fichiers and question_analyser:
                with st.spinner(f"Analyse de {len(fichiers)} document(s)..."):
                    temp_paths = []
                    for f_up in fichiers:
                        tp = f"temp_{f_up.name}"
                        with open(tp, "wb") as f:
                            f.write(f_up.getbuffer())
                        temp_paths.append(tp)

                    if len(temp_paths) == 1:
                        st.session_state.vectorstore = preparer_moteur_ia(temp_paths[0])
                    else:
                        vs_list = [preparer_moteur_ia(p) for p in temp_paths]
                        vs_principal = vs_list[0]
                        for vs in vs_list[1:]:
                            vs_principal.merge_from(vs)
                        st.session_state.vectorstore = vs_principal

                    rapport = analyser_et_resoudre(question_analyser, st.session_state.vectorstore)
                    st.session_state.dernier_rapport = rapport
                    nouvelles_taches = extraire_taches_pour_dashboard(rapport)
                    st.session_state.liste_taches.extend(nouvelles_taches)

                    for p in temp_paths:
                        try: os.remove(p)
                        except Exception: pass

                    st.success(f"✅ Analyse terminée ! ({len(fichiers)} document(s))")
            else:
                st.error("Veuillez charger au moins un fichier et poser une question.")

    with col_out:
        if st.session_state.dernier_rapport:
            st.markdown("### 📄 Rapport d'Expertise")
            st.markdown(
                f'<div class="report-box">{st.session_state.dernier_rapport}</div>',
                unsafe_allow_html=True
            )
        else:
            st.info("Le rapport d'analyse s'affichera ici après le traitement.")

# ─────────────────────────────────────────────
# ONGLET 2 : CHAT
# ─────────────────────────────────────────────
with tab2:
    st.subheader("Discutez avec vos documents")
    if st.session_state.vectorstore is None:
        st.warning("⚠️ Veuillez charger un document dans l'onglet 'Analyse' pour activer le chat.")
    else:
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
        if prompt := st.chat_input("Posez une question sur le document..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)
            with st.chat_message("assistant"):
                with st.spinner("TradAIx réfléchit..."):
                    reponse = analyser_et_resoudre(prompt, st.session_state.vectorstore)
                    st.markdown(reponse)
                    st.session_state.messages.append({"role": "assistant", "content": reponse})

# ─────────────────────────────────────────────
# ONGLET 3 : DASHBOARD
# ─────────────────────────────────────────────
with tab3:
    module_dashboard(
        current_user=st.session_state.user_email,
        liste_taches_analyse=st.session_state.liste_taches if st.session_state.liste_taches else None
    )

# ─────────────────────────────────────────────
# ONGLET 4 : MESSAGERIE
# ─────────────────────────────────────────────
with tab4:
    module_messagerie(st.session_state.user_email)

# ─────────────────────────────────────────────
# ONGLET 5 : TÂCHES EMAIL
# ─────────────────────────────────────────────
with tab5:
    module_taches_email(st.session_state.user_email)

# ─────────────────────────────────────────────
# ONGLET 6 : NOTES
# ─────────────────────────────────────────────
with tab6:
    module_notes(st.session_state.user_email)

# --- FOOTER ---
st.markdown("---")
st.caption("TradAIx © 2026 - Système intelligent sécurisé")
