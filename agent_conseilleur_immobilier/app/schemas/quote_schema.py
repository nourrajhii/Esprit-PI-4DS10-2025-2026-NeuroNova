from pydantic import BaseModel

class QuoteRequest(BaseModel):
    user_id: int | None = None
    apartment_id: str
    project_type: str = "renovation"

class QuoteResponse(BaseModel):
    apartment_id: str
    project_type: str
    subtotal_materials: float
    subtotal_labor: float
    subtotal_equipment: float
    contingency_cost: float
    total_cost: float