from sqlalchemy import Column, Integer, String, Text, DECIMAL, Date, TIMESTAMP, ForeignKey, text
from app.database import Base


class Material(Base):
    __tablename__ = "materials"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False)
    category = Column(String(100), nullable=False)
    subcategory = Column(String(100))
    unit = Column(String(50), nullable=False)
    unit_price_min = Column(DECIMAL(12, 3), default=0)
    unit_price_avg = Column(DECIMAL(12, 3), nullable=False)
    unit_price_max = Column(DECIMAL(12, 3), default=0)
    supplier = Column(String(150))
    city = Column(String(100))
    country = Column(String(100), default="Tunisia")
    last_update = Column(Date)
    source = Column(Text)
    confidence_score = Column(DECIMAL(3, 2), default=0.80)
    created_at = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"))


class MetalSpec(Base):
    __tablename__ = "metal_specs"

    id = Column(Integer, primary_key=True, index=True)
    material_id = Column(Integer, ForeignKey("materials.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False)
    metal_type = Column(String(100), nullable=False)
    grade = Column(String(50))
    dimension = Column(String(100))
    weight_per_meter = Column(DECIMAL(10, 3))
    corrosion_resistance = Column(String(100))
    usage_type = Column(String(150))
    created_at = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"))