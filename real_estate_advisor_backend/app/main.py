from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import app.models

from app.routes.apartments import router as apartments_router
from app.routes.materials import router as materials_router
from app.routes.advisor import router as advisor_router
from app.routes.recommendations import router as recommendations_router

app = FastAPI(
    title="Real Estate Advisor API",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(apartments_router)
app.include_router(materials_router)
app.include_router(advisor_router)
app.include_router(recommendations_router)

@app.get("/")
def root():
    return {"message": "Real Estate Advisor API is running"}

@app.get("/health")
def health_check():
    return {"status": "ok"}