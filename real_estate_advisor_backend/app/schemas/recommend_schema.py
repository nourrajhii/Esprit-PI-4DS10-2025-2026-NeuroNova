from pydantic import BaseModel
from typing import Optional

class RecommendRequest(BaseModel):
    budget: float
    city: Optional[str] = None