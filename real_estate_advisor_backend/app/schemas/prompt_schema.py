from pydantic import BaseModel
from typing import Optional


class PromptRequest(BaseModel):
    prompt: str


class PromptAdvisorResponse(BaseModel):
    parsed_criteria: dict
    recommended_apartments: list[dict]
    comparison_result: Optional[dict] = None
    natural_response: str