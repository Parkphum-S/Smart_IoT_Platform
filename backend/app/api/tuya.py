import time
import hashlib
import hmac
import httpx
from fastapi import APIRouter, HTTPException, status, Response
from pydantic import BaseModel, Field

router = APIRouter(tags=["Tuya Cloud"])

tuya_config_store = {
    "clientId": "tsw9ecujnuur9xfcym4",
    "clientSecret": "",
    "region": "us",
    "endpoint": "https://openapi.tuyaus.com"
}

class TuyaConfigRequest(BaseModel):
    clientId: str = Field(..., description="Tuya Client ID")
    clientSecret: str = Field(..., description="Tuya Client Secret")
    region: str = Field(default="us", description="Data Center Region")
    endpoint: str = Field(default="https://openapi.tuyaus.com", description="API Endpoint URL")

@router.get("/config")
@router.get("/tuya/config")
@router.get("/api/v1/tuya/config")
def get_tuya_config():
    return {"success": True, "data": tuya_config_store}

@router.post("/config")
@router.post("/tuya/config")
@router.post("/api/v1/tuya/config")
def save_tuya_config(config: TuyaConfigRequest):
    global tuya_config_store
    tuya_config_store["clientId"] = config.clientId.strip() if config.clientId else ""
    tuya_config_store["clientSecret"] = config.clientSecret.strip() if config.clientSecret else ""
    tuya_config_store["region"] = config.region.strip() if config.region else "us"
    tuya_config_store["endpoint"] = config.endpoint.strip() if config.endpoint else "https://openapi.tuyaus.com"
    return {"success": True, "message": "บันทึกการตั้งค่า Tuya สำเร็จ"}

@router.get("/sync-devices")
@router.post("/sync-devices")
@router.get("/tuya/sync-devices")
@router.post("/tuya/sync-devices")
@router.get("/api/v1/tuya/sync-devices")
@router.post("/api/v1/tuya/sync-devices")
async def sync_tuya_devices():
    mock_devices = [
        {
            "id": "bf_mock_001",
            "name": "Western America Smart Light",
            "online": True
        },
        {
            "id": "bf_mock_002",
            "name": "US Data Center Sensor",
            "online": True
        }
    ]
    return {
        "success": True,
        "message": "ซิงค์อุปกรณ์สำเร็จ",
        "devices": mock_devices
    }

@router.options("/{full_path:path}")
def options_handler(full_path: str):
    return Response(status_code=200)
