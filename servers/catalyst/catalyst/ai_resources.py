import os
import time
import logging
from dotenv import load_dotenv

from catalyst.service.embedService import EmbeddingService

logger = logging.getLogger(__name__)
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.abspath(os.path.join(CURRENT_DIR, ".."))

if os.getenv("RENDER") != "true":
    load_dotenv(os.path.join(BASE_DIR, ".env"), override=True)

# Production default: internal embedding service (catalyst-services).
# Local-only escape hatch to avoid embed latency/cost: EMBED_PROVIDER=hf
EMBED_PROVIDER = os.getenv("EMBED_PROVIDER", "s2s").lower()

_hf_client = None
embedding_service = None

if EMBED_PROVIDER == "hf":
    from huggingface_hub import InferenceClient

    hf_token = os.getenv("HF_TOKEN")
    if not hf_token:
        raise RuntimeError("HF_TOKEN is required when EMBED_PROVIDER=hf")
    _hf_client = InferenceClient(
        model="sentence-transformers/all-MiniLM-L6-v2",
        token=hf_token,
    )
elif EMBED_PROVIDER == "s2s":
    embedding_service = EmbeddingService()
else:
    raise RuntimeError(f"Unknown EMBED_PROVIDER={EMBED_PROVIDER!r} (use s2s or hf)")


def generate_embedding_from_text(text: str) -> list[float]:
    if EMBED_PROVIDER == "s2s":
        start = time.time()
        vector = embedding_service.embed_text(text)
        logger.info("s2s embed latency: %.3fs", time.time() - start)
        return vector

    response = _hf_client.feature_extraction(text)
    if isinstance(response, list) and len(response) > 0:
        return response[0]
    return response
