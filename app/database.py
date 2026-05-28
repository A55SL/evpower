import os
from sqlalchemy import create_engine, Column, String, DateTime, Enum as SAEnum
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime, timezone
from dotenv import load_dotenv
from app.models import ChargerStatus, OTAResult

load_dotenv()

# --- Connection ---

MYSQL_USER = os.getenv("MYSQL_USER")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD")
MYSQL_HOST = os.getenv("MYSQL_HOST")
MYSQL_PORT = os.getenv("MYSQL_PORT", "3306")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE")

DATABASE_URL = (
    f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}"
    f"@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}"
)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# --- Tables ---

class ChargerStateDB(Base):
    __tablename__ = "chargers"

    charger_id = Column(String(100), primary_key=True, index=True)
    manufacturer = Column(String(100), nullable=False)
    model_name = Column(String(100), nullable=False)
    ocpp_variant = Column(String(50), nullable=False)
    firmware_ver = Column(String(50), nullable=False)
    status = Column(SAEnum(ChargerStatus), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class OTAEventDB(Base):
    __tablename__ = "ota_events"

    id = Column(String(36), primary_key=True)
    charger_id = Column(String(100), nullable=False)
    from_version = Column(String(50), nullable=False)
    to_version = Column(String(50), nullable=False)
    result = Column(SAEnum(OTAResult), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


# --- Helpers ---

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    Base.metadata.create_all(bind=engine)