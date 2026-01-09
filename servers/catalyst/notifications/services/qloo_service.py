import json
import os
import requests
import numpy as np
import torch
from typing import List, Tuple
from nltk.corpus import stopwords
from nltk import download as nltk_download
from catalyst.ai_resources import generate_embedding_from_text
from catalyst.constants import QLOO_URL,QLOO_URL_SEARCH,QLOO_URL_TAGS,MAX_RES_QLOO,MAX_QLOO_ITEMS,MOVIE_ENTITY,BOOK_ENTITY,TAG_TYPES,FALLBACK_TAGS
from dotenv import load_dotenv
import random
from urllib.parse import urlparse


if os.getenv("RENDER") != "true":
    load_dotenv()

QLOO_API_KEY = os.getenv('QLOO_API_KEY')
QLOO_BASE_URL = os.getenv('QLOO_BASE_URL', QLOO_URL)

if not QLOO_API_KEY:
    raise Exception("QLOO_API_KEY is missing. Please set it as an environment variable.")

try:
    _stopwords = set(stopwords.words('english'))
except LookupError:
    nltk_download('stopwords')
    _stopwords = set(stopwords.words('english'))


def pretty_print_json(data):
    print(json.dumps(data, indent=2))


def get_audience(endpoint: str) -> str:
    parsed = urlparse(endpoint)
    return f"{parsed.scheme}://{parsed.netloc}"


def extract_keywords(text: str) -> List[str]:
    tokens = [word.lower().strip(".,!?;:()[]\"'") for word in text.split()]
    keywords = [token for token in tokens if token and token not in _stopwords and len(token) > 2]
    seen = set()
    unique_keywords = []
    for kw in keywords:
        if kw not in seen:
            seen.add(kw)
            unique_keywords.append(kw)
    return unique_keywords


def normalize_interest(interest: str) -> str:
    return interest.strip().lower().replace("-", " ").replace("_", " ")


def cosine_similarity(candidate_emb: np.ndarray, existing_embeds: np.ndarray) -> np.ndarray:
    candidate_tensor = torch.tensor(candidate_emb).float()
    existing_tensor = torch.tensor(existing_embeds).float()

    candidate_norm = candidate_tensor / (candidate_tensor.norm(p=2) + 1e-10)
    existing_norms = existing_tensor / (existing_tensor.norm(dim=1, keepdim=True) + 1e-10)

    sims = torch.matmul(existing_norms, candidate_norm)
    return sims.cpu().numpy()


def deduplicate_interests(
    existing_list: List[str],
    existing_embeds: List[List[float]],
    new_candidates: List[str],
    similarity_threshold: float = 0.85
) -> List[Tuple[str, List[float]]]:
    clean_new = []
    normed_existing = [normalize_interest(i) for i in existing_list]
    arr_existing = np.array(existing_embeds) if existing_embeds else None

    for candidate in new_candidates:
        normed_candidate = normalize_interest(candidate)
        if normed_candidate in normed_existing:
            continue

        candidate_emb = generate_embedding_from_text(candidate)

        if arr_existing is not None and len(arr_existing) > 0:
            sims = cosine_similarity(np.array(candidate_emb), arr_existing)
            if (sims >= similarity_threshold).any():
                continue

        clean_new.append((normed_candidate, candidate_emb))
    return clean_new


def search_entities_by_name(keywords: List[str], types: List[str]) -> List[str]:
    base_url = QLOO_URL_SEARCH
    headers = {"X-Api-Key": QLOO_API_KEY, "Accept": "application/json"}
    entity_ids = set()

    for kw in keywords:
        params = {
            "query": kw,
            "types": types,
            "take": MAX_RES_QLOO
        }
        try:
            response = requests.get(base_url, params=params, headers=headers, timeout=5)
            response.raise_for_status()
            res_json = response.json()
            results = res_json.get("results", [])
            for entity in results:
                eid = entity.get("entity_id")
                if eid:
                    entity_ids.add(eid)
        except Exception as e:
            print(f"Entity search failed for '{kw}': {e}")
            continue
    return list(entity_ids)


def search_tags_by_keyword(keywords: List[str], tag_types: List[str]) -> List[str]:
    base_url = QLOO_URL_TAGS
    headers = {"X-Api-Key": QLOO_API_KEY, "Accept": "application/json"}
    tag_ids = set()

    for kw in keywords:
        params = {
            "filter.query": kw,
            "filter.tag.types": tag_types,
            "feature.typo_tolerance": "true",
            "take": MAX_RES_QLOO
        }
        try:
            response = requests.get(base_url, params=params, headers=headers, timeout=10) 
            response.raise_for_status()
            res_json = response.json()
            results = res_json.get("results")
            if isinstance(results, dict):
                tags = results.get("tags", [])
            elif isinstance(results, list):
                tags = results
            else:
                print(f"Warning: Unknown 'results' data type for keyword '{kw}': {type(results)}")
                tags = []

            for tag in tags:
                if not isinstance(tag, dict):
                    continue
                tid = tag.get("id") or tag.get("tag")
                if tid and isinstance(tid, str):
                    tag_ids.add(tid)

        except requests.exceptions.Timeout:
            print(f"Tag search timed out for keyword '{kw}', consider retrying or increasing timeout.")
            continue
        except Exception as e:
            print(f"Tag search failed for '{kw}': {e}")
            continue
    return list(tag_ids)

def fetch_qloo_interests(keywords: List[str]) -> List[dict]:
    if not keywords:
        return []

    entity_types = [
        BOOK_ENTITY,
        MOVIE_ENTITY
    ]
    tag_types = TAG_TYPES

    resolved_entities = search_entities_by_name(keywords, entity_types)
    resolved_tags = search_tags_by_keyword(keywords, tag_types)

    max_items = MAX_QLOO_ITEMS
    half_limit = max_items // 2

    num_entities = min(len(resolved_entities), half_limit)
    num_tags = min(len(resolved_tags), half_limit)

    leftover = max_items - (num_entities + num_tags)
    if leftover > 0:
        additional_entities = min(len(resolved_entities) - num_entities, leftover)
        num_entities += additional_entities
        leftover -= additional_entities
    if leftover > 0:
        additional_tags = min(len(resolved_tags) - num_tags, leftover)
        num_tags += additional_tags

    selected_entities = random.sample(resolved_entities, num_entities) if num_entities > 0 else []
    selected_tags = random.sample(resolved_tags, num_tags) if num_tags > 0 else []

    if not selected_entities and not selected_tags:
        fallback_tags = FALLBACK_TAGS
        selected_tags = fallback_tags[:max_items]

    interests = {}
    if selected_entities:
        interests["entities"] = [{"entity": eid, "weight": MAX_QLOO_ITEMS} for eid in selected_entities]
    if selected_tags:
        interests["tags"] = [{"tag": tid, "weight": MAX_QLOO_ITEMS} for tid in selected_tags]

    if not interests:
        return []

    available_types = []
    if selected_entities:
        if BOOK_ENTITY in entity_types:
            available_types.append(BOOK_ENTITY)
        if MOVIE_ENTITY in entity_types:
            available_types.append(MOVIE_ENTITY)
    else:
        available_types = [MOVIE_ENTITY]

    filter_type = random.choice(available_types) if available_types else MOVIE_ENTITY

    payload = {
        "filter": {
            "type": filter_type
        },
        "signal": {
            "interests": interests,
            "demographics": {
                "audiences": [
                    "urn:audience:life_stage:university",
                    "urn:audience:communities:india"
                ],
                "age": "18_to_25",
                "gender": ""
            },
            "location": "India"
        },
        "take": 5,
        "feature": {
            "explainability": True
        }
    }

    headers = {
        "X-Api-Key": QLOO_API_KEY,
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    try:
        response = requests.post(QLOO_BASE_URL, json=payload, headers=headers, timeout=10)
        response.raise_for_status()
        result = response.json()
        print(json.dumps(result, indent=2))
        interests_list = []
        for entity in result.get("results", {}).get("entities", []):
            interests_list.append({
                "entity_id": entity.get("entity_id"),
                "name": entity.get("name"),
                "type": entity.get("type"),
                "popularity": entity.get("popularity"),
                "tags": entity.get("tags"),
            })
        return interests_list
    except requests.RequestException as e:
        print(f"Qloo API error: {e}")
        if hasattr(e, "response") and e.response is not None:
            print(e.response.text)
        return []
