from sqlalchemy import Column, String, DECIMAL, Integer, Text, TIMESTAMP, text
from app.database import Base

class Apartment(Base):
    __tablename__ = "apartments"

    id = Column(String(100), primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    price = Column(DECIMAL(12, 2), nullable=False)
    city = Column(String(100))
    property_type = Column(String(100))
    surface_m2 = Column(DECIMAL(10, 2))
    rooms = Column(Integer)
    bathrooms = Column(Integer)
    transaction_type = Column(String(50))
    url = Column(Text)
    created_at = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"))