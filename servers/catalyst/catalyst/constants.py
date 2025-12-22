MAX_QUESTIONS_PER_ROADMAP = 20
TRANSFORMERS_MODEL = "all-MiniLM-L6-v2"
COLLECTION_NAME = "questions"
LLM_MODEL = "qwen-3-32b"
LLM_MODEL1 = "llama-4-scout-17b-16e-instruct"
QLOO_URL="https://hackathon.api.qloo.com/v2/insights"
QLOO_URL_SEARCH="https://hackathon.api.qloo.com/search"
QLOO_URL_TAGS="https://hackathon.api.qloo.com/v2/tags"
EMBED_ENDPOINT = "/embed"
EMBED_BASE = "EMBED_SERVICE_BASE"
ADDITIONAL_COMMENTS='additional_comments'
CATALYST_EMAIL="admin@catalystedutech.com"
NOTIFICATION_PROMPT_TEMPLATE="""
You are an assistant that generates short notification messages ONLY.

Rules:
- Output ONLY the final notification text
- DO NOT explain your reasoning
- DO NOT include thoughts, analysis, or meta commentary
- Maximum 2 sentences
- Keep it concise and engaging

User Interest: {interests}

Notification:
"""
LLM_TEMP=0.6
LLM_TEMP1=0.4
LLM_TEMP2=0.4
MAX_TOKENS=4096
MAX_TOKENS1=60
MAX_RES_QLOO=5
MAX_QLOO_ITEMS=10
MOVIE_ENTITY="urn:entity:movie"
BOOK_ENTITY="urn:entity:book"
TAG_TYPES=[
    "urn:tag:genre",
    "urn:tag:theme",
    "urn:tag:influence"
]
FALLBACK_TAGS=[
    "urn:tag:genre:qloo:pop_music",
    "urn:tag:genre:qloo:technology",
    "urn:tag:audience:qloo:university"
]

BATCH_SIZE = 5
SA_EMAIL = "TASKS_SA_EMAIL"
PROCESS_URL = "TASK_PROCESS_URL"

ASIA_SOUTH1 = "ASIA_SOUTH1"
NOTIFICATION_QUEUE = "NOTIF_QUEUE"
PROJECT_ID = "PID"
PENDING="pending"
SENT="sent"
FAILED="failed"
DELIVERY_STATUS="delivery_status"