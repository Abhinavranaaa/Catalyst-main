
import os
from dotenv import load_dotenv
import time
import logging
from catalyst.service.embedService import EmbeddingService

logger = logging.getLogger(__name__)
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.abspath(os.path.join(CURRENT_DIR, '..'))

if os.getenv("RENDER") != "true":
    load_dotenv(os.path.join(BASE_DIR, '.env'), override=True)


HF_TOKEN = os.getenv('HF_TOKEN')
if not HF_TOKEN:
    raise RuntimeError("HF_TOKEN is not set in environment variables.")

embedding_service = EmbeddingService()

def generate_embedding_from_text(text: str) -> list[float]:
    """
    Generate embeddings for a given text using Hugging Face Inference API.
    """
    start = time.time()
    response = embedding_service.embed_text(text)
    end = time.time()
    logger.info(f"Hugging Face latency: {end - start:.3f} seconds")
    if isinstance(response, list) and len(response) > 0:
        return response[0]  # HF Inference sometimes wraps vectors in a list
    return response




