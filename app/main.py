import logging
from fastapi import FastAPI, Depends, HTTPException, Security
from fastapi.security.api_key import APIKeyHeader
from sqlalchemy.orm import Session
from contextlib import asynccontextmanager
import os
from dotenv import load_dotenv

from app.database import get_db, init_db
from app.models import (
    ChargerPayload,
    FirmwareUpdatePayload,
    ChargerStateResponse,
    HealthResponse
)
from app.services import (
    handle_telemetry,
    handle_validation_result,
    handle_firmware_update
)
from app.repository import get_charger, get_ota_history
from prometheus_fastapi_instrumentator import Instrumentator

load_dotenv()

# --- Logging ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)
logger = logging.getLogger(__name__)

# --- API Key Security ---
API_KEY = os.getenv("API_KEY")
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=True)

def verify_api_key(key: str = Security(api_key_header)):
    if key != API_KEY:
        logger.warning("Unauthorized request - invalid API key")
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    return key


# --- App Lifespan ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting EV Charger Integration Service")
    init_db()
    logger.info("Database tables initialized")
    yield
    logger.info("Shutting down EV Charger Integration Service")


# --- App ---
app = FastAPI(
    title="EV Charger Integration Service",
    description="Microservice for integrating third party EV chargers via OCPP negotiation and OTA updates",
    version="1.0.0",
    lifespan=lifespan
)

Instrumentator().instrument(app).expose(app)


# --- Routes ---

@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health(db: Session = Depends(get_db)):
    try:
        db.execute(__import__("sqlalchemy").text("SELECT 1"))
        db_status = "ok"
    except Exception:
        db_status = "unreachable"
    return HealthResponse(status="ok", database=db_status)


@app.post("/telemetry", tags=["Charger"], dependencies=[Depends(verify_api_key)])
async def receive_telemetry(
    payload: ChargerPayload,
    db: Session = Depends(get_db)
):
    try:
        result = await handle_telemetry(payload, db)
        return result
    except Exception as e:
        logger.error(f"Error handling telemetry | error={str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chargers/{charger_id}/validate", tags=["Charger"], dependencies=[Depends(verify_api_key)])
async def validation_result(
    charger_id: str,
    ocpp_variant: str,
    firmware_ver: str,
    db: Session = Depends(get_db)
):
    try:
        result = await handle_validation_result(charger_id, ocpp_variant, firmware_ver, db)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error handling validation | charger_id={charger_id} | error={str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.patch("/chargers/{charger_id}/firmware", tags=["Charger"], dependencies=[Depends(verify_api_key)])
async def firmware_update(
    charger_id: str,
    payload: FirmwareUpdatePayload,
    db: Session = Depends(get_db)
):
    try:
        result = await handle_firmware_update(charger_id, payload, db)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error handling firmware update | charger_id={charger_id} | error={str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/chargers/{charger_id}/status", response_model=ChargerStateResponse, tags=["Charger"], dependencies=[Depends(verify_api_key)])
async def get_status(
    charger_id: str,
    db: Session = Depends(get_db)
):
    charger = get_charger(db, charger_id)
    if not charger:
        raise HTTPException(status_code=404, detail=f"Charger {charger_id} not found")
    return charger


@app.get("/chargers/{charger_id}/ota-history", tags=["Charger"], dependencies=[Depends(verify_api_key)])
async def ota_history(
    charger_id: str,
    db: Session = Depends(get_db)
):
    history = get_ota_history(db, charger_id)
    if not history:
        raise HTTPException(status_code=404, detail=f"No OTA history found for charger {charger_id}")
    return history