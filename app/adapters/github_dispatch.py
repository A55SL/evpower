import os
import logging
import httpx
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPO_OWNER = os.getenv("GITHUB_REPO_OWNER")
GITHUB_REPO_NAME = os.getenv("GITHUB_REPO_NAME")

GITHUB_DISPATCH_URL = (
    f"https://api.github.com/repos/{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}/dispatches"
)

HEADERS = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28"
}


# --- Validation Pipeline ---

async def dispatch_validation(charger_id: str, ocpp_variant: str, firmware_ver: str) -> None:
    payload = {
        "event_type": "validate_charger",
        "client_payload": {
            "charger_id": charger_id,
            "ocpp_variant": ocpp_variant,
            "firmware_ver": firmware_ver
        }
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                GITHUB_DISPATCH_URL,
                json=payload,
                headers=HEADERS,
                timeout=10.0
            )
            response.raise_for_status()
            logger.info(f"Validation dispatch sent | charger_id={charger_id} | status={response.status_code}")

    except httpx.HTTPStatusError as e:
        logger.error(f"GitHub dispatch failed | charger_id={charger_id} | status={e.response.status_code} | detail={e.response.text}")
        raise RuntimeError(f"Failed to dispatch validation workflow: {str(e)}")

    except httpx.RequestError as e:
        logger.error(f"GitHub dispatch request error | charger_id={charger_id} | error={str(e)}")
        raise RuntimeError(f"Network error when dispatching validation workflow: {str(e)}")


# --- OTA Update Pipeline ---

async def dispatch_ota_update(charger_id: str, current_version: str, target_version: str) -> None:
    payload = {
        "event_type": "ota_update",
        "client_payload": {
            "charger_id": charger_id,
            "current_version": current_version,
            "target_version": target_version
        }
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                GITHUB_DISPATCH_URL,
                json=payload,
                headers=HEADERS,
                timeout=10.0
            )
            response.raise_for_status()
            logger.info(f"OTA dispatch sent | charger_id={charger_id} | {current_version} -> {target_version} | status={response.status_code}")

    except httpx.HTTPStatusError as e:
        logger.error(f"OTA dispatch failed | charger_id={charger_id} | status={e.response.status_code} | detail={e.response.text}")
        raise RuntimeError(f"Failed to dispatch OTA workflow: {str(e)}")

    except httpx.RequestError as e:
        logger.error(f"OTA dispatch request error | charger_id={charger_id} | error={str(e)}")
        raise RuntimeError(f"Network error when dispatching OTA workflow: {str(e)}")