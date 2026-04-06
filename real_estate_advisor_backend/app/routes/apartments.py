from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.apartment import Apartment
from app.schemas.apartment_schema import ApartmentResponse

router = APIRouter(prefix="/apartments", tags=["Apartments"])

@router.get("/", response_model=list[ApartmentResponse])
def get_apartments(db: Session = Depends(get_db)):
    return db.query(Apartment).limit(100).all()

@router.get("/{apartment_id}", response_model=ApartmentResponse)
def get_apartment_by_id(apartment_id: str, db: Session = Depends(get_db)):
    apartment = db.query(Apartment).filter(Apartment.id == apartment_id).first()
    if not apartment:
        raise HTTPException(status_code=404, detail="Appartement introuvable.")
    return apartment