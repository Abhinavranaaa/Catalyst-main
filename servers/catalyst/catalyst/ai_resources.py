
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

# can use infernce client for testing with hugging face

embedding_service = EmbeddingService()

def generate_embedding_from_text(text: str) -> list[float]:
    start = time.time()
    response = embedding_service.embed_text(text)
    end = time.time()
    logger.info(f"Hugging Face latency: {end - start:.3f} seconds")
    if isinstance(response, dict) and "embeddings" in response:
        return response["embeddings"][0]
    if isinstance(response, list) and len(response) > 0:
        return response[0]
    raise ValueError(f"Unexpected embedding response format: {response}")




