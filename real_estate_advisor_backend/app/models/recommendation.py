from sqlalchemy import Column, Integer, Text, DECIMAL, TIMESTAMP, ForeignKey, String, text
from app.database import Base

class Recommendation(Base):
    __tablename__ = "recommendations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL", onupdate="CASCADE"), nullable=True)
    apartment_a_id = Column(String(100), ForeignKey("apartments.id", ondelete="SET NULL", onupdate="CASCADE"), nullable=True)
    apartment_b_id = Column(String(100), ForeignKey("apartments.id", ondelete="SET NULL", onupdate="CASCADE"), nullable=True)
    budget = Column(DECIMAL(12, 2), nullable=False)
    score_a = Column(DECIMAL(6, 2), default=0)
    score_b = Column(DECIMAL(6, 2), default=0)
    recommended_apartment_id = Column(String(100), ForeignKey("apartments.id", ondelete="SET NULL", onupdate="CASCADE"), nullable=True)
    reason_text = Column(Text)
    total_cost_a = Column(DECIMAL(12, 2), default=0)
    total_cost_b = Column(DECIMAL(12, 2), default=0)
    created_at = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"))