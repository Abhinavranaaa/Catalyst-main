from abc import ABC, abstractmethod
import os
import requests
from dotenv import load_dotenv

from catalyst import constants

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.abspath(os.path.join(CURRENT_DIR, "..", ".."))
if os.getenv("RENDER") != "true":
    load_dotenv(os.path.join(BASE_DIR, ".env"), override=True)

EMBED_BASE = os.getenv(constants.EMBED_BASE)
EMBED_SERVICE_SECRET = os.getenv("EMBED_SERVICE_SECRET", "").strip()

# google_id_token — Cloud Run IAM (current GCP prod)
# shared_secret  — AWS / Docker Compose (same host as API)
# none           — private network only (no Authorization header)
_explicit_mode = os.getenv("EMBED_AUTH_MODE", "").strip().lower()
if _explicit_mode:
    EMBED_AUTH_MODE = _explicit_mode
elif EMBED_SERVICE_SECRET:
    EMBED_AUTH_MODE = "shared_secret"
else:
    EMBED_AUTH_MODE = "google_id_token"


class AdapterProvider(ABC):
    @abstractmethod
    def generate_embedding(self, text: str) -> list[float]:
        pass


class EmbeddingServiceAdapter(AdapterProvider):
    """Client for catalyst-services embedding API (POST /embed)."""

    def __init__(self):
        self.service_url = (EMBED_BASE or "").rstrip("/")
        self.endpoint = constants.EMBED_ENDPOINT
        self.url = f"{self.service_url}{self.endpoint}" if self.service_url else ""
        if not self.service_url:
            raise RuntimeError("EMBED_SERVICE_BASE not configured")

        self._auth_request = None
        if EMBED_AUTH_MODE == "google_id_token":
            import google.auth.transport.requests

            self._auth_request = google.auth.transport.requests.Request()

    def _get_id_token(self) -> str:
        import google.oauth2.id_token

        try:
            return google.oauth2.id_token.fetch_id_token(
                self._auth_request, self.service_url
            )
        except Exception as exc:
            raise RuntimeError(f"Failed to obtain ID token: {exc}") from exc

    def _auth_headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if EMBED_AUTH_MODE == "none":
            return headers
        if EMBED_AUTH_MODE == "shared_secret":
            if not EMBED_SERVICE_SECRET:
                raise RuntimeError(
                    "EMBED_SERVICE_SECRET required when EMBED_AUTH_MODE=shared_secret"
                )
            headers["X-Embed-Secret"] = EMBED_SERVICE_SECRET
            headers["Authorization"] = f"Bearer {EMBED_SERVICE_SECRET}"
            return headers
        if EMBED_AUTH_MODE == "google_id_token":
            headers["Authorization"] = f"Bearer {self._get_id_token()}"
            return headers
        raise RuntimeError(f"Unknown EMBED_AUTH_MODE: {EMBED_AUTH_MODE}")

    def generate_embedding(self, text: str) -> list[float]:
        payload = {"text": text}

        try:
            response = requests.post(
                self.url,
                json=payload,
                headers=self._auth_headers(),
                timeout=30,
            )
            response.raise_for_status()
        except requests.exceptions.Timeout as exc:
            raise RuntimeError("Embedding service timeout") from exc
        except requests.exceptions.RequestException as exc:
            raise RuntimeError(f"Embedding service error: {exc}") from exc

        data = response.json()
        # catalyst-services returns EmbedResponse: {embeddings, model, dim}
        if isinstance(data, dict) and "embeddings" in data:
            vectors = data["embeddings"]
            if isinstance(vectors, list) and vectors:
                return vectors[0]
        if isinstance(data, list) and data:
            return data[0] if isinstance(data[0], list) else data
        raise ValueError(f"Unexpected embedding response format: {data}")
