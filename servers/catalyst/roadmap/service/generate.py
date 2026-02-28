from .profileSynthesis import fetchUsrProfile
from typing import Dict, Any, List, Optional
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain.schema import HumanMessage
import json
import logging
from langchain_cerebras import ChatCerebras
from langchain_openai import ChatOpenAI
import os
from dotenv import load_dotenv
from catalyst.constants import MAX_QUESTIONS_PER_ROADMAP, COLLECTION_NAME, LLM_MODEL_ROADMAP, MAX_TOKENS, LLM_TEMP2, ROADMAP_ID, PROMPT_TEMPLATE_V2, GROK_API_KEY,LLM_PROVIDER, GROK,PROMPT_TEMPLATE_V3, MAX_ROADMAPS_PER_WINDOW, WINDOW
from notifications.services import normalize_interest
from qdrant_client import QdrantClient
import torch
from catalyst.ai_resources import generate_embedding_from_text
from question.models import Question
import ast
from typing import Optional, Union
import re
from typing import Dict
from django.db import transaction
from roadmap.models import Roadmap, RoadmapQuestion, Question, RoadmapJob
from catalyst.utils import remove_think_blocks 
import uuid
import time
from practice.helper import fetchRoadmap,fetchJob
from django.core.exceptions import ValidationError
from catalyst.rate_limit.services import SlidingWindowRateLimitter



logger = logging.getLogger(__name__)
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.abspath(os.path.join(CURRENT_DIR, '..','..'))

if os.getenv("RENDER") != "true":
    load_dotenv(os.path.join(BASE_DIR, '.env'), override=True)

VECTOR_DB_URL = os.getenv("VECTOR_DB_URL")
VECTOR_DB_KEY = os.getenv("VECTOR_DB_KEY")
CEREBRAS_API_KEY = os.getenv("CEREBRAS_API_KEY")
GROK_API_KEY = os.getenv(GROK_API_KEY)
LLM_MODEL_ROADMAP = os.getenv(LLM_MODEL_ROADMAP)
client = QdrantClient(url=VECTOR_DB_URL, api_key=VECTOR_DB_KEY)

LLM_PROVIDER = os.getenv(LLM_PROVIDER, GROK)

if LLM_PROVIDER == "grok":
    llm = ChatOpenAI(
        model=LLM_MODEL_ROADMAP,
        api_key=GROK_API_KEY,
        base_url="https://api.groq.com/openai/v1",
        temperature=LLM_TEMP2,
        max_tokens=MAX_TOKENS
    )
else:
    llm = ChatCerebras(
        model_name=LLM_MODEL_ROADMAP,
        api_key=CEREBRAS_API_KEY,
        temperature=LLM_TEMP2,
        max_tokens=MAX_TOKENS
    )

if not VECTOR_DB_URL or not VECTOR_DB_KEY or not CEREBRAS_API_KEY:
    raise Exception("One or more critical environment variables (VECTOR_DB_URL, VECTOR_DB_KEY, CEREBRAS_API_KEY) are missing.")

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")



def generate_roadmap_json(user_id: str, subject: str, topic: str, additional_comments: str = None)->dict:
    # limiter = SlidingWindowRateLimitter(MAX_ROADMAPS_PER_WINDOW,WINDOW)
    # limiter.check(user_id)
    response = generate_roadmap(user_id,subject,topic,additional_comments)
    roadmap_formatted = response["formatted"]
    roadmap = response["raw"]
    roadmap_instance = save_roadmap_response(user_id, raw_roadmap_data=roadmap_formatted, raw_roadmap=roadmap,subject=subject,topic=topic)
    roadmap_formatted[ROADMAP_ID] = roadmap_instance.id
    return roadmap_instance


        

def generate_roadmap(user_id: str, subject: str, topic: str, additional_comments: str = None) -> dict:
    """
    Full pipeline: builds user profile, fetches questions, and composes roadmap via LLM or fallback.
    """
    try:
        start=time.time()
        summary = fetchUsrProfile(user_id)
        end=time.time()
        logger.info(f"profile summary latency: {end - start:.3f} seconds")
        qdrant_hits = fetch_relevant_questions(subject, topic, MAX_QUESTIONS_PER_ROADMAP, additional_comments)
        question_data = _fetch_question_metadata(qdrant_hits)
        question_set = _format_results(qdrant_hits, question_data)

        if not question_set:
            logger.warning("No relevant questions found. Falling back to generic roadmap.")
            return create_fallback_roadmap([])

        roadmap = generate_roadmap_blocks(
            llm=llm,
            user_profile=summary,
            subject=subject,
            topic=topic,
            additional_comments=additional_comments,
            questions=question_set
        )

        roadmap_formatted = reshape_roadmap_for_response(roadmap,question_data)


        return {
            "formatted": roadmap_formatted,
            "raw": roadmap
        }

    except Exception as e:
        logger.error(f"Critical failure in roadmap pipeline: {e}", exc_info=True)
        return create_fallback_roadmap([])


def fetch_relevant_questions(
    subject: str,
    topic: str,
    top_k: int,
    additional_comments: Optional[str] = ""
):
    """
    Retrieves the most relevant questions by querying a vector search index (Qdrant)
    using semantic similarity, then fetching rich metadata from the relational DB.
    """
    try:
        query_text = f"Subject: {subject}. Topic: {topic}. {additional_comments}".strip()
        query_vector = generate_embedding_from_text(query_text)
        qdrant_hits = _query_qdrant(query_vector, top_k)
        return qdrant_hits

    except Exception as e:
        logger.error(f"🔥 Failed to fetch relevant questions: {e}", exc_info=True)
        return []
    

def _query_qdrant(query_vector: List[float], top_k: int):
    """
    Queries Qdrant for top_k semantically similar items.
    """
    logger.info("🔍 Querying Qdrant...")
    start=time.time()
    results = client.search(
        collection_name=COLLECTION_NAME,
        query_vector=query_vector,
        limit=top_k,
        with_payload=False,
    )
    end=time.time()
    logger.info(f"Qdrant latency: {end - start:.3f} seconds")

    if not results:
        logger.warning("⚠️ No matching results found in Qdrant.")
        return []

    return results


def _fetch_question_metadata(results) -> Dict[str, Question]:
    """
    Fetches full question data from the SQL database using IDs from Qdrant.
    """
    ids = [str(hit.id) for hit in results]
    if not ids:
        return {}

    logger.info(f"📦 Fetching metadata for IDs: {ids}")
    start=time.time()
    questions = Question.objects.filter(id__in=ids)
    metadata = {str(q.id): q for q in questions}
    end = time.time()
    logger.info(f"Supabase latency question set: {end - start:.3f} seconds")
    missing_ids = set(ids) - set(metadata.keys())
    if missing_ids:
        logger.warning(f"🚫 Missing questions in DB for IDs: {missing_ids}")

    return metadata


def _format_results(results, question_metadata: Dict[str, Question]) -> List[Dict]:
    """
    Combines Qdrant similarity scores with full SQL metadata.
    """
    formatted = []

    for hit in results:
        q_id = str(hit.id)
        question = question_metadata.get(q_id)
        if not question:
            continue 

        formatted.append({
            "id": q_id,
            "text": question.text,
            "topic": question.topic or "unknown",
            "subject": question.subject or "unknown",
            "difficulty": question.difficulty or "medium",
            "source": question.source or "unknown",
            "options": question.options,
            "correct_index": question.correct_index,
            "similarity_score": round(1 - hit.score, 4)
        })

    logger.info(f"✅ Formatted {len(formatted)} questions from {len(results)} hits.")
    return formatted




def generate_roadmap_blocks(
    llm,
    user_profile: str,
    subject: str,
    topic: str,
    additional_comments: str,
    questions: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Uses LLM to dynamically group, filter, and order questions into a personalized learning roadmap.
    The prompt explicitly instructs the model to use the user profile for question synthesis and selection.
    """
    # Prepare question summaries with options
    questions_summary = [
        {
            "id": q["id"],
            "text": (q["text"][:200] + "...") if len(q["text"]) > 200 else q["text"],
            "difficulty": q.get("difficulty", "medium"),
            "topic": q.get("topic", "general"),
            "options": q.get("options", []),
            "similarity_score": round(q.get("similarity_score", 0.0), 3),
            "correct_index": q.get("correct_index",-1)
        }
        for q in questions[:MAX_QUESTIONS_PER_ROADMAP]
    ]

    # Explicit prompt with clear instructions on using user profile for selection and grouping
    template = PROMPT_TEMPLATE_V3
    prompt = PromptTemplate.from_template(template)

    try:
        formatted_prompt = prompt.format(
            user_profile=user_profile,
            subject=subject,
            topic=topic,
            additional_comments=additional_comments or "None",
            questions_data=json.dumps(questions_summary, indent=2)
        )

        start = time.time()

        response = llm.invoke([
            HumanMessage(content=formatted_prompt)
        ])

        end = time.time()
        latency = end - start

        response_text = response.content

        # ✅ Proper token extraction
        usage = response.response_metadata.get("token_usage", {})

        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)
        total_tokens = usage.get("total_tokens", 0)

        logger.info(
            f"LLM | model={LLM_MODEL_ROADMAP} | "
            f"prompt={prompt_tokens} | "
            f"completion={completion_tokens} | "
            f"total={total_tokens} | "
            f"latency={latency:.3f}s"
        )

        roadmap = parse_llm_response_to_json(response_text, debug_log=logger.debug)

        if not roadmap:
            logger.error("Roadmap output could not be parsed even after fallback.")
            return create_fallback_roadmap(questions)

        return roadmap

    except Exception as e:
        logger.error(f"LLM request failed: {e}", exc_info=True)
        return create_fallback_roadmap(questions)


def create_fallback_roadmap(
    questions: list,
    default_blocks: int = 5,
    questions_per_block: int = 4
) -> dict:
    """
    Deterministically partitions questions if LLM generation fails.
    """
    difficulty_order = {'easy': 1, 'medium': 2, 'hard': 3}
    sorted_questions = sorted(questions, key=lambda q: difficulty_order.get(q.get('difficulty', 'medium'), 2))
    blocks, idx = [], 0

    for block_num in range(1, default_blocks + 1):
        block_questions = []
        for _ in range(questions_per_block):
            if idx < len(sorted_questions):
                q = sorted_questions[idx]
                block_questions.append({
                    "question_id": q['id'],
                    "question_text": q['text'],
                    "options": q.get('options', []),
                    "correct_index": q.get('correct_index', 0),
                    "difficulty": q['difficulty'],
                    "topic": q['topic'],
                    "learning_objective": f"Understand key concept in {q['topic']}"
                })
                idx += 1
        blocks.append({
            "block_number": block_num,
            "block_title": f"Block {block_num}",
            "block_description": f"Step {block_num} topics.",
            "estimated_time": f"{15 + block_num * 5} minutes",
            "questions": block_questions
        })

    return {
        "roadmap_title": "Auto-Generated Learning Roadmap",
        "total_blocks": default_blocks,
        "estimated_duration": f"{default_blocks * 20} minutes",
        "difficulty_level": "mixed",
        "blocks": blocks,
        "learning_tips": "Begin with easier blocks, increase challenge as you gain confidence."
    }

def parse_llm_response_to_json(response: Union[str, dict], debug_log: Optional[callable] = None) -> Optional[dict]:
    """
    Gracefully parses LLM response into a valid JSON dict.
    Strips markdown fences, preamble, and attempts JSON parsing with fallback to ast.literal_eval.
    """
    if isinstance(response, dict):
        return response

    if not isinstance(response, str):
        response = str(response or "")

    cleaned = response.strip()

    cleaned = re.sub(r"^.*?\{", "{", cleaned, flags=re.DOTALL)


    cleaned = re.sub(r"```(?:json)?", "", cleaned).strip()
    
    first_json_brace = cleaned.find("{")
    if first_json_brace > 0:
        cleaned = cleaned[first_json_brace:]

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e1:
        if debug_log:
            debug_log(f"json.loads failed: {e1}")

        try:
            result = ast.literal_eval(cleaned)
            if isinstance(result, dict):
                return result
        except Exception as e2:
            if debug_log:
                debug_log(f"Fallback ast.literal_eval failed: {e2}")

    return None
        
def reshape_roadmap_for_response(raw_roadmap: dict,questions: Dict[str, Question]) -> dict:
    """
    Convert internal roadmap representation to the expected JSON response format,
    preserving your keys and setting isSaved and isExpanded to False.
    Pagination and metadata are omitted as requested.
    """
    roadmap_items = []
    difficulty_map={
        "easy":1,
        "medium":2,
        "hard":3
    }
    score_difficulty_map = {
        1: "Easy",
        2: "Medium",
        3: "Hard"
    }

    roadmap_difficulty = 0
    roadmap_question = 0
    for idx, block in enumerate(raw_roadmap.get("blocks", []), start=1):
        item = {
            "id": f"block-{idx:03d}", 
            "title": block.get("block_title", f"Block {idx}"),
            "summary": block.get("block_description", ""),
            "progressPercentage": 0,
            "isSaved": False,
            "isExpanded": False,
            "questions": []
        }
        score_diff = 0
        ct = 0
        for q in block.get("questions", []):
            qid = q.get("question_id")
            ques = questions.get(qid)

            if not ques:
                logger.warning(f"Question id {qid} not found in question lookup. Skipping.")
                continue
            score_diff+=difficulty_map[normalize_difficulty(ques.difficulty)]
            roadmap_difficulty+=score_diff
            ct+=1
            roadmap_question+=1
            if ques:
                question = {
                "id": q.get("question_id", ""),
                "question_text": q.get("question_text", ""),
                "options": ques.options,
                "topic": q.get("topic",""),
                "correct_index": ques.correct_index,
                "isBookmarked": False,
                "status": "unanswered",
                "difficulty": ques.difficulty
                }
            else: 
                logger.warning("No relevant questions found. skipping the q_id due to invalid q_id")
            
            item["questions"].append(question)

        avg_difficulty_score = round(score_diff / ct)
        item["difficulty"] = score_difficulty_map.get(
                avg_difficulty_score, "Medium"
            )

        roadmap_items.append(item)

    roadmap_difficulty = round(roadmap_difficulty/roadmap_question)
    avg_roadmap_difficulty = score_difficulty_map.get(avg_difficulty_score, "Medium")
    return {
        "roadmapItems": roadmap_items,
        "avg_difficulty": avg_roadmap_difficulty
    }

def save_roadmap_response(user_id: int, raw_roadmap_data: Dict,raw_roadmap: dict, subject:str, topic:str):
    """
    Saves the processed roadmap JSON into Roadmap model's `generated_json`,
    populates other roadmap fields (title, description if any),
    and creates/updates corresponding RoadmapQuestion links.
    
    Args:
        user_id: ID of the User to whom the roadmap belongs.
        raw_roadmap_data: Reformatted roadmap dictionary with 'roadmapItems' key.
    
    Returns:
        Roadmap instance updated or created.
    """
    unique_topics = extract_unique_topics(raw_roadmap,topic)

    title = raw_roadmap.get(
        "roadmap_title",
        raw_roadmap_data.get("roadmapItems", [{}])[0].get("title", "User Roadmap")
    )
    description = raw_roadmap.get("roadmap_description")

    with transaction.atomic():

        roadmap = Roadmap.objects.create(
            user_id=user_id,
            title=title,
            description=description,
            avg_difficulty = raw_roadmap_data.get("avg_difficulty","Medium"),
            generated_json=raw_roadmap_data,
            subject=subject,
            topics=unique_topics
        )
        question_id = set()
        for block in raw_roadmap_data.get("roadmapItems", []):
            for q in block.get("questions", []):
                qid = q.get("id")
                if not qid:
                    continue
                try:
                    question_uuid = uuid.UUID(qid)
                    question_id.add(question_uuid)
                except (ValueError, TypeError, AttributeError):
                    continue
        
        questions = Question.objects.in_bulk(question_id)
        roadmap_questions = [
            RoadmapQuestion(roadmap=roadmap,question=quest,status='unanswered')
            for quest in questions.values()
        ]
        RoadmapQuestion.objects.bulk_create(roadmap_questions,ignore_conflicts=True)

    return roadmap


def sync_roadmap_json_with_question_status(
    roadmap
) -> Dict:
    """
    Sync roadmap.generated_json with latest RoadmapQuestion.status
    Avoids N+1 queries and works for both create & fetch flows.
    """

    if not roadmap.generated_json:
        return {}

    roadmap_json = roadmap.generated_json

    roadmap_questions = (
        RoadmapQuestion.objects
        .filter(roadmap=roadmap)
        .only("question_id", "status")
    )

    status_map = {
        str(rq.question_id): rq.status
        for rq in roadmap_questions
    }

    for block in roadmap_json.get("roadmapItems", []):
        for q in block.get("questions", []):
            qid = q.get("id")
            if not qid:
                continue
            q["status"] = status_map.get(qid, "unanswered")

    return roadmap_json


def fetchRoadmapJson(roadmap_id: str) -> Dict:
    try:
        roadmap_uuid = uuid.UUID(roadmap_id)
    except (ValueError, TypeError):
        raise ValidationError(f"Invalid roadmap_id: {roadmap_id}")

    roadmap = fetchRoadmap(roadmap_id=roadmap_uuid)
    result = roadmap.generated_json
    result[ROADMAP_ID] = str(roadmap_uuid)
    return result

def fetchRoadmapJob(user_id:str,job_id:str)->dict:
    try:
        job_uuid = uuid.UUID(job_id)
    except (ValueError, TypeError):
        raise ValidationError(f"Invalid roadmap_id: {job_id}")
    
    job = fetchJob(job_uuid,user_id)
    if not job.roadmap:
        return {"status":job.status,"error_msg":job.error_message}
    else:
        result = dict(job.roadmap.generated_json)
        result[ROADMAP_ID] = str(job.roadmap.id)
        return {"status":job.status,"result":result,"error_msg":job.error_message}
        
    
    

    
    
    
    
def extract_unique_topics(raw_roadmap: dict, topic: str) -> list[str]:
    seen: set[str] = set()
    seen.add(topic)
    unique_topics: list[str] = []

    main_topic = normalize_interest(topic)
    if main_topic:
        seen.add(main_topic)
        unique_topics.append(main_topic)

    for block in raw_roadmap.get("blocks", []):
        for q in block.get("questions", []):
            raw_topic = q.get("topic", "")
            norm_topic = normalize_interest(raw_topic)

            if not norm_topic:
                continue

            if norm_topic in seen:
                continue

            seen.add(norm_topic)
            unique_topics.append(norm_topic)

    return unique_topics

def normalize_difficulty(difficulty: str) -> str:
    if not difficulty:
        return "medium"
    return difficulty.strip().lower()



# fox that error
# count only successful attempts


