"""
app/schemas/price_prediction_schema.py
"""

from pydantic import BaseModel, Field


class PricePredictionRequest(BaseModel):
    surface_m2:       float = Field(..., gt=0,  example=120.0)
    rooms:            int   = Field(..., ge=1,  example=3)
    bathrooms:        int   = Field(1,  ge=0,  example=1)
    city:             str   = Field(...,        example="Tunis")
    property_type:    str   = Field("appartement", example="appartement")
    transaction_type: str   = Field("vente",    example="vente")

    class Config:
        json_schema_extra = {
            "example": {
                "surface_m2": 120.0,
                "rooms": 3,
                "bathrooms": 1,
                "city": "Tunis",
                "property_type": "appartement",
                "transaction_type": "vente",
            }
        }


class MarketData(BaseModel):
    city_known:      bool
    n_comparables:   int
    market_pm2_low:  float
    market_pm2_mid:  float
    market_pm2_high: float


class ConfidenceRange(BaseModel):
    min: float
    max: float


class PricePredictionResponse(BaseModel):
    predicted_price:  float
    confidence_range: ConfidenceRange
    price_per_m2:     float
    market_data:      MarketData
    input_summary:    dict


class ModelInfoResponse(BaseModel):
    cities:            list[str]
    property_types:    list[str]
    transaction_types: list[str]
    n_samples:         int
    price_min:         float
    price_max:         float
    price_mean:        float
    market_pm2_median: float
