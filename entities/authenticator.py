import base64
import hashlib
import hmac
import json

class Authenticator:
    def __init__(self):
        try:
            with open("api.json") as f:
                data = json.load(f)
                self.API_KEY = data["API_KEY"].encode("utf-8")
                self.API_SECRET = data["API_SECRET"].encode("utf-8")
        except Exception as e:
            print(F"Error: {e}")


    def get_api_key(self) -> str:
        return self.API_KEY

    def get_api_secret(self) -> str:
        return self.API_SECRET

    def get_encoded_payload(self, payload: str) -> str:
        return base64.b64encode(payload.encode("utf-8"))

    def get_signature(self, payload: str) -> str:
        return hmac.new(self.API_SECRET, payload, hashlib.sha384).hexdigest()
