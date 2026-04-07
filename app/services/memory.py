"""
app/services/memory.py — Gestion des sessions conversationnelles (JSON)
"""
import json
import os
import re
from datetime import datetime
from pathlib import Path

from app.core.config import MEMORY_DIR, CONTEXT_WINDOW, SUMMARY_KEEP_LAST, MAX_CHARS_BEFORE_SUMMARY


# ── Structures ─────────────────────────────────────────────────────────────────

def _empty_session(session_id: str) -> dict:
    return {
        "session_id": session_id,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "summary":    "",
        "messages":   [],
    }


def _session_path(session_id: str) -> Path:
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    return MEMORY_DIR / f"{session_id}.json"


# ── Persistence ────────────────────────────────────────────────────────────────

def load_session(session_id: str) -> dict:
    path = _session_path(session_id)
    if path.exists():
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return _empty_session(session_id)


def save_session(session: dict):
    session["updated_at"] = datetime.now().isoformat()
    path = _session_path(session["session_id"])
    with open(path, "w", encoding="utf-8") as f:
        json.dump(session, f, ensure_ascii=False, indent=2)


def list_sessions() -> list[dict]:
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    sessions = []
    for path in sorted(MEMORY_DIR.glob("*.json"), key=os.path.getmtime, reverse=True):
        try:
            with open(path, encoding="utf-8") as f:
                s = json.load(f)
            first_user = next(
                (m["content"][:60] for m in s.get("messages", []) if m["role"] == "user"),
                "Session vide"
            )
            sessions.append({
                "session_id":    s["session_id"],
                "updated_at":    s.get("updated_at", ""),
                "message_count": len(s.get("messages", [])),
                "preview":       first_user,
            })
        except Exception:
            pass
    return sessions


def delete_session(session_id: str) -> bool:
    path = _session_path(session_id)
    if path.exists():
        path.unlink()
        return True
    return False


# ── Messages ───────────────────────────────────────────────────────────────────

def add_message(session: dict, role: str, content: str):
    session["messages"].append({
        "role":      role,
        "content":   content,
        "timestamp": datetime.now().isoformat(),
    })


def _total_chars(session: dict) -> int:
    total = len(session.get("summary", ""))
    total += sum(len(m["content"]) for m in session.get("messages", []))
    return total


# ── Résumé automatique ─────────────────────────────────────────────────────────

def _detect_language(text: str) -> str:
    arabic = len(re.findall(r'[\u0600-\u06FF]', text))
    return "ar" if arabic > len(text) * 0.15 else "fr"


def summarize_old_messages(session: dict) -> bool:
    if _total_chars(session) < MAX_CHARS_BEFORE_SUMMARY:
        return False
    messages = session.get("messages", [])
    if len(messages) <= SUMMARY_KEEP_LAST * 2:
        return False

    cutoff = len(messages) - SUMMARY_KEEP_LAST * 2
    to_summarize = messages[:cutoff]
    to_keep = messages[cutoff:]

    conv_text = "\n".join(
        f"{'[User]' if m['role'] == 'user' else '[Assistant]'}: {m['content']}"
        for m in to_summarize
    )
    lang = _detect_language(conv_text)
    if lang == "ar":
        instr = "لخّص هذه المحادثة القانونية بإيجاز مع الحفاظ على المعلومات القانونية الأساسية."
    else:
        instr = "Résume cette conversation juridique de manière concise en conservant les informations légales clés."

    prompt = f"{instr}\n\nConversation :\n{conv_text}\n\nRésumé :"

    try:
        from app.services.llm import get_llm
        llm = get_llm()
        summary = llm.invoke(prompt).strip()
        old_summary = session.get("summary", "").strip()
        session["summary"] = f"{old_summary}\n\n{summary}".strip() if old_summary else summary
        session["messages"] = to_keep
        return True
    except Exception as e:
        print(f"⚠️ Erreur résumé : {e}")
        return False


# ── Contexte pour le prompt ────────────────────────────────────────────────────

def build_conversation_context(session: dict, lang: str = "fr") -> str:
    parts = []
    summary = session.get("summary", "").strip()
    if summary:
        header = "[ملخص المحادثة السابقة]" if lang == "ar" else "[Résumé des échanges précédents]"
        parts.append(f"{header}\n{summary}")

    recent = session.get("messages", [])[-(CONTEXT_WINDOW * 2):]
    if recent:
        header = "[آخر الرسائل]" if lang == "ar" else "[Derniers échanges]"
        lines = []
        for m in recent:
            label = ("المستخدم" if m["role"] == "user" else "المساعد") if lang == "ar" \
                else ("Utilisateur" if m["role"] == "user" else "Assistant")
            lines.append(f"{label}: {m['content']}")
        parts.append(f"{header}\n" + "\n".join(lines))

    return "\n\n".join(parts)


def new_session_id() -> str:
    return datetime.now().strftime("session_%Y%m%d_%H%M%S")
