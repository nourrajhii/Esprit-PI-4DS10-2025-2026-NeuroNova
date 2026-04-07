from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.material import Material
from app.schemas.material_schema import MaterialResponse

router = APIRouter(prefix="/materials", tags=["Materials"])

@router.get("/", response_model=list[MaterialResponse])
def get_materials(db: Session = Depends(get_db)):
    return db.query(Material).all()