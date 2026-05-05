"""
Thin /invoke adapter for nour2 legal chatbot.
Wraps existing /chat endpoint without touching core logic.
Run: uvicorn invoke_adapter:app --host 0.0.0.0 --port 8003
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx, uvicorn, os

# Load root .env so GEMINI_API_KEY and OLLAMA_HOST are available
try:
    from dotenv import load_dotenv
    _here = os.path.dirname(os.path.abspath(__file__))
    load_dotenv(os.path.join(_here, ".env"), override=False)
    load_dotenv(os.path.join(_here, "..", "..", ".env"), override=False)  # project root
except ImportError:
    pass

app = FastAPI(title="Nour2 Legal /invoke adapter")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

LEGAL_BASE = os.getenv("LEGAL_INTERNAL_URL", "http://localhost:8011")


class InvokeRequest(BaseModel):
    input: dict
    context: dict = {}


@app.post("/invoke")
async def invoke(req: InvokeRequest):
    question = req.input.get("question", req.input.get("message", ""))
    session_id = req.context.get("session_id")
    k = req.input.get("k", 3)

    if not question:
        raise HTTPException(status_code=400, detail="input.question is required")

    payload = {"question": question, "k": k}
    if session_id:
        payload["session_id"] = session_id

    async with httpx.AsyncClient(timeout=120) as client:
        try:
            resp = await client.post(f"{LEGAL_BASE}/chat", json=payload)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Legal agent unreachable: {e}")

    # Strip internal _doc field from metrics before forwarding
    metrics = []
    for m in data.get("metrics", []):
        metrics.append({k: v for k, v in m.items() if k != "_doc"})

    lang = data.get("lang", "fr")
    answer = data.get("answer", "").strip()
    if not answer:
        answer = (
            "عذراً، لم يتمكن النظام من توليد إجابة. تأكد من أن Ollama يعمل أو أن GEMINI_API_KEY محدد."
            if lang == "ar"
            else "Désolé, le système n'a pas pu générer de réponse. Vérifiez qu'Ollama tourne ou que GEMINI_API_KEY est configuré."
        )

    return {
        "output": {
            "answer": answer,
            "question_type": data.get("question_type", ""),
            "lang": data.get("lang", "fr"),
            "is_calculation": data.get("is_calculation", False),
            "from_cache": data.get("from_cache", False),
            "metrics": metrics,
            "hardcoded_source": data.get("hardcoded_source"),
            "session_id": data.get("session_id"),
        },
        "agent": "legal",
        "confidence": 0.92
    }


@app.get("/health")
async def health():
    async with httpx.AsyncClient(timeout=5) as client:
        try:
            r = await client.get(f"{LEGAL_BASE}/health")
            return {"status": "ok", "upstream": r.json()}
        except Exception as e:
            return {"status": "degraded", "error": str(e)}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8003)
