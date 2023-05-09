import base64
import hashlib
import hmac
import json

class Authenticator:
    def __init__(self):
        try:
            with open("TradeBot/api.json") as f:
                data = json.load(f)
                self.API_KEY = data["API_KEY"].encode("utf-8")
                self.API_SECRET = data["API_SECRET"].encode("utf-8")
        except Exception as e:
            raise Exception(f"Authenticator:__init__(): Loading JSON file error: {e}")


    def get_api_key(self) -> str:
        return self.API_KEY

    def get_api_secret(self) -> str:
        return self.API_SECRET

    def get_encoded_payload(self, payload: str) -> bytes:
        return base64.b64encode(payload.encode("utf-8"))

    def get_signature(self, payload: bytes) -> str:
        return hmac.new(self.API_SECRET, payload, hashlib.sha384).hexdigest()
