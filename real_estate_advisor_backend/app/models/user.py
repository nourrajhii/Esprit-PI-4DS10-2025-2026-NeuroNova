from sqlalchemy import Column, Integer, String, TIMESTAMP, text
from app.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(150), nullable=False)
    email = Column(String(150), unique=True, nullable=False)
    role = Column(String(50), server_default="client")
    created_at = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"))