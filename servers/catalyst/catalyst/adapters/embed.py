from abc import ABC, abstractmethod
import os
import requests
import google.auth
import google.oauth2.id_token
import google.auth.transport.requests
from catalyst import constants
from dotenv import load_dotenv

class AdapterProvider(ABC):
    @abstractmethod
    def generate_embedding(self, text: str) -> list[float]:
        pass


CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.abspath(os.path.join(CURRENT_DIR, '..','..'))
if os.getenv("RENDER") != "true":
    load_dotenv(os.path.join(BASE_DIR, '.env'), override=True)
EMBED_BASE = os.getenv(constants.EMBED_BASE)

class EmbeddingServiceAdapter(AdapterProvider):
    def __init__(self):
        self.service_url = EMBED_BASE
        self.endpoint = constants.EMBED_ENDPOINT 
        self.url = self.service_url + self.endpoint
        if not self.url:
            raise RuntimeError("EMBED_SERVICE_URL not configured")

        self._auth_request = google.auth.transport.requests.Request()
    
    def _get_id_token(self):
        """Generate Google IAM ID token for Cloud Run auth"""
        try:
            return google.oauth2.id_token.fetch_id_token(
                self._auth_request, self.service_url
            )
        except Exception as exc:
            raise RuntimeError(f"Failed to obtain ID token: {exc}")

    def generate_embedding(self, text: str) -> list[float]:
        headers = {
            "Authorization": f"Bearer {self._get_id_token()}",
            "Content-Type": "application/json"
        }

        payload = {"text": text}

        try:
            response = requests.post(
                self.url,
                json=payload,
                headers=headers,
                timeout=15,  
            )
            response.raise_for_status()
        except requests.exceptions.Timeout:
            raise RuntimeError("Embedding service timeout")
        except requests.exceptions.RequestException as exc:
            raise RuntimeError(f"Embedding service error: {exc}")

        data = response.json()
        return data["embeddings"][0]