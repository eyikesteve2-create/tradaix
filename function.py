import os
import json
from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader, TextLoader, CSVLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_groq import ChatGroq

load_dotenv()

# ─────────────────────────────────────────────
# MODÈLE GROQ (gratuit et rapide)
# ─────────────────────────────────────────────
def get_llm():
    return ChatGroq(
        api_key=os.getenv("GROQ_API_KEY"),
        model_name="llama3-70b-8192",
        temperature=0.2
    )


# ─────────────────────────────────────────────
# 1. CHARGEMENT DU DOCUMENT
#    Sans FAISS ni embeddings — on garde le texte
#    brut découpé en chunks pour l'envoyer à Groq
# ─────────────────────────────────────────────
def preparer_moteur_ia(chemin_fichier: str):
    ext = chemin_fichier.lower()

    if ext.endswith('.pdf'):
        loader = PyPDFLoader(chemin_fichier)
    elif ext.endswith('.csv'):
        loader = CSVLoader(chemin_fichier)
    else:
        loader = TextLoader(chemin_fichier, encoding='utf-8')

    documents = loader.load()

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=2000,
        chunk_overlap=200
    )
    chunks = text_splitter.split_documents(documents)

    # On retourne les chunks de texte brut (pas de vectorstore)
    texte_complet = "\n\n".join([c.page_content for c in chunks])

    # Limiter à 12000 caractères pour rester dans les limites de Groq
    return texte_complet[:12000]


# ─────────────────────────────────────────────
# 2. ANALYSE : résumé + synthèse + propositions
# ─────────────────────────────────────────────
def analyser_et_resoudre(question: str, contexte_document) -> str:
    if not contexte_document:
        return "❌ Erreur : aucun document chargé."

    llm = get_llm()

    prompt = f"""Tu es TradAIx, un expert en analyse documentaire et conseil stratégique pour les entreprises.

Voici le contenu du document analysé :
{contexte_document}

Question posée : {question}

Réponds TOUJOURS en structurant ta réponse en trois sections claires en français :

## 📋 RÉSUMÉ
Présente les points essentiels en lien avec la question. Sois concis et factuel (5 à 8 lignes max).

## 🔍 SYNTHÈSE
Analyse en profondeur les informations clés. Mets en évidence les enjeux, problèmes, opportunités ou risques.

## ✅ PROPOSITIONS D'ACTIONS
Liste 3 à 6 actions concrètes et prioritaires. Pour chaque action indique :
- La priorité : 🔴 Haute / 🟡 Moyenne / 🟢 Basse
- Une brève justification
"""

    reponse = llm.invoke(prompt)
    return reponse.content


# ─────────────────────────────────────────────
# 3. EXTRACTION DES TÂCHES pour le dashboard
# ─────────────────────────────────────────────
def extraire_taches_pour_dashboard(rapport: str) -> list:
    if not rapport:
        return []

    llm = get_llm()

    prompt = f"""Extrais les actions du rapport ci-dessous et retourne UNIQUEMENT un JSON valide.
Format attendu :
[
  {{"tache": "Nom de l'action", "priorite": "Haute", "statut": "À faire"}},
  {{"tache": "Autre action",    "priorite": "Moyenne", "statut": "À faire"}}
]

Rapport :
{rapport}

Réponds UNIQUEMENT avec le JSON brut, sans texte ni markdown autour.
"""

    try:
        reponse = llm.invoke(prompt)
        contenu = reponse.content.strip()

        if "```" in contenu:
            contenu = contenu.split("```")[1]
            if contenu.startswith("json"):
                contenu = contenu[4:]

        taches = json.loads(contenu.strip())

        return [
            {
                "tache":    t.get("tache", "Sans titre"),
                "priorite": t.get("priorite", "Moyenne"),
                "statut":   t.get("statut", "À faire"),
            }
            for t in taches if isinstance(t, dict) and "tache" in t
        ]

    except Exception:
        return [
            {"tache": "Vérifier le rapport manuellement", "priorite": "Haute",   "statut": "À faire"},
            {"tache": "Relancer l'analyse si nécessaire",  "priorite": "Moyenne", "statut": "À faire"},
        ]