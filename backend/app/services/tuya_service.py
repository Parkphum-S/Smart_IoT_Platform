import time
import hmac
import hashlib
import requests
from typing import Dict, Any, List

class TuyaOpenAPIClient:
    def __init__(self, client_id: str, client_secret: str, endpoint: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.endpoint = endpoint.rstrip("/")
        self.access_token = None

    def _calc_sign(self, client_id: str, secret: str, t: str, access_token: str = "", string_to_sign: str = "") -> str:
        if access_token:
            message = client_id + access_token + t + string_to_sign
        else:
            message = client_id + t + string_to_sign
            
        sign = hmac.new(
            secret.encode("utf-8"),
            message.encode("utf-8"),
            hashlib.sha256
        ).hexdigest().upper()
        return sign

    def get_access_token(self) -> str:
        t = str(int(time.time() * 1000))
        path = "/v1.0/token?grant_type=1"
        content_sha256 = hashlib.sha256("".encode("utf-8")).hexdigest()
        string_to_sign = f"GET\n{content_sha256}\n\n{path}"
        
        sign = self._calc_sign(self.client_id, self.client_secret, t, string_to_sign=string_to_sign)
        
        headers = {
            "client_id": self.client_id,
            "sign": sign,
            "t": t,
            "sign_method": "HMAC-SHA256"
        }
        
        url = f"{self.endpoint}{path}"
        response = requests.get(url, headers=headers)
        data = response.json()
        
        if data.get("success"):
            self.access_token = data["result"]["access_token"]
            return self.access_token
        else:
            raise Exception(f"Failed to authenticate with Tuya Cloud: {data.get('msg')}")

    def fetch_devices(self, uid: str) -> List[Dict[str, Any]]:
        if not self.access_token:
            self.get_access_token()
            
        t = str(int(time.time() * 1000))
        path = f"/v1.0/users/{uid}/devices"
        
        content_sha256 = hashlib.sha256("".encode("utf-8")).hexdigest()
        string_to_sign = f"GET\n{content_sha256}\n\n{path}"
        
        sign = self._calc_sign(self.client_id, self.client_secret, t, access_token=self.access_token, string_to_sign=string_to_sign)
        
        headers = {
            "client_id": self.client_id,
            "access_token": self.access_token,
            "sign": sign,
            "t": t,
            "sign_method": "HMAC-SHA256"
        }
        
        url = f"{self.endpoint}{path}"
        response = requests.get(url, headers=headers)
        data = response.json()
        
        if data.get("success"):
            return data.get("result", [])
        else:
            raise Exception(f"Failed to fetch devices: {data.get('msg')}")
