import streamlit as st
import imaplib
import email
from email.header import decode_header
from datetime import datetime, timedelta
from dotenv import load_dotenv
from langchain_groq import ChatGroq
import json
import os
from db import get_db

load_dotenv()

# ─────────────────────────────────────────────
# SAUVEGARDE TÂCHE DANS SUPABASE
# ─────────────────────────────────────────────
def sauvegarder_tache(user_email: str, tache: dict):
    deadline_str  = tache.get("deadline","Aucune")
    deadline_date = None
    if "jour" in deadline_str.lower():
        try:
            nb = int(''.join(filter(str.isdigit, deadline_str)))
            deadline_date = (datetime.now()+timedelta(days=nb)).strftime("%Y-%m-%d")
        except:
            deadline_date = (datetime.now()+timedelta(days=7)).strftime("%Y-%m-%d")

    get_db().table("taches").insert({
        "tache":       tache.get("tache","Sans titre")[:60],
        "description": tache.get("description",""),
        "categorie":   "Importante",
        "priorite":    tache.get("priorite","Moyenne"),
        "statut":      "En attente de traitement",
        "deadline":    deadline_date,
        "delai_jours": 7,
        "assigne_a":   user_email,
        "cree_par":    user_email,
        "etoile":      False,
        "source":      "email",
    }).execute()

# ─────────────────────────────────────────────
# CONNEXION MAIL IMAP
# ─────────────────────────────────────────────
def detecter_serveur_imap(email_addr: str) -> str:
    domaine  = email_addr.split("@")[-1].lower()
    serveurs = {
        "gmail.com":   "imap.gmail.com",
        "yahoo.com":   "imap.mail.yahoo.com",
        "yahoo.fr":    "imap.mail.yahoo.com",
        "outlook.com": "imap-mail.outlook.com",
        "hotmail.com": "imap-mail.outlook.com",
        "live.com":    "imap-mail.outlook.com",
        "orange.fr":   "imap.orange.fr",
        "free.fr":     "imap.free.fr",
        "sfr.fr":      "imap.sfr.fr",
        "laposte.net": "imap.laposte.net",
    }
    return serveurs.get(domaine,"")

def connecter_boite_mail(email_addr, mot_de_passe, serveur_imap):
    try:
        mail = imaplib.IMAP4_SSL(serveur_imap)
        mail.login(email_addr, mot_de_passe)
        return mail
    except imaplib.IMAP4.error as e:
        st.error(f"❌ Erreur connexion mail : {e}")
        return None
    except Exception as e:
        st.error(f"❌ Erreur : {e}")
        return None

def lire_emails_non_lus(mail_conn, nb_max=10):
    emails = []
    try:
        mail_conn.select("INBOX")
        _, ids = mail_conn.search(None, "UNSEEN")
        ids_list = ids[0].split()[-nb_max:]
        for eid in ids_list:
            _, data = mail_conn.fetch(eid, "(RFC822)")
            msg = email.message_from_bytes(data[0][1])
            sujet_raw = decode_header(msg["Subject"])[0]
            sujet = (sujet_raw[0].decode(sujet_raw[1] or "utf-8")
                     if isinstance(sujet_raw[0], bytes) else sujet_raw[0])
            expediteur = msg.get("From","Inconnu")
            date_str   = msg.get("Date","")
            corps = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        try:
                            corps = part.get_payload(decode=True).decode("utf-8",errors="ignore")
                            break
                        except: pass
            else:
                try: corps = msg.get_payload(decode=True).decode("utf-8",errors="ignore")
                except: pass
            emails.append({
                "id": eid.decode(), "sujet": sujet,
                "expediteur": expediteur, "date": date_str,
                "corps": corps[:2000],
            })
    except Exception as e:
        st.error(f"Erreur lecture emails : {e}")
    return emails

# ─────────────────────────────────────────────
# EXTRACTION IA VIA GROQ
# ─────────────────────────────────────────────
def extraire_tache_depuis_email(email_data: dict) -> dict:
    llm = ChatGroq(
        api_key=os.getenv("GROQ_API_KEY"),
        model_name="llama-3.3-70b-versatile",
        temperature=0
    )
    prompt = f"""Analyse cet email et extrait une tâche structurée.
Email :
- Sujet : {email_data['sujet']}
- De : {email_data['expediteur']}
- Date : {email_data['date']}
- Contenu : {email_data['corps']}

Réponds UNIQUEMENT avec un JSON valide (sans markdown) :
{{
  "tache": "titre court de la tâche (max 60 caractères)",
  "description": "description détaillée",
  "priorite": "Haute|Moyenne|Basse",
  "deadline": "dans X jours ou Aucune",
  "assigne_a": "email si mentionné sinon Moi",
  "source": "email",
  "expediteur": "{email_data['expediteur']}"
}}"""
    try:
        reponse = llm.invoke(prompt)
        contenu = reponse.content.strip()
        if "```" in contenu:
            contenu = contenu.split("```")[1]
            if contenu.startswith("json"):
                contenu = contenu[4:]
        return json.loads(contenu.strip())
    except:
        return {
            "tache":       email_data["sujet"][:60],
            "description": email_data["corps"][:200],
            "priorite":    "Moyenne",
            "deadline":    "Aucune",
            "assigne_a":   "Moi",
            "source":      "email",
            "expediteur":  email_data["expediteur"],
        }

# ─────────────────────────────────────────────
# CSS
# ─────────────────────────────────────────────
def inject_css():
    st.markdown("""
    <style>
    .email-card { background:#fff; border-radius:10px; padding:14px 18px; margin-bottom:10px;
                  border-left:4px solid #1E3A8A; box-shadow:0 2px 6px rgba(0,0,0,0.07); }
    .email-sujet { font-weight:700; color:#1E3A8A; font-size:15px; }
    .email-meta  { font-size:12px; color:#888; margin-bottom:6px; }
    .email-corps { font-size:13px; color:#444; white-space:pre-wrap; max-height:100px; overflow:hidden; }
    .tache-preview { background:#f0f7ff; border-radius:8px; padding:10px 14px; margin-top:8px; font-size:13px; }
    .badge-haute   { background:#FFE0E0; color:#CC0000; padding:2px 8px; border-radius:10px; font-size:11px; }
    .badge-moyenne { background:#FFF3CD; color:#856404; padding:2px 8px; border-radius:10px; font-size:11px; }
    .badge-basse   { background:#D4EDDA; color:#155724; padding:2px 8px; border-radius:10px; font-size:11px; }
    </style>
    """, unsafe_allow_html=True)

def badge_priorite(p):
    cls = {"Haute":"badge-haute","Moyenne":"badge-moyenne","Basse":"badge-basse"}.get(p,"badge-moyenne")
    return f'<span class="{cls}">{p}</span>'

# ─────────────────────────────────────────────
# MODULE PRINCIPAL
# ─────────────────────────────────────────────
def module_taches_email(current_user: str):
    inject_css()
    st.markdown("### 📧 Créer des tâches depuis vos Emails")

    # Récupération des infos de connexion depuis la session (configurées ailleurs)
    email_addr   = current_user
    mot_de_passe = st.session_state.get("mail_mdp", os.getenv("MAIL_PASSWORD", ""))
    serveur      = st.session_state.get("mail_imap", detecter_serveur_imap(email_addr))

    col_nb, col_btn1, col_btn2 = st.columns([2, 2, 1])
    with col_nb:
        nb_emails = st.slider("Nombre d'emails à analyser", 1, 20, 5, key="nb_emails")
    with col_btn1:
        connecter = st.button("📬 Charger mes emails", use_container_width=True, type="primary")
    with col_btn2:
        if st.button("🗑️ Réinitialiser", use_container_width=True):
            st.session_state.pop("mail_emails", None)
            st.session_state.pop("mail_taches_extraites", None)
            st.rerun()

    if connecter:
        if not mot_de_passe or not serveur:
            st.error("❌ Informations de connexion mail introuvables dans la session.")
        else:
            with st.spinner("Connexion à votre boite mail..."):
                conn = connecter_boite_mail(email_addr, mot_de_passe, serveur)
            if conn:
                with st.spinner("Lecture des emails non lus..."):
                    emails_lus = lire_emails_non_lus(conn, nb_max=nb_emails)
                    conn.logout()
                if emails_lus:
                    st.session_state.mail_emails = emails_lus
                    st.success(f"✅ {len(emails_lus)} email(s) récupéré(s) !")
                else:
                    st.info("Aucun email non lu trouvé.")

    if st.session_state.get("mail_emails"):
        emails = st.session_state.mail_emails
        st.markdown(f"#### 📨 {len(emails)} email(s) non lu(s)")
        taches_a_sauver = []

        for i, em in enumerate(emails):
            st.markdown(f"""
            <div class="email-card">
                <div class="email-sujet">📩 {em['sujet']}</div>
                <div class="email-meta">De : {em['expediteur']} &nbsp;|&nbsp; {em['date']}</div>
                <div class="email-corps">{em['corps'][:300]}{'...' if len(em['corps'])>300 else ''}</div>
            </div>""", unsafe_allow_html=True)

            col_ext, col_skip = st.columns([3,1])
            with col_ext:
                if st.button("🤖 Extraire la tâche", key=f"ext_{i}", use_container_width=True):
                    with st.spinner("Analyse IA en cours..."):
                        tache = extraire_tache_depuis_email(em)
                        if "mail_taches_extraites" not in st.session_state:
                            st.session_state.mail_taches_extraites = {}
                        st.session_state.mail_taches_extraites[i] = tache
            with col_skip:
                if st.button("⏭️ Ignorer", key=f"skip_{i}", use_container_width=True):
                    st.session_state.get("mail_taches_extraites",{}).pop(i, None)

            extraites = st.session_state.get("mail_taches_extraites",{})
            if i in extraites:
                t = extraites[i]
                st.markdown(f"""
                <div class="tache-preview">
                    <b>📋 Tâche :</b> {t.get('tache','')}<br>
                    <b>📝 Description :</b> {t.get('description','')}<br>
                    <b>⚡ Priorité :</b> {badge_priorite(t.get('priorite','Moyenne'))}&nbsp;
                    <b>📅 Deadline :</b> {t.get('deadline','Aucune')}&nbsp;
                    <b>👤 Assigné à :</b> {t.get('assigne_a','Moi')}
                </div>""", unsafe_allow_html=True)
                taches_a_sauver.append(t)

        if taches_a_sauver:
            st.markdown("---")
            col_save, col_info = st.columns([2,3])
            with col_save:
                if st.button(f"💾 Sauvegarder {len(taches_a_sauver)} tâche(s)",
                             use_container_width=True, type="primary"):
                    with st.spinner("Sauvegarde dans Supabase..."):
                        for t in taches_a_sauver:
                            sauvegarder_tache(current_user, t)
                    st.success(f"✅ {len(taches_a_sauver)} tâche(s) sauvegardée(s) !")
                    st.session_state.pop("mail_emails", None)
                    st.session_state.pop("mail_taches_extraites", None)
                    st.rerun()
            with col_info:
                st.info("Les tâches sont visibles dans le Dashboard & Objectifs")