from pydantic import BaseModel

class CompareRequest(BaseModel):
    user_id: int | None = None
    apartment_a_id: str
    apartment_b_id: str
    budget: float

class CompareResponse(BaseModel):
    apartment_a_id: str
    apartment_b_id: str
    score_a: float
    score_b: float
    total_cost_a: float
    total_cost_b: float
    recommended_apartment_id: str
    reason: str
    details: dict