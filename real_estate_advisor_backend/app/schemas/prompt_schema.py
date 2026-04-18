from pydantic import BaseModel
from typing import Optional, List


class PromptRequest(BaseModel):
    prompt: str
    conversation_history: Optional[List[dict]] = []


class PropertyItem(BaseModel):
    id: str
    title: str
    price: float
    city: Optional[str] = None
    region: Optional[str] = None
    property_type: Optional[str] = None
    surface_m2: Optional[float] = None
    rooms: Optional[int] = None
    bathrooms: Optional[int] = None
    transaction_type: Optional[str] = None
    url: Optional[str] = None
    detected_category: Optional[str] = None
    detected_sub_type: Optional[str] = None
    score: Optional[float] = None
    price_per_m2: Optional[float] = None


class PromptAdvisorResponse(BaseModel):
    natural_response: str
    advice: str
    criteria: dict
    is_real_estate_query: bool
    properties: list[dict]
    total_found: int
    market_stats: dict