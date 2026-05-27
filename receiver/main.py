import os

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

load_dotenv()

GH_TOKEN = os.getenv("GH_TOKEN")
GH_OWNER = os.getenv("GH_OWNER")
GH_REPO = os.getenv("GH_REPO")

app = FastAPI(
    title="EV Charger Telemetry Receiver",
    description="Receives charger telemetry from Postman and kicks off GitHub Actions validation.",
    version="1.0.0",
)

# In-memory state store: charger_id -> current state dict
charger_states: dict[str, dict] = {}


class ChargerPayload(BaseModel):
    charger_id: str
    manufacture: str
    model_name: str
    ocpp_variant: str
    firmware_ver: str


class FirmwareUpdate(BaseModel):
    firmware_ver: str


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/charger/telemetry", status_code=202)
async def receive_telemetry(payload: ChargerPayload):
    """
    Accepts EV charger telemetry, stores initial state, and triggers
    Pipeline 1 (validation) via a GitHub repository_dispatch event.
    """
    if not all([GH_TOKEN, GH_OWNER, GH_REPO]):
        raise HTTPException(
            status_code=500,
            detail="Missing required env vars: GH_TOKEN, GH_OWNER, GH_REPO",
        )

    charger_states[payload.charger_id] = {
        **payload.model_dump(),
        "status": "pending_validation",
    }

    dispatch_url = f"https://api.github.com/repos/{GH_OWNER}/{GH_REPO}/dispatches"

    client_payload = payload.model_dump()
    client_payload["retry_count"] = 0

    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(
            dispatch_url,
            headers={
                "Authorization": f"Bearer {GH_TOKEN}",
                "Accept": "application/vnd.github.v3+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            json={
                "event_type": "validate-charger",
                "client_payload": client_payload,
            },
        )

    if response.status_code not in (200, 201, 204):
        raise HTTPException(
            status_code=502,
            detail=f"GitHub dispatch failed [{response.status_code}]: {response.text}",
        )

    return {
        "status": "dispatched",
        "event_type": "validate-charger",
        "charger_id": payload.charger_id,
        "github_status": response.status_code,
        "message": "Pipeline 1 (validation) has been triggered on GitHub Actions.",
    }


@app.patch("/charger/{charger_id}/firmware")
async def update_firmware(charger_id: str, update: FirmwareUpdate):
    """
    Called by Pipeline 2 (OTA update) to push the new firmware version back
    to the receiver. Postman can poll GET /charger/{id}/status to see the change.
    """
    if charger_id not in charger_states:
        raise HTTPException(
            status_code=404,
            detail=f"Charger '{charger_id}' not found. Send a telemetry payload first.",
        )

    old_firmware = charger_states[charger_id]["firmware_ver"]
    charger_states[charger_id]["firmware_ver"] = update.firmware_ver
    charger_states[charger_id]["status"] = "ota_applied"

    return {
        "charger_id": charger_id,
        "firmware_ver_before": old_firmware,
        "firmware_ver_after": update.firmware_ver,
        "status": "ota_applied",
        "message": f"Firmware updated from {old_firmware} to {update.firmware_ver}.",
    }


@app.get("/charger/{charger_id}/status")
async def get_status(charger_id: str):
    """
    Returns the current known state of a charger. Poll this from Postman
    to see the firmware version change after Pipeline 2 runs.
    """
    if charger_id not in charger_states:
        raise HTTPException(
            status_code=404,
            detail=f"Charger '{charger_id}' not found. Send a telemetry payload first.",
        )

    return charger_states[charger_id]
