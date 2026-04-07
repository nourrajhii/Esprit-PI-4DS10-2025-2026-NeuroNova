from pydantic import BaseModel
from typing import Optional

class MaterialResponse(BaseModel):
    id: int
    name: str
    category: str
    subcategory: Optional[str] = None
    unit: str
    unit_price_avg: float

    class Config:
        from_attributes = True