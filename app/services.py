import logging
from sqlalchemy.orm import Session

from app.models import ChargerPayload, ChargerStatus, FirmwareUpdatePayload, OTAResult
from app.repository import (
    upsert_charger,
    update_charger_status,
    update_charger_firmware,
    log_ota_event,
    get_charger
)
from app.adapters.github_dispatch import dispatch_validation, dispatch_ota_update
from app.metrics import (
    telemetry_requests_total,
    validation_failures_total,
    ota_triggered_total,
    ota_success_total,
    ota_failed_total
)

logger = logging.getLogger(__name__)

# --- Supported OCPP versions ---
SUPPORTED_OCPP_VERSIONS = ["2.0.0", "2.0.1"]
TARGET_FIRMWARE_VERSION = "2.0.0"


# --- Telemetry ---

async def handle_telemetry(payload: ChargerPayload, db: Session) -> dict:
    logger.info(f"Telemetry received | charger_id={payload.charger_id} | ocpp={payload.ocpp_variant} | firmware={payload.firmware_ver}")
    telemetry_requests_total.inc()

    # Save to DB with CONFIG_STARTED
    upsert_charger(db, payload, ChargerStatus.CONFIG_STARTED)
    logger.info(f"Charger state set to CONFIG_STARTED | charger_id={payload.charger_id}")

    # Trigger validation pipeline
    await dispatch_validation(
        charger_id=payload.charger_id,
        ocpp_variant=payload.ocpp_variant,
        firmware_ver=payload.firmware_ver
    )

    return {
        "message": "Telemetry received. Validation pipeline triggered.",
        "charger_id": payload.charger_id,
        "status": ChargerStatus.CONFIG_STARTED
    }


# --- Validation Result (called back by GitHub Actions) ---

async def handle_validation_result(charger_id: str, ocpp_variant: str, firmware_ver: str, db: Session) -> dict:
    charger = get_charger(db, charger_id)
    if not charger:
        logger.warning(f"Validation result received for unknown charger | charger_id={charger_id}")
        raise ValueError(f"Charger {charger_id} not found")

    if ocpp_variant in SUPPORTED_OCPP_VERSIONS:
        update_charger_status(db, charger_id, ChargerStatus.CONFIG_SUCCESS)
        logger.info(f"Validation passed | charger_id={charger_id} | ocpp={ocpp_variant}")
        return {
            "message": "Validation successful. Charger registered.",
            "charger_id": charger_id,
            "status": ChargerStatus.CONFIG_SUCCESS
        }
    else:
        update_charger_status(db, charger_id, ChargerStatus.CONFIG_FAILED)
        validation_failures_total.inc()
        logger.warning(f"Validation failed | charger_id={charger_id} | ocpp={ocpp_variant} not in supported versions")

        # Trigger OTA pipeline
        log_ota_event(
            db,
            charger_id=charger_id,
            from_version=firmware_ver,
            to_version=TARGET_FIRMWARE_VERSION
        )
        update_charger_status(db, charger_id, ChargerStatus.INTEGRATION_STARTED)
        ota_triggered_total.inc()

        await dispatch_ota_update(
            charger_id=charger_id,
            current_version=firmware_ver,
            target_version=TARGET_FIRMWARE_VERSION
        )

        logger.info(f"OTA pipeline triggered | charger_id={charger_id} | {firmware_ver} -> {TARGET_FIRMWARE_VERSION}")
        return {
            "message": "Validation failed. OTA update pipeline triggered.",
            "charger_id": charger_id,
            "status": ChargerStatus.INTEGRATION_STARTED
        }


# --- OTA Result (called back by GitHub Actions) ---

async def handle_firmware_update(charger_id: str, payload: FirmwareUpdatePayload, db: Session) -> dict:
    charger = get_charger(db, charger_id)
    if not charger:
        logger.warning(f"OTA result received for unknown charger | charger_id={charger_id}")
        raise ValueError(f"Charger {charger_id} not found")

    if payload.result == OTAResult.SUCCESS:
        update_charger_firmware(db, charger_id, payload.firmware_ver, ChargerStatus.INTEGRATION_COMPLETED)
        ota_success_total.inc()
        logger.info(f"OTA success | charger_id={charger_id} | new firmware={payload.firmware_ver}")

        # Re-trigger validation for final handshake
        await dispatch_validation(
            charger_id=charger_id,
            ocpp_variant=payload.firmware_ver,
            firmware_ver=payload.firmware_ver
        )

        logger.info(f"Re-validation triggered after OTA | charger_id={charger_id}")
        return {
            "message": "OTA successful. Re-validation triggered.",
            "charger_id": charger_id,
            "status": ChargerStatus.INTEGRATION_COMPLETED
        }
    else:
        update_charger_status(db, charger_id, ChargerStatus.INTEGRATION_FAILED)
        ota_failed_total.inc()
        logger.warning(f"OTA failed | charger_id={charger_id}")
        return {
            "message": "OTA update failed.",
            "charger_id": charger_id,
            "status": ChargerStatus.INTEGRATION_FAILED
        }