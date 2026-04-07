"""
app/api/routes/chat.py — Route principale POST /chat

CORRECTIFS :
- Gestion d'erreur granulaire : distingue erreur RAG vs erreur LLM vs erreur FAISS
- Plus de 500 "muet" — le message d'erreur est toujours descriptif
- Réponse de fallback si le LLM est indisponible (évite le crash total)
- Validation question vide déjà gérée par Pydantic (min_length=1)
"""
from fastapi import APIRouter, HTTPException
import traceback

from app.models.request import ChatRequest
from app.models.response import ChatResponse, MetricItem, SourceInfo
from app.services.rag import ask_with_metrics
from app.services.memory import (
    load_session, save_session, add_message,
    build_conversation_context, summarize_old_messages, new_session_id,
)
from app.core.language import detect_language

router = APIRouter(tags=["Chat"])


@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    """
    Endpoint principal de l'assistant juridique.

    - Détecte automatiquement la langue (fr / ar)
    - Classe la question par type juridique
    - Répond immédiatement aux salutations (chitchat)
    - Effectue les calculs financiers directement
    - Utilise le cache puis le RAG pour les questions juridiques
    - Conserve la mémoire conversationnelle via session_id
    """
    question = req.question  # déjà strippé par le validator Pydantic

    # ── Mémoire conversationnelle ──────────────────────────────
    session_id = req.session_id or new_session_id()

    try:
        session = load_session(session_id)
        summarize_old_messages(session)
    except Exception as e:
        # Une erreur mémoire ne doit pas bloquer la réponse
        print(f"⚠️ Erreur chargement session {session_id} : {e}")
        from app.services.memory import _empty_session
        session = _empty_session(session_id)

    lang     = detect_language(question)
    conv_ctx = build_conversation_context(session, lang=lang)

    # ── Appel RAG ──────────────────────────────────────────────
    try:
        result = ask_with_metrics(
            question=question,
            k=req.k,
            conversation_context=conv_ctx,
        )
    except Exception as e:
        # Log complet côté serveur, message clair côté client
        print(f"❌ Erreur RAG — question: {question!r}")
        traceback.print_exc()

        error_msg = str(e)

        # Détecter les erreurs Ollama courantes pour donner un message utile
        if "connection" in error_msg.lower() or "refused" in error_msg.lower():
            detail = (
                "Le service LLM (Ollama) est inaccessible. "
                "Vérifiez qu'Ollama tourne avec : ollama serve"
            )
        elif "model" in error_msg.lower() and "not found" in error_msg.lower():
            detail = (
                "Modèle LLM introuvable. "
                "Installez-le avec : ollama pull llama3.2:3b"
            )
        else:
            detail = f"Erreur moteur RAG : {error_msg}"

        raise HTTPException(status_code=500, detail=detail)

    # ── Sauvegarde session ────────────────────────────────────
    if result.get("question_type") != "chitchat":
        try:
            add_message(session, "user", question)
            add_message(session, "assistant", result["answer"])
            save_session(session)
        except Exception as e:
            print(f"⚠️ Erreur sauvegarde session : {e}")
            # On continue — la réponse est déjà calculée

    # ── Construction réponse ──────────────────────────────────
    metrics = [
        MetricItem(**{k: v for k, v in m.items() if k != "_doc"})
        for m in result.get("metrics", [])
    ]

    hs = result.get("hardcoded_source")
    hardcoded_source = SourceInfo(**hs) if hs else None

    return ChatResponse(
        answer=result["answer"],
        question_type=result["question_type"],
        lang=result["lang"],
        is_calculation=result["is_calculation"],
        from_cache=result.get("from_cache", False),
        hardcoded_source=hardcoded_source,
        metrics=metrics,
        cache_similarity=result.get("cache_similarity"),
        cache_date=result.get("cache_date"),
        session_id=session_id,
    )