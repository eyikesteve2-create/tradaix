import streamlit as st
from datetime import datetime, date, timedelta
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from db import get_db

# ─────────────────────────────────────────────
# CONSTANTES
# ─────────────────────────────────────────────
PRIORITES    = ["Haute", "Moyenne", "Basse"]
CATEGORIES   = ["Importante", "Urgente", "Quotidienne", "Hebdomadaire", "Mensuelle"]
STATUTS      = ["En attente de traitement", "En cours de traitement", "Tâche achevée"]
PRIO_ORDER   = {"Haute": 0, "Moyenne": 1, "Basse": 2}
COULEURS_CAT = {
    "Importante": "#CC0000", "Urgente": "#FF6600",
    "Quotidienne": "#1E3A8A", "Hebdomadaire": "#7C3AED", "Mensuelle": "#059669"
}

# ─────────────────────────────────────────────
# CSS
# ─────────────────────────────────────────────
def inject_css():
    st.markdown("""
    <style>
    .kanban-col { background:#F8F9FB; border-radius:14px; padding:16px 12px; min-height:300px; border-top:4px solid #DDD; }
    .kanban-col.attente { border-top-color:#F59E0B; }
    .kanban-col.encours { border-top-color:#3B82F6; }
    .kanban-col.achevee { border-top-color:#10B981; }
    .task-card { background:#FFF; border-radius:10px; padding:12px 14px; margin-bottom:10px;
                 box-shadow:0 2px 8px rgba(0,0,0,0.07); border-left:4px solid #DDD; font-size:13px; }
    .task-card.haute   { border-left-color:#CC0000; }
    .task-card.moyenne { border-left-color:#F59E0B; }
    .task-card.basse   { border-left-color:#10B981; }
    .task-card.achevee { border-left-color:#AAA; opacity:0.7; }
    .task-title { font-weight:700; color:#1E293B; margin-bottom:4px; font-size:14px; }
    .task-meta  { color:#888; font-size:11px; margin-bottom:6px; }
    .badge { display:inline-block; padding:2px 9px; border-radius:10px; font-size:11px; font-weight:600; margin-right:3px; }
    .b-haute    { background:#FFE0E0; color:#CC0000; }
    .b-moyenne  { background:#FFF3CD; color:#856404; }
    .b-basse    { background:#D4EDDA; color:#155724; }
    .b-attente  { background:#FEF3C7; color:#92400E; }
    .b-encours  { background:#DBEAFE; color:#1E40AF; }
    .b-achevee  { background:#D1FAE5; color:#065F46; }
    .b-transfere{ background:#EDE9FE; color:#5B21B6; }
    .dl-ok     { color:#059669; font-size:11px; font-weight:600; }
    .dl-proche { color:#F59E0B; font-size:11px; font-weight:600; }
    .dl-depasse{ color:#CC0000; font-size:11px; font-weight:700; }
    .stat-card { background:#fff; border-radius:12px; padding:18px 10px; text-align:center;
                 box-shadow:0 2px 10px rgba(0,0,0,0.07); border-bottom:3px solid #E5E7EB; }
    .stat-num  { font-size:2.4em; font-weight:800; }
    .stat-label{ font-size:12px; color:#666; margin-top:4px; }
    .notif-badge { background:#CC0000; color:white; border-radius:50%; width:20px; height:20px;
                   display:inline-flex; align-items:center; justify-content:center;
                   font-size:11px; font-weight:700; margin-left:4px; }
    </style>
    """, unsafe_allow_html=True)

# ─────────────────────────────────────────────
# UTILITAIRES
# ─────────────────────────────────────────────
def deadline_html(dl_str):
    if not dl_str:
        return ""
    try:
        dl    = datetime.strptime(str(dl_str)[:10], "%Y-%m-%d").date()
        delta = (dl - date.today()).days
        if delta < 0:
            return f'<span class="dl-depasse">⚠️ Dépassée de {abs(delta)}j</span>'
        elif delta <= 2:
            return f'<span class="dl-proche">🔥 Dans {delta}j</span>'
        else:
            return f'<span class="dl-ok">📅 {dl.strftime("%d/%m/%Y")}</span>'
    except:
        return f'<span class="dl-ok">📅 {dl_str}</span>'

def badge(texte, cls):
    return f'<span class="badge {cls}">{texte}</span>'

def statut_badge(s):
    m = {
        "En attente de traitement": ("b-attente", "⏳ En attente"),
        "En cours de traitement":   ("b-encours",  "🔄 En cours"),
        "Tâche achevée":            ("b-achevee",  "✅ Achevée"),
    }
    cls, label = m.get(s, ("b-attente", s))
    return f'<span class="badge {cls}">{label}</span>'

# ─────────────────────────────────────────────
# CRUD TÂCHES
# ─────────────────────────────────────────────
def get_mes_taches(user_email: str) -> list:
    db   = get_db()
    res1 = db.table("taches").select("*").eq("cree_par", user_email).execute()
    res2 = db.table("taches").select("*").eq("assigne_a", user_email).neq("cree_par", user_email).execute()
    return (res1.data or []) + (res2.data or [])

def creer_tache_db(tache: dict) -> int:
    db  = get_db()
    res = db.table("taches").insert({
        "tache":       tache.get("tache","")[:60],
        "description": tache.get("description",""),
        "categorie":   tache.get("categorie","Quotidienne"),
        "priorite":    tache.get("priorite","Moyenne"),
        "statut":      tache.get("statut","En attente de traitement"),
        "deadline":    tache.get("deadline"),
        "delai_jours": tache.get("delai_jours",3),
        "assigne_a":   tache.get("assigne_a",""),
        "cree_par":    tache.get("cree_par",""),
        "etoile":      bool(tache.get("etoile",False)),
        "source":      tache.get("source","manuel"),
    }).execute()
    return res.data[0]["id"] if res.data else None

def update_tache(tid, champs: dict):
    get_db().table("taches").update(champs).eq("id", tid).execute()

def supprimer_tache(tid):
    get_db().table("taches").delete().eq("id", tid).execute()

def get_utilisateurs(current_user: str) -> list:
    db  = get_db()
    res = db.table("utilisateurs").select("email").neq("email", current_user).execute()
    return [r["email"] for r in (res.data or [])]

def envoyer_notif_messagerie(expediteur, destinataire, tache_id, titre):
    db       = get_db()
    membres  = sorted([expediteur, destinataire])
    salon_id = f"prive__{membres[0]}__{membres[1]}"
    res      = db.table("salons").select("salon_id").eq("salon_id", salon_id).execute()
    if not res.data:
        db.table("salons").insert({
            "salon_id": salon_id, "type": "prive", "membres": ",".join(membres)
        }).execute()
    db.table("messages").insert({
        "salon_id":    salon_id,
        "expediteur":  expediteur,
        "contenu":     f"📋 Tâche assignée : **{titre}**\nAllez dans 📊 Dashboard pour commencer.",
        "type":        "tache",
        "tache_id":    tache_id,
        "tache_titre": titre,
        "lu_par":      expediteur,
    }).execute()

# ─────────────────────────────────────────────
# FORMULAIRE CRÉATION
# ─────────────────────────────────────────────
def formulaire_creation(current_user, utilisateurs):
    with st.expander("➕ Créer et transférer une tâche", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            titre     = st.text_input("📋 Titre *", placeholder="Ex: Rapport mensuel")
            categorie = st.selectbox("🗂️ Catégorie", CATEGORIES)
            priorite  = st.selectbox("⚡ Priorité", PRIORITES)
        with col2:
            delai     = st.number_input("⏱️ Délai (jours)", min_value=1, max_value=365, value=3)
            deadline  = date.today() + timedelta(days=int(delai))
            st.info(f"📅 Date limite : **{deadline.strftime('%d/%m/%Y')}**")
            dest      = st.selectbox("👤 Assigner à", ["Moi-même"] + utilisateurs)
        description = st.text_area("📝 Description", placeholder="Décrivez la tâche...")

        if st.button("💾 Créer & Transférer", use_container_width=True, type="primary"):
            if not titre:
                st.error("Le titre est obligatoire.")
                return
            assignee = current_user if dest == "Moi-même" else dest
            tid = creer_tache_db({
                "tache": titre, "description": description,
                "categorie": categorie, "priorite": priorite,
                "statut": "En attente de traitement",
                "deadline": str(deadline), "delai_jours": int(delai),
                "assigne_a": assignee, "cree_par": current_user,
                "etoile": False, "source": "manuel",
            })
            if assignee != current_user:
                try:
                    envoyer_notif_messagerie(current_user, assignee, tid, titre)
                    st.success(f"✅ Tâche **{titre}** créée et transférée à **{assignee}** avec notification !")
                except:
                    st.success(f"✅ Tâche **{titre}** créée et assignée à **{assignee}** !")
            else:
                st.success(f"✅ Tâche **{titre}** créée !")
            st.rerun()

# ─────────────────────────────────────────────
# CARTE TÂCHE
# ─────────────────────────────────────────────
def carte_tache(t, current_user, utilisateurs):
    tid      = t.get("id")
    titre    = t.get("tache","")
    statut   = t.get("statut","En attente de traitement")
    priorite = t.get("priorite","Moyenne")
    deadline = t.get("deadline","")
    etoile   = bool(t.get("etoile",False))
    cree_par = t.get("cree_par","")
    assignee = t.get("assigne_a","")
    est_mien = cree_par == current_user
    transfere= assignee != cree_par

    prio_cls  = priorite.lower()
    dl_html   = deadline_html(deadline)
    etoile_s  = "⭐" if etoile else "☆"
    transf_b  = badge("Transférée","b-transfere") if transfere else ""
    direction = (f"📤 → {assignee}" if transfere and est_mien else
                 f"📥 ← {cree_par}" if transfere else "👤 Ma tâche")

    st.markdown(f"""
    <div class="task-card {prio_cls}">
        <div style="display:flex;justify-content:space-between;">
            <div class="task-title">{titre}</div>
            <div style="font-size:18px">{etoile_s}</div>
        </div>
        <div class="task-meta">{direction} &nbsp;|&nbsp; {dl_html}</div>
        <div>{badge(priorite,f"b-{prio_cls}")}{statut_badge(statut)}{transf_b}</div>
    </div>
    """, unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns([3, 3, 2, 1])
    with c1:
        if statut == "En attente de traitement":
            if st.button("▶️ Commencer", key=f"start_{tid}", use_container_width=True):
                update_tache(tid, {"statut": "En cours de traitement", "debut_le": datetime.now().isoformat()})
                st.rerun()
        elif statut == "En cours de traitement":
            if st.button("✅ Marquer achevée", key=f"done_{tid}", use_container_width=True):
                update_tache(tid, {"statut": "Tâche achevée", "fin_le": datetime.now().isoformat()})
                st.rerun()
        else:
            st.success("✅ Tâche achevée")
    with c2:
        if est_mien and utilisateurs:
            dest2 = st.selectbox("Retransférer", ["—"]+utilisateurs,
                                 key=f"rt_{tid}", label_visibility="collapsed")
            if dest2 != "—":
                update_tache(tid, {"assigne_a": dest2})
                try: envoyer_notif_messagerie(current_user, dest2, tid, titre)
                except: pass
                st.success(f"Transférée à {dest2} !")
                st.rerun()
    with c3:
        if st.button(f"{'⭐' if not etoile else '✩'} Étoile", key=f"star_{tid}", use_container_width=True):
            update_tache(tid, {"etoile": not etoile})
            st.rerun()
    with c4:
        if est_mien:
            if st.button("🗑️", key=f"del_{tid}"):
                supprimer_tache(tid)
                st.rerun()
    st.markdown("<hr style='margin:4px 0;opacity:0.1;'>", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# STATISTIQUES
# ─────────────────────────────────────────────
def afficher_statistiques(taches):
    st.markdown("## 📊 Statistiques des dossiers")
    total    = len(taches)
    attente  = sum(1 for t in taches if t.get("statut") == "En attente de traitement")
    encours  = sum(1 for t in taches if t.get("statut") == "En cours de traitement")
    achevees = sum(1 for t in taches if t.get("statut") == "Tâche achevée")
    etoilees = sum(1 for t in taches if t.get("etoile"))
    urgentes = sum(1 for t in taches if t.get("priorite") == "Haute")
    depassees= 0
    for t in taches:
        dl = t.get("deadline","")
        if dl and t.get("statut") != "Tâche achevée":
            try:
                if datetime.strptime(str(dl)[:10],"%Y-%m-%d").date() < date.today():
                    depassees += 1
            except: pass
    taux = round((achevees/total*100) if total > 0 else 0, 1)

    cols = st.columns(7)
    for col,(num,label,color,ico) in zip(cols,[
        (total,"Total","#1E3A8A","📋"),
        (attente,"En attente","#F59E0B","⏳"),
        (encours,"En cours","#3B82F6","🔄"),
        (achevees,"Achevées","#10B981","✅"),
        (etoilees,"Prioritaires","#F59E0B","⭐"),
        (urgentes,"Urgentes","#CC0000","🔥"),
        (depassees,"Dépassées","#CC0000","⚠️"),
    ]):
        col.markdown(f"""
        <div class="stat-card" style="border-bottom-color:{color}">
            <div class="stat-num" style="color:{color}">{num}</div>
            <div class="stat-label">{ico} {label}</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    col_g1, col_g2 = st.columns(2)
    with col_g1:
        fig1 = go.Figure(data=[go.Pie(
            labels=["En attente","En cours","Achevées"],
            values=[attente, encours, achevees], hole=0.5,
            marker_colors=["#F59E0B","#3B82F6","#10B981"]
        )])
        fig1.update_layout(title="Répartition par statut", height=300)
        st.plotly_chart(fig1, use_container_width=True)
    with col_g2:
        prios = [t.get("priorite","Moyenne") for t in taches]
        df_p  = pd.DataFrame({"Priorité":prios})["Priorité"].value_counts().reset_index()
        df_p.columns = ["Priorité","Nombre"]
        fig2 = px.bar(df_p, x="Priorité", y="Nombre", title="Tâches par priorité",
                      color="Priorité",
                      color_discrete_map={"Haute":"#CC0000","Moyenne":"#F59E0B","Basse":"#10B981"})
        fig2.update_layout(height=300, showlegend=False)
        st.plotly_chart(fig2, use_container_width=True)

    col_g3, col_g4 = st.columns(2)
    with col_g3:
        fig3 = go.Figure(go.Indicator(
            mode="gauge+number", value=taux,
            title={"text":"Taux d'achèvement (%)"},
            gauge={"axis":{"range":[0,100]},"bar":{"color":"#10B981"},
                   "steps":[{"range":[0,33],"color":"#FFE0E0"},
                             {"range":[33,66],"color":"#FFF3CD"},
                             {"range":[66,100],"color":"#D1FAE5"}],
                   "threshold":{"line":{"color":"#CC0000","width":4},"value":80}}
        ))
        fig3.update_layout(height=280)
        st.plotly_chart(fig3, use_container_width=True)
    with col_g4:
        taches_dl = [t for t in taches if t.get("deadline") and t.get("statut") != "Tâche achevée"]
        if taches_dl:
            df_dl = pd.DataFrame([{
                "Tâche": t.get("tache","")[:25],
                "Start": date.today().strftime("%Y-%m-%d"),
                "Deadline": str(t.get("deadline",""))[:10],
                "Priorité": t.get("priorite","Moyenne"),
            } for t in taches_dl])
            df_dl["Deadline"] = pd.to_datetime(df_dl["Deadline"])
            fig4 = px.timeline(df_dl, x_start="Start", x_end="Deadline",
                               y="Tâche", color="Priorité",
                               color_discrete_map={"Haute":"#CC0000","Moyenne":"#F59E0B","Basse":"#10B981"},
                               title="Timeline des deadlines")
            fig4.update_yaxes(autorange="reversed")
            fig4.update_layout(height=280)
            st.plotly_chart(fig4, use_container_width=True)
        else:
            st.info("Aucune deadline à afficher.")

# ─────────────────────────────────────────────
# MODULE PRINCIPAL
# ─────────────────────────────────────────────
def module_dashboard(current_user: str, liste_taches_analyse=None):
    inject_css()
    utilisateurs = get_utilisateurs(current_user)

    col_title, col_stats, col_refresh = st.columns([4,1,1])
    with col_title:
        st.markdown("### 📊 Dashboard & Suivi des Tâches")
    with col_stats:
        show_stats = st.button("📈 Statistiques", use_container_width=True)
    with col_refresh:
        if st.button("🔄 Actualiser", use_container_width=True, key="btn_actu_dashboard"):
            st.rerun()

    if liste_taches_analyse:
        with st.expander(f"📥 {len(liste_taches_analyse)} tâche(s) de l'analyse IA", expanded=False):
            for i, t in enumerate(liste_taches_analyse):
                c1,c2,c3,c4 = st.columns([3,2,2,1])
                with c1: st.write(f"📋 **{t.get('tache','')}**")
                with c2: cat = st.selectbox("Catégorie", CATEGORIES, key=f"ia_cat_{i}")
                with c3: dl  = st.date_input("Deadline", value=date.today()+timedelta(days=7), key=f"ia_dl_{i}")
                with c4:
                    if st.button("➕", key=f"ia_add_{i}", use_container_width=True):
                        creer_tache_db({
                            "tache": t.get("tache",""), "description": "",
                            "categorie": cat, "priorite": t.get("priorite","Moyenne"),
                            "statut": "En attente de traitement", "deadline": str(dl),
                            "delai_jours": (dl-date.today()).days,
                            "assigne_a": current_user, "cree_par": current_user,
                            "etoile": False, "source": "analyse",
                        })
                        st.success("✅ Ajoutée !")
                        st.rerun()

    formulaire_creation(current_user, utilisateurs)
    st.markdown("---")

    taches = get_mes_taches(current_user)
    if not taches:
        st.info("Aucune tâche. Créez votre première tâche ci-dessus !")
        return

    if show_stats:
        afficher_statistiques(taches)
        return

    attente_list = sorted(
        [t for t in taches if t.get("statut") == "En attente de traitement"],
        key=lambda t: (PRIO_ORDER.get(t.get("priorite","Moyenne"),1),
                       0 if t.get("etoile") else 1,
                       str(t.get("deadline") or "9999"))
    )
    encours_list = [t for t in taches if t.get("statut") == "En cours de traitement"]
    achevee_list = [t for t in taches if t.get("statut") == "Tâche achevée"]
    nb_att, nb_enc, nb_ach = len(attente_list), len(encours_list), len(achevee_list)

    col_f1,col_f2,col_f3 = st.columns(3)
    with col_f1: filtre_prio   = st.selectbox("Priorité",  ["Toutes"]+PRIORITES,  label_visibility="collapsed")
    with col_f2: filtre_cat    = st.selectbox("Catégorie", ["Toutes"]+CATEGORIES, label_visibility="collapsed")
    with col_f3: filtre_etoile = st.checkbox("⭐ Étoilées uniquement")

    def filtrer(lst):
        r = lst
        if filtre_prio  != "Toutes": r = [t for t in r if t.get("priorite")  == filtre_prio]
        if filtre_cat   != "Toutes": r = [t for t in r if t.get("categorie") == filtre_cat]
        if filtre_etoile:            r = [t for t in r if t.get("etoile")]
        return r

    attente_list = filtrer(attente_list)
    encours_list = filtrer(encours_list)
    achevee_list = filtrer(achevee_list)

    col_att, col_enc, col_ach = st.columns(3)
    with col_att:
        st.markdown(f'<div class="kanban-col attente"><div style="font-weight:700;font-size:15px;margin-bottom:12px;">⏳ En attente <span class="notif-badge">{nb_att}</span></div></div>', unsafe_allow_html=True)
        st.caption("Triées par priorité ↓")
        for t in attente_list: carte_tache(t, current_user, utilisateurs)
        if not attente_list: st.info("Aucune tâche en attente.")
    with col_enc:
        st.markdown(f'<div class="kanban-col encours"><div style="font-weight:700;font-size:15px;margin-bottom:12px;">🔄 En cours <span class="notif-badge" style="background:#3B82F6">{nb_enc}</span></div></div>', unsafe_allow_html=True)
        for t in encours_list: carte_tache(t, current_user, utilisateurs)
        if not encours_list: st.info("Aucune tâche en cours.")
    with col_ach:
        st.markdown(f'<div class="kanban-col achevee"><div style="font-weight:700;font-size:15px;margin-bottom:12px;">✅ Tâche achevée <span class="notif-badge" style="background:#10B981">{nb_ach}</span></div></div>', unsafe_allow_html=True)
        for t in achevee_list: carte_tache(t, current_user, utilisateurs)
        if not achevee_list: st.info("Aucune tâche achevée.")
