from pydantic import BaseModel
from typing import Optional

class ApartmentResponse(BaseModel):
    id: str
    title: str
    price: float
    city: Optional[str] = None
    property_type: Optional[str] = None
    surface_m2: Optional[float] = None
    rooms: Optional[int] = None
    bathrooms: Optional[int] = None
    transaction_type: Optional[str] = None
    url: Optional[str] = None

    class Config:
        from_attributes = True