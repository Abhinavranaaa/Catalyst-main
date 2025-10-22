from .profileSynthesis import buildUserProfile
from typing import Dict, Any, List, Optional
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
import json
import logging
from langchain_cerebras import ChatCerebras
import os
from dotenv import load_dotenv
from catalyst.constants import MAX_QUESTIONS_PER_ROADMAP, COLLECTION_NAME, LLM_MODEL1, MAX_TOKENS, LLM_TEMP2
from qdrant_client import QdrantClient
import torch
from catalyst.ai_resources import _generate_query_vector
from question.models import Question
import ast
from typing import Optional, Union
import re
from typing import Dict
from django.db import transaction
from roadmap.models import Roadmap, RoadmapQuestion, Question
import uuid

logger = logging.getLogger(__name__)
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.abspath(os.path.join(CURRENT_DIR, '..'))

if os.getenv("RENDER") != "true":
    load_dotenv(os.path.join(BASE_DIR, '.env'), override=True)

VECTOR_DB_URL = os.getenv("VECTOR_DB_URL")
VECTOR_DB_KEY = os.getenv("VECTOR_DB_KEY")
CEREBRAS_API_KEY = os.getenv("CEREBRAS_API_KEY")
client = QdrantClient(url=VECTOR_DB_URL, api_key=VECTOR_DB_KEY)

llm = ChatCerebras(
        model_name=LLM_MODEL1, 
        api_key=CEREBRAS_API_KEY,
        temperature=LLM_TEMP2,
        max_tokens=MAX_TOKENS
    )

if not VECTOR_DB_URL or not VECTOR_DB_KEY or not CEREBRAS_API_KEY:
    raise Exception("One or more critical environment variables (VECTOR_DB_URL, VECTOR_DB_KEY, CEREBRAS_API_KEY) are missing.")

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")



def generate_roadmap(user_id: str, subject: str, topic: str, additional_comments: str = None) -> dict:
    """
    Full pipeline: builds user profile, fetches questions, and composes roadmap via LLM or fallback.
    """
    try:
        profile = buildUserProfile(user_id)
        question_set = fetch_relevant_questions(subject, topic, MAX_QUESTIONS_PER_ROADMAP, additional_comments)

        if not question_set:
            logger.warning("No relevant questions found. Falling back to generic roadmap.")
            return create_fallback_roadmap([])

        roadmap = generate_roadmap_blocks(
            llm=llm,
            user_profile=profile["summary"],
            subject=subject,
            topic=topic,
            additional_comments=additional_comments,
            questions=question_set
        )
        # save roadmap logic 
        return roadmap

    except Exception as e:
        logger.error(f"Critical failure in roadmap pipeline: {e}", exc_info=True)
        return create_fallback_roadmap([])


def fetch_relevant_questions(
    subject: str,
    topic: str,
    top_k: int,
    additional_comments: Optional[str] = ""
) -> List[Dict]:
    """
    Retrieves the most relevant questions by querying a vector search index (Qdrant)
    using semantic similarity, then fetching rich metadata from the relational DB.
    """
    try:
        query_vector = _generate_query_vector(subject, topic, additional_comments)
        qdrant_hits = _query_qdrant(query_vector, top_k)
        question_data = _fetch_question_metadata(qdrant_hits)
        return _format_results(qdrant_hits, question_data)

    except Exception as e:
        logger.error(f"🔥 Failed to fetch relevant questions: {e}", exc_info=True)
        return []
    

def _query_qdrant(query_vector: List[float], top_k: int):
    """
    Queries Qdrant for top_k semantically similar items.
    """
    logger.info("🔍 Querying Qdrant...")
    results = client.search(
        collection_name=COLLECTION_NAME,
        query_vector=query_vector,
        limit=top_k,
        with_payload=False,
    )

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

    questions = Question.objects.filter(id__in=ids)
    metadata = {str(q.id): q for q in questions}

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
            "similarity_score": round(q.get("similarity_score", 0.0), 3)
        }
        for q in questions[:MAX_QUESTIONS_PER_ROADMAP]
    ]

    # Explicit prompt with clear instructions on using user profile for selection and grouping
    template = """
        You are an expert education strategist and curriculum designer.

        You must generate a personalized learning roadmap based on the following:

        === USER PROFILE ===
        {user_profile}

        === LEARNING CONTEXT ===
        - Subject: {subject}
        - Topic: {topic}
        - Additional Comments: {additional_comments}

        === QUESTION BANK ===
        {questions_data}

        TASK:
        - Use the user profile to prioritize weak topics and adjust difficulty sequencing.
        - Drop redundant or irrelevant questions.
        - Organize questions into logical learning blocks of dynamic count and size.
        - You MAY add 1 synthetic question per block if needed for concept bridging, must be clearly labeled.
        - Each block must have a title, description, estimated time.
        - Each question must include id, text, difficulty, topic, 4 options, and a learning objective.
        - Start from easier concepts, progress to advanced.
        - STRICTLY output valid JSON, no extra text, no markdown, no prefix or suffix.

        OUTPUT FORMAT:
        {{
        "roadmap_title": "Personalized Learning Path for {topic}",
        "total_blocks": [calculated integer],
        "estimated_duration": "[e.g. '2 hours']",
        "difficulty_level": "[beginner/intermediate/advanced/mixed]",
        "blocks": [
            {{
            "block_number": 1,
            "block_title": "Block title",
            "block_description": "What this block covers and how it helps",
            "estimated_time": "30 minutes",
            "questions": [
                {{
                "question_id": "q123" or "synthetic_1",
                "question_text": "question text",
                "difficulty": "easy/medium/hard",
                "topic": "micro-topic",
                "options": ["option1", "option2", "option3", "option4"],
                "learning_objective": "Learner gains X"
                }}
            ]
            }}
        ],
        "learning_tips": "1-2 practical, motivational tips"
        }}

        ONLY output valid JSON. No markdown, no explanations, no extraneous text.
        """
    prompt = PromptTemplate.from_template(template)

    chain = LLMChain(llm=llm, prompt=prompt)
    try:
        response = chain.run({
            "user_profile": user_profile,
            "subject": subject,
            "topic": topic,
            "additional_comments": additional_comments or "None",
            "questions_data": json.dumps(questions_summary, indent=2)
        })

        response_text = response if isinstance(response, str) else str(response)
        roadmap = parse_llm_response_to_json(response_text, debug_log=logger.debug)

        if not roadmap:
            logger.error("⚠️ Roadmap output could not be parsed even after fallback.")
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

    # Remove common preamble lines (e.g., "Here is the JSON:")
    cleaned = re.sub(r"^.*?\{", "{", cleaned, flags=re.DOTALL)

    # Remove markdown code fences
    cleaned = re.sub(r"```(?:json)?", "", cleaned).strip()
    
    # Ensure we're starting with a JSON object
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
        
def reshape_roadmap_for_response(raw_roadmap: dict) -> dict:
    """
    Convert internal roadmap representation to the expected JSON response format,
    preserving your keys and setting isSaved and isExpanded to False.
    Pagination and metadata are omitted as requested.
    """
    roadmap_items = []
    for idx, block in enumerate(raw_roadmap.get("blocks", []), start=1):
        item = {
            "id": f"block-{idx:03d}", 
            "title": block.get("block_title", f"Block {idx}"),
            "summary": block.get("block_description", ""),
            "difficulty": block.get("difficulty", "Medium").capitalize() if "difficulty" in block else "Medium",
            "progressPercentage": 0,
            "isSaved": False,
            "isExpanded": False,
            "questions": []
        }

        for q in block.get("questions", []):
            question = {
                "id": q.get("question_id", ""),
                "title": q.get("question_text", "")[:50],
                "question_text": q.get("question_text", ""),
                "options": q.get("options", []),
                "correct_index": q.get("correct_index", 0),
                "isBookmarked": False,
                "difficulty": q.get("difficulty", "Medium").capitalize()
            }
            item["questions"].append(question)

        roadmap_items.append(item)

    return {
        "roadmapItems": roadmap_items,
    }

def save_roadmap_response(user_id: int, raw_roadmap_data: Dict):
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

    title = raw_roadmap_data.get(
        "roadmap_title",
        raw_roadmap_data.get("roadmapItems", [{}])[0].get("title", "User Roadmap")
    )
    description = raw_roadmap_data.get("description", "")

    with transaction.atomic():
        roadmap, created = Roadmap.objects.get_or_create(user_id=user_id, title=title)
        roadmap.description = description
        roadmap.generated_json = raw_roadmap_data
        roadmap.save()

        # Clear existing roadmap questions
        RoadmapQuestion.objects.filter(roadmap=roadmap).delete()

        for block in raw_roadmap_data.get("roadmapItems", []):
            for q in block.get("questions", []):
                qid = q.get("id")
                if not qid:
                    continue
                try:
                    question_uuid = uuid.UUID(qid)
                except (ValueError, TypeError, AttributeError):
                    continue

                try:
                    question_obj = Question.objects.get(id=question_uuid)
                except Question.DoesNotExist:
                    continue

                RoadmapQuestion.objects.create(
                    roadmap=roadmap,
                    question=question_obj,
                )

    return roadmap

