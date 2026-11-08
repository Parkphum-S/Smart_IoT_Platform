import time
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

router = APIRouter(prefix="/tuya", tags=["Tuya Cloud"])

tuya_config_store = {
    "clientId": "",
    "clientSecret": "",
    "region": "sg",
    "endpoint": "https://openapi.tuyasg.com"
}

class TuyaConfigRequest(BaseModel):
    clientId: str = Field(..., description="Tuya Client ID")
    clientSecret: str = Field(..., description="Tuya Client Secret")
    region: str = Field(default="sg", description="Data Center Region")
    endpoint: str = Field(default="https://openapi.tuyasg.com", description="API Endpoint URL")

@router.get("/config")
def get_tuya_config():
    tuya_config_store["endpoint"] = "https://openapi.tuyasg.com"
    return {"success": True, "data": tuya_config_store}

@router.post("/config")
def save_tuya_config(config: TuyaConfigRequest):
    global tuya_config_store
    tuya_config_store["clientId"] = config.clientId.strip() if config.clientId else ""
    tuya_config_store["clientSecret"] = config.clientSecret.strip() if config.clientSecret else ""
    tuya_config_store["region"] = "sg"
    tuya_config_store["endpoint"] = "https://openapi.tuyasg.com"
    return {"success": True, "message": "บันทึกการตั้งค่า Tuya สำเร็จ"}

@router.post("/sync-devices")
async def sync_tuya_devices():
    client_id = tuya_config_store.get("clientId", "").strip()
    client_secret = tuya_config_store.get("clientSecret", "").strip()

    if not client_id or not client_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ยังไม่ได้ตั้งค่า Tuya API Credentials"
        )

    # ใช้ Mock Data ทันที 100% เพื่อหลีกเลี่ยงปัญหา Network/Firewall ของเซิร์ฟเวอร์
    print("INFO: Operating in Mock Data mode due to external network restrictions.")
    mock_devices = [
        {
            "id": "mock_dev_001",
            "name": "Smart Living Room Light (Mock)",
            "category": "dj",
            "online": True,
            "status": [{"code": "switch_1", "value": True}]
        },
        {
            "id": "mock_dev_002",
            "name": "Smart Air Purifier (Mock)",
            "category": "kj",
            "online": True,
            "status": [{"code": "switch", "value": False}]
        },
        {
            "id": "mock_dev_003",
            "name": "Smart Temperature Sensor (Mock)",
            "category": "wsdcg",
            "online": True,
            "status": [{"code": "va_temperature", "value": 25}]
        }
    ]
    return {
        "success": True,
        "message": "ซิงค์อุปกรณ์สำเร็จ (โหมดจำลอง Mock Data เนื่องจากเครือข่ายภายนอกถูกจำกัด)",
        "devices": mock_devices
    }
