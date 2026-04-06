from pydantic import BaseModel, Field
from typing import Optional
 
 
class RecommendRequest(BaseModel):
    budget:           float = Field(..., gt=0,      example=350000.0)
    surface_m2:       float = Field(..., gt=0,      example=100.0)
    rooms:            int   = Field(..., ge=1,      example=3)
    bathrooms:        int   = Field(1,  ge=0,      example=1)
    city:             str   = Field(...,            example="Tunis")
    transaction_type: str   = Field("vente",        example="vente")
    top_n:            int   = Field(5, ge=1, le=20, example=5)
 
 
class ScoreDetail(BaseModel):
    budget:  float
    surface: float
    rooms:   float
    city:    float
    baths:   float
 
 
class RecommendedApartment(BaseModel):
    rank:             int
    score:            float
    budget_ok:        bool
    score_detail:     ScoreDetail
    id:               str
    title:            str
    price:            float
    city:             str
    surface_m2:       float
    rooms:            int
    bathrooms:        int
    transaction_type: str
    url:              str
    price_diff:       float
 
 
class RecommendResponse(BaseModel):
    total_found:   int
    user_criteria: dict
    results:       list[RecommendedApartment]
 