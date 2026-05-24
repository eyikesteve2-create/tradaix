from datetime import datetime
import streamlit as st
from db import get_db


# ─────────────────────────────────────────────
# CSS STYLE WHATSAPP
# ─────────────────────────────────────────────
def inject_css():
    st.markdown("""
    <style>
    .chat-container {
        display:flex; flex-direction:column; gap:8px; padding:16px;
        max-height:500px; overflow-y:auto; background:#f0f2f5;
        border-radius:12px; margin-bottom:12px;
    }
    .msg-received { display:flex; align-items:flex-end; gap:8px; max-width:75%; align-self:flex-start; }
    .msg-received .bubble {
        background:#fff; color:#111827; padding:10px 14px;
        border-radius:18px 18px 18px 4px; font-size:14px; line-height:1.5;
        box-shadow:0 1px 2px rgba(0,0,0,0.08);
    }
    .msg-sent { display:flex; flex-direction:column; align-items:flex-end; max-width:75%; align-self:flex-end; }
    .msg-sent .bubble {
        background:#1E3A8A; color:#fff; padding:10px 14px;
        border-radius:18px 18px 4px 18px; font-size:14px; line-height:1.5;
    }
    .avatar {
        width:32px; height:32px; border-radius:50%; background:#1E3A8A; color:white;
        display:flex; align-items:center; justify-content:center;
        font-size:13px; font-weight:bold; flex-shrink:0;
    }
    .msg-meta { font-size:11px; color:#6B7280; margin-bottom:3px; padding:0 4px; }
    .date-separator { text-align:center; color:#9CA3AF; font-size:12px; margin:8px 0; }
    .online-bar {
        display:flex; gap:12px; padding:10px 16px; background:white;
        border-radius:10px; margin-bottom:8px; flex-wrap:wrap;
    }
    .online-user { display:flex; align-items:center; gap:6px; font-size:13px; color:#374151; }
    .dot-online { width:8px; height:8px; border-radius:50%; background:#10B981; display:inline-block; }
    .tick { font-size:11px; color:#93C5FD; margin-top:2px; }
    .tick.seen { color:#3B82F6; }
    </style>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────
# UTILITAIRES
# ─────────────────────────────────────────────
def get_utilisateurs(current_user: str) -> list:
    db  = get_db()
    res = db.table("utilisateurs").select("email, nom").neq("email", current_user).execute()
    return [r["email"] for r in (res.data or [])]


def get_ou_creer_salon(user1: str, user2: str) -> str:
    membres  = sorted([user1, user2])
    salon_id = f"prive__{membres[0]}__{membres[1]}"
    db       = get_db()
    res      = db.table("salons").select("salon_id").eq("salon_id", salon_id).execute()
    if not res.data:
        db.table("salons").insert({
            "salon_id": salon_id,
            "type":     "prive",
            "membres":  ",".join(membres),
        }).execute()
    return salon_id


def get_ou_creer_salon_general() -> str:
    salon_id = "general"
    db       = get_db()
    res      = db.table("salons").select("salon_id").eq("salon_id", salon_id).execute()
    if not res.data:
        db.table("salons").insert({
            "salon_id": salon_id,
            "type":     "groupe",
            "nom":      "Salon général",
        }).execute()
    return salon_id


def get_messages(salon_id: str, limit: int = 100) -> list:
    db  = get_db()
    res = db.table("messages").select("*").eq("salon_id", salon_id)\
            .order("timestamp", desc=False).limit(limit).execute()
    return res.data or []


def envoyer_message(salon_id: str, expediteur: str, contenu: str):
    if not contenu.strip():
        return
    get_db().table("messages").insert({
        "salon_id":   salon_id,
        "expediteur": expediteur,
        "contenu":    contenu.strip(),
        "lu_par":     expediteur,
    }).execute()


def marquer_lus(salon_id: str, current_user: str):
    db  = get_db()
    res = db.table("messages").select("id, lu_par")\
            .eq("salon_id", salon_id).neq("expediteur", current_user).execute()
    for msg in (res.data or []):
        lu_par = msg.get("lu_par", "") or ""
        if current_user not in lu_par.split(","):
            nouveau = (lu_par + "," + current_user).strip(",")
            db.table("messages").update({"lu_par": nouveau}).eq("id", msg["id"]).execute()


# ─────────────────────────────────────────────
# AFFICHAGE MESSAGE
# ─────────────────────────────────────────────
def render_message(msg: dict, current_user: str):
    expediteur = msg.get("expediteur", "?")
    contenu    = msg.get("contenu", "")
    timestamp  = msg.get("timestamp", "")
    lu_par     = msg.get("lu_par", "") or ""

    heure = ""
    if timestamp:
        try:
            heure = datetime.fromisoformat(timestamp.replace("Z", "+00:00")).strftime("%H:%M")
        except Exception:
            heure = ""

    initiale = expediteur[0].upper() if expediteur else "?"
    est_moi  = (expediteur == current_user)
    vu       = current_user in lu_par.split(",")
    tick     = "✓✓" if vu else "✓"
    tick_cls = "seen" if vu else ""

    if est_moi:
        st.markdown(f"""
        <div class="msg-sent">
            <div class="msg-meta">{heure}</div>
            <div class="bubble">{contenu}</div>
            <div class="tick {tick_cls}">{tick}</div>
        </div>""", unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class="msg-received">
            <div class="avatar">{initiale}</div>
            <div>
                <div class="msg-meta">{expediteur} · {heure}</div>
                <div class="bubble">{contenu}</div>
            </div>
        </div>""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# MODULE PRINCIPAL
# ─────────────────────────────────────────────
def module_messagerie(current_user: str):
    inject_css()
    st.markdown("### 💬 Messagerie TradAIx")

    utilisateurs = get_utilisateurs(current_user)
    if utilisateurs:
        barre = "".join([
            f'<div class="online-user"><span class="dot-online"></span>{u}</div>'
            for u in utilisateurs
        ])
        st.markdown(f'<div class="online-bar">{barre}</div>', unsafe_allow_html=True)
    else:
        st.info("Aucun autre utilisateur enregistré pour l'instant.")

    col1, col2 = st.columns([3, 1])
    with col1:
        destinataire = st.selectbox(
            "Conversation avec :",
            utilisateurs if utilisateurs else ["(aucun utilisateur)"],
            key="dest_select"
        )
    with col2:
        salon_groupe = st.checkbox("Salon général", key="salon_groupe")

    if salon_groupe:
        salon_id = get_ou_creer_salon_general()
    elif utilisateurs:
        salon_id = get_ou_creer_salon(current_user, destinataire)
    else:
        st.warning("Aucun autre utilisateur disponible.")
        return

    messages = get_messages(salon_id)
    marquer_lus(salon_id, current_user)

    st.markdown('<div class="chat-container">', unsafe_allow_html=True)
    last_date = None
    for msg in messages:
        ts = msg.get("timestamp", "")
        if ts:
            try:
                date_str = datetime.fromisoformat(ts.replace("Z", "+00:00")).strftime("%d %B %Y")
                if date_str != last_date:
                    st.markdown(
                        f'<div class="date-separator">── {date_str} ──</div>',
                        unsafe_allow_html=True
                    )
                    last_date = date_str
            except Exception:
                pass
        render_message(msg, current_user)

    if not messages:
        st.markdown(
            '<div style="text-align:center;color:#9CA3AF;padding:40px 0;">'
            'Aucun message. Soyez le premier à écrire !</div>',
            unsafe_allow_html=True
        )
    st.markdown('</div>', unsafe_allow_html=True)

    with st.form(key=f"form_msg_{salon_id}", clear_on_submit=True):
        col_inp, col_btn = st.columns([5, 1])
        with col_inp:
            nouveau_msg = st.text_input(
                "Message", placeholder="Écrire un message...",
                label_visibility="collapsed"
            )
        with col_btn:
            envoyer = st.form_submit_button("📤")
        if envoyer and nouveau_msg.strip():
            envoyer_message(salon_id, current_user, nouveau_msg)
            st.rerun()

    col_refresh, col_info = st.columns([1, 4])
    with col_refresh:
        if st.button("🔄 Actualiser", use_container_width=True, key="btn_actu_messagerie"):
            st.rerun()
    with col_info:
        st.caption("Cliquez sur Actualiser pour voir les nouveaux messages.")
