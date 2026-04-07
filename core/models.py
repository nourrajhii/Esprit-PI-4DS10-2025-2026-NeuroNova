"""
models.py — Base de données SQLite avec SQLAlchemy (remplace MongoDB/Beanie)
Aucune installation de serveur requise — fichier local materiaux.db
"""
from sqlalchemy import create_engine, Column, String, Float, Boolean, DateTime, Text
from sqlalchemy.orm import DeclarativeBase, Session
from sqlalchemy.pool import StaticPool
import datetime
import os
from dotenv import load_dotenv

load_dotenv()


# ── Base SQLAlchemy ───────────────────────────────────────────────────────────
class Base(DeclarativeBase):
    pass


class Website(Base):
    __tablename__ = "websites"

    id          = Column(String, primary_key=True)
    name        = Column(String, nullable=False)
    base_url    = Column(String, nullable=False, unique=True)
    is_active   = Column(Boolean, default=False)
    created_at  = Column(DateTime, default=datetime.datetime.utcnow)


class MaterialListing(Base):
    __tablename__ = "material_listings"

    id              = Column(String, primary_key=True)
    website_id      = Column(String, nullable=False)
    source_type     = Column(String, default="ecommerce")

    # Identification
    title           = Column(String, nullable=False)
    category        = Column(String, default="autre")
    subcategory     = Column(String, nullable=True)
    brand           = Column(String, nullable=True)
    reference       = Column(String, nullable=True)

    # Prix
    price           = Column(Float, default=0.0)
    price_min       = Column(Float, nullable=True)
    price_max       = Column(Float, nullable=True)
    price_per_unit  = Column(Float, default=0.0)
    currency        = Column(String, default="TND")
    unit            = Column(String, default="unite")
    quantity        = Column(Float, default=1.0)

    # Faience/carrelage
    dimensions      = Column(String, nullable=True)
    tile_m2         = Column(Float, nullable=True)

    # Localisation
    city            = Column(String, nullable=True)
    supplier        = Column(String, nullable=True)

    # Disponibilite
    in_stock        = Column(Boolean, default=True)

    # Contenu
    description     = Column(Text, nullable=True)
    image_urls      = Column(Text, default="")   # JSON string
    listing_url     = Column(String, nullable=False)

    # Meta
    data_hash       = Column(String, nullable=False)
    scraped_at      = Column(DateTime, default=datetime.datetime.utcnow)


# ── Engine global ─────────────────────────────────────────────────────────────
_engine = None


def get_engine():
    global _engine
    if _engine is None:
        db_path = os.getenv("DATABASE_URL", "sqlite:///materiaux.db")
        # Si l'URL ne commence pas par sqlite, forcer SQLite
        if not db_path.startswith("sqlite"):
            db_path = "sqlite:///materiaux.db"
        _engine = create_engine(
            db_path,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            echo=False,
        )
        Base.metadata.create_all(_engine)
    return _engine


def get_session() -> Session:
    return Session(get_engine())


async def init_db():
    """Compatibilité avec le runner async — initialise SQLite."""
    get_engine()
    print("SQLite initialise : materiaux.db")