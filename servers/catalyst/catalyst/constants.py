MAX_QUESTIONS_PER_ROADMAP = 20
TRANSFORMERS_MODEL = "all-MiniLM-L6-v2"
COLLECTION_NAME = "questions"
LLM_MODEL = "qwen-3-235b-a22b-instruct-2507"
LLM_MODEL_NOTIFICATIONS = "llama-3.1-8b"
LLM_MODEL_PROFILE = "llama-3.3-70b"
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
LLM_TEMP1=0.3
LLM_TEMP2=0.3
MAX_TOKENS=4096
MAX_TOKENS1=600
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
PROFILE_TEMPLATE_1="""
You are an assistant that produces SHORT learning profile summaries.

Rules:
- Output ONLY the final answer
- DO NOT include reasoning, analysis, or explanations
- Maximum 120 words total
- Use the exact format below
- No extra text before or after

FORMAT:
1. Learning Behavior:
<1-2 sentences>

2. Curriculum Adaptation:
<1-2 sentences>

3. Roadmap Tips:
- <tip 1>
- <tip 2>

USER DATA:
- Learning Streak: {learning_streak} days
- Strong Topics: {strong_topics}
- Weak Topics: {weak_topics}
- Average Accuracy: {average_accuracy}%
- Average Difficulty Attempted: {avg_difficulty}
- Average Time per Question: {average_time_per_question} seconds
- Taste Keywords List: {taste_keywords_list}
"""
PROFILE_TEMPLATE_2="""
        You are an expert AI learning coach. Analyze the following weekly metrics and generate a clear, 3-part summary:

        === USER PERFORMANCE DATA ===
        - Learning Streak: {learning_streak} days
        - Strong Topics: {strong_topics}
        - Weak Topics: {weak_topics}
        - Average Accuracy: {average_accuracy}%
        - Average Difficulty Attempted: {avg_difficulty}
        - Average Time per Question: {average_time_per_question} seconds
        - Taste Keywords List: {taste_keywords_list}

        === TASK ===
        1. Write a short paragraph summarizing the user's current learning behavior and style (e.g., cautious, fast-paced, high-achiever, etc.).
        2. Suggest how curriculum blocks should be adapted to this learner (e.g., start simple, mix topics, reinforce weaknesses first, etc.).
        3. Give 2-3 roadmap-specific tips that could help improve performance or motivation.

        Keep it concise, grounded in the data, and easy for an LLM or a human coach to reuse in a personalized roadmap.
        """

LAST_N_ATTEMPTS=5