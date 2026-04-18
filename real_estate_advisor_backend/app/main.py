"""
main.py — Point d'entrée FastAPI de l'agent conseiller immobilier.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes.advisor import router as advisor_router

app = FastAPI(
    title="Real Estate Advisor Tunisia",
    version="8.0",
    description="Agent conseiller immobilier intelligent — marché tunisien",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:4200",
        "http://127.0.0.1:4200",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(advisor_router)


@app.get("/health")
def health():
    return {
        "status":  "ok",
        "service": "real_estate_advisor_backend",
        "version": "8.0",
    }