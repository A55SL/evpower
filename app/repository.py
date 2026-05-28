from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime, timezone
from uuid import uuid4

from app.database import ChargerStateDB, OTAEventDB
from app.models import ChargerPayload, ChargerStatus, OTAResult


# --- Charger State ---

def get_charger(db: Session, charger_id: str) -> ChargerStateDB | None:
    return db.query(ChargerStateDB).filter(
        ChargerStateDB.charger_id == charger_id
    ).first()


def upsert_charger(db: Session, payload: ChargerPayload, status: ChargerStatus) -> ChargerStateDB:
    try:
        charger = get_charger(db, payload.charger_id)

        if charger:
            charger.manufacturer = payload.manufacturer
            charger.model_name = payload.model_name
            charger.ocpp_variant = payload.ocpp_variant
            charger.firmware_ver = payload.firmware_ver
            charger.status = status
            charger.updated_at = datetime.now(timezone.utc)
        else:
            charger = ChargerStateDB(
                charger_id=payload.charger_id,
                manufacturer=payload.manufacturer,
                model_name=payload.model_name,
                ocpp_variant=payload.ocpp_variant,
                firmware_ver=payload.firmware_ver,
                status=status,
            )
            db.add(charger)

        db.commit()
        db.refresh(charger)
        return charger

    except SQLAlchemyError as e:
        db.rollback()
        raise RuntimeError(f"Database error during upsert: {str(e)}")


def update_charger_status(db: Session, charger_id: str, status: ChargerStatus) -> ChargerStateDB | None:
    try:
        charger = get_charger(db, charger_id)
        if not charger:
            return None

        charger.status = status
        charger.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(charger)
        return charger

    except SQLAlchemyError as e:
        db.rollback()
        raise RuntimeError(f"Database error during status update: {str(e)}")


def update_charger_firmware(db: Session, charger_id: str, firmware_ver: str, status: ChargerStatus) -> ChargerStateDB | None:
    try:
        charger = get_charger(db, charger_id)
        if not charger:
            return None

        charger.firmware_ver = firmware_ver
        charger.ocpp_variant = firmware_ver
        charger.status = status
        charger.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(charger)
        return charger

    except SQLAlchemyError as e:
        db.rollback()
        raise RuntimeError(f"Database error during firmware update: {str(e)}")


# --- OTA Events ---

def log_ota_event(
    db: Session,
    charger_id: str,
    from_version: str,
    to_version: str,
    result: OTAResult | None = None
) -> OTAEventDB:
    try:
        event = OTAEventDB(
            id=str(uuid4()),
            charger_id=charger_id,
            from_version=from_version,
            to_version=to_version,
            result=result,
            created_at=datetime.now(timezone.utc)
        )
        db.add(event)
        db.commit()
        db.refresh(event)
        return event

    except SQLAlchemyError as e:
        db.rollback()
        raise RuntimeError(f"Database error during OTA log: {str(e)}")


def get_ota_history(db: Session, charger_id: str) -> list[OTAEventDB]:
    return db.query(OTAEventDB).filter(
        OTAEventDB.charger_id == charger_id
    ).order_by(OTAEventDB.created_at.desc()).all()