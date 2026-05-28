from pydantic import BaseModel
from enum import Enum


# --- Enums ---

class ChargerStatus(str, Enum):
    CONFIG_STARTED = "CONFIG_STARTED"
    CONFIG_SUCCESS = "CONFIG_SUCCESS"
    CONFIG_FAILED = "CONFIG_FAILED"
    INTEGRATION_STARTED = "INTEGRATION_STARTED"
    INTEGRATION_FAILED = "INTEGRATION_FAILED"
    INTEGRATION_COMPLETED = "INTEGRATION_COMPLETED"


class OTAResult(str, Enum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


# --- Request Models (what Postman sends) ---

class ChargerPayload(BaseModel):
    charger_id: str
    manufacturer: str
    model_name: str
    ocpp_variant: str
    firmware_ver: str


class FirmwareUpdatePayload(BaseModel):
    firmware_ver: str
    result: OTAResult


# --- Response Models (what your service returns) ---

class ChargerStateResponse(BaseModel):
    charger_id: str
    manufacturer: str
    model_name: str
    ocpp_variant: str
    firmware_ver: str
    status: ChargerStatus

    class Config:
        from_attributes = True


class HealthResponse(BaseModel):
    status: str
    database: str