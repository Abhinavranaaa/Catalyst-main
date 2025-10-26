# import logging
# from typing import List
# import torch
# from transformers import AutoTokenizer, AutoModel

# # Configure logging
# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)

# # Force CPU (Render free tier usually has no GPU)
# device = torch.device("cpu")

# # Load small paraphrase model (MiniLM ~22MB)
# MODEL_NAME = "sentence-transformers/paraphrase-MiniLM-L6-v2"
# logger.info(f"🚀 Loading model: {MODEL_NAME} on CPU (optimized for low RAM)")

# # Use float16 if supported to reduce memory
# dtype = torch.float16 if torch.backends.mps.is_available() else torch.float32

# tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
# model = AutoModel.from_pretrained(MODEL_NAME, torch_dtype=dtype).to(device)
# model.eval()  # inference only

# def generate_embedding_from_text(text: str) -> List[float]:
#     """Generate a semantic embedding vector from a single text string."""
#     inputs = tokenizer(
#         text,
#         return_tensors="pt",
#         truncation=True,
#         padding=True,
#         max_length=128  # shorter = less RAM
#     ).to(device)

#     with torch.no_grad():
#         output = model(**inputs)
#         # CLS pooling
#         cls_vector = output.last_hidden_state[:, 0, :]
#         return cls_vector.cpu().numpy()[0].tolist()

# def _generate_query_vector(subject: str, topic: str, additional_comments: str) -> List[float]:
#     """Generate a semantic embedding vector from subject, topic, and comments."""
#     query_text = f"Subject: {subject}. Topic: {topic}. {additional_comments}".strip()
#     logger.info(f"🧠 Generating embedding for: {query_text}")

#     inputs = tokenizer(
#         query_text,
#         return_tensors="pt",
#         truncation=True,
#         padding=True,
#         max_length=128
#     ).to(device)

#     with torch.no_grad():
#         output = model(**inputs)
#         cls_vector = output.last_hidden_state[:, 0, :]
#         return cls_vector.cpu().numpy()[0].tolist()

from huggingface_hub import InferenceClient
import os
from dotenv import load_dotenv
import time
import logging

logger = logging.getLogger(__name__)
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.abspath(os.path.join(CURRENT_DIR, '..'))

if os.getenv("RENDER") != "true":
    load_dotenv(os.path.join(BASE_DIR, '.env'), override=True)


HF_TOKEN = os.getenv('HF_TOKEN')
if not HF_TOKEN:
    raise RuntimeError("HF_TOKEN is not set in environment variables.")

client = InferenceClient(model="sentence-transformers/all-MiniLM-L6-v2", token=HF_TOKEN)

def generate_embedding_from_text(text: str) -> list[float]:
    """
    Generate embeddings for a given text using Hugging Face Inference API.
    """
    response = client.feature_extraction(text)
    if isinstance(response, list) and len(response) > 0:
        return response[0]  # HF Inference sometimes wraps vectors in a list
    return response

def _generate_query_vector(subject: str, topic: str, additional_comments: str) -> list[float]:
    """
    Generate a query vector by combining subject, topic, and extra comments.
    """
    query_text = f"Subject: {subject}. Topic: {topic}. {additional_comments}".strip()
    start = time.time()
    response = client.feature_extraction(query_text)
    end = time.time()
    logger.info(f"Hugging Face latency: {end - start:.3f} seconds")
    if isinstance(response, list) and len(response) > 0:
        return response[0]
    return response



