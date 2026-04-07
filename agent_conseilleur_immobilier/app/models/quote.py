from sqlalchemy import Column, Integer, String, DECIMAL, TIMESTAMP, ForeignKey, text
from app.database import Base

class Quote(Base):
    __tablename__ = "quotes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL", onupdate="CASCADE"), nullable=True)
    apartment_id = Column(String(100), ForeignKey("apartments.id", ondelete="SET NULL", onupdate="CASCADE"), nullable=True)
    project_type = Column(String(100), nullable=False)
    surface_m2 = Column(DECIMAL(10, 2), default=0)
    subtotal_materials = Column(DECIMAL(12, 2), default=0)
    subtotal_labor = Column(DECIMAL(12, 2), default=0)
    subtotal_equipment = Column(DECIMAL(12, 2), default=0)
    contingency_cost = Column(DECIMAL(12, 2), default=0)
    total_cost = Column(DECIMAL(12, 2), default=0)
    created_at = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"))


class QuoteItem(Base):
    __tablename__ = "quote_items"

    id = Column(Integer, primary_key=True, index=True)
    quote_id = Column(Integer, ForeignKey("quotes.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False)
    material_id = Column(Integer, ForeignKey("materials.id", ondelete="SET NULL", onupdate="CASCADE"), nullable=True)
    item_name = Column(String(150), nullable=False)
    quantity = Column(DECIMAL(12, 3), nullable=False)
    unit = Column(String(50), nullable=False)
    unit_price = Column(DECIMAL(12, 3), nullable=False)
    subtotal = Column(DECIMAL(12, 2), nullable=False)
    created_at = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"))