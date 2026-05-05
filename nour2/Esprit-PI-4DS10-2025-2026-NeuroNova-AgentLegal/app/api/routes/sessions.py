"""
app/api/routes/sessions.py — Gestion des sessions conversationnelles
"""
from fastapi import APIRouter, HTTPException
from app.models.response import SessionItem
from app.services.memory import list_sessions, delete_session, load_session

router = APIRouter(prefix="/sessions", tags=["Sessions"])


@router.get("", response_model=list[SessionItem])
async def get_sessions():
    """Liste toutes les sessions sauvegardées."""
    return list_sessions()


@router.get("/{session_id}")
async def get_session(session_id: str):
    """Retourne le détail d'une session (messages + résumé)."""
    session = load_session(session_id)
    if not session.get("messages") and not session.get("summary"):
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' introuvable.")
    return session


@router.delete("/{session_id}")
async def remove_session(session_id: str):
    """Supprime une session."""
    ok = delete_session(session_id)
    if not ok:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' introuvable.")
    return {"deleted": True, "session_id": session_id}
