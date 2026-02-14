MAX_QUESTIONS_PER_ROADMAP = 30
TRANSFORMERS_MODEL = "all-MiniLM-L6-v2"
COLLECTION_NAME = "questions"
LLM_MODEL = "qwen-3-32b"
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
ROADMAP_ID = "roadmap_id"

PROMPT_TEMPLATE_V2 = """
You are an expert education strategist and curriculum designer.

Your sole task is to organize an existing question bank into a precise, personalized learning roadmap.
You MUST NOT create, invent, rephrase, or synthesize any new questions.

You must strictly follow all instructions and output ONLY valid JSON.

====================
USER PROFILE
====================
{user_profile}

====================
LEARNING CONTEXT
====================
Subject: {subject}
Primary Topic: {topic}
Additional Comments: {additional_comments}

====================
QUESTION BANK (SOURCE OF TRUTH)
====================
{questions_data}

IMPORTANT:
- You may ONLY use questions provided in the QUESTION BANK
- Every question_id in the output MUST exist in the input
- If a question is irrelevant, it must be DROPPED (not replaced)

====================
TASK
====================
1. Personalization & Progression
   - Analyze the user profile to identify strengths, gaps, and weak areas
   - Refine the learning progression to:
     - Start with foundational concepts
     - Gradually move to applied and advanced concepts
   - Adjust ordering and grouping to best fit the learner’s needs

2. Question Filtering & Ordering
   - Remove redundant or off-topic questions
   - Maintain a strict, continuous learning order:
     - Earlier blocks enable later blocks
     - No conceptual jumps or regressions
   - Preserve original question wording and intent

3. Learning Block Construction
   - Create a dynamic number of blocks
   - Block sizes and question counts may vary
   - Each block must group questions that:
     - Share the same core concept or micro-topic
     - Build logically on each other
   - Do NOT mix unrelated concepts in the same block

4. Question Integrity (STRICT)
   Each question MUST include:
   - question_id (from input only)
   - question_text (unchanged)
   - topic (specific micro-topic)
   - learning_objective (single, clear outcome)

====================
OUTPUT RULES (STRICT)
====================
- Output ONLY valid JSON
- No markdown
- No explanations
- No comments
- No trailing commas
- No additional keys outside the schema
- Maintain stable key ordering as shown below

====================
OUTPUT FORMAT
====================
{{
  "roadmap_title": "Personalized Learning Path for {topic}",
  "roadmap_description": "Two concise lines summarizing what the learner will master and how the roadmap progresses conceptually.",
  "total_blocks": <integer>,
  "estimated_duration": "<e.g. '2 hours'>",
  "difficulty_level": "<beginner | intermediate | advanced | mixed>",
  "blocks": [
    {{
      "block_number": 1,
      "block_title": "Block title",
      "block_description": "What this block covers and how it prepares the learner for the next block",
      "estimated_time": "30 minutes",
      "questions": [
        {{
          "question_id": "existing_question_id",
          "question_text": "Exact question text from input",
          "topic": "specific micro-topic",
          "learning_objective": "Learner gains X"
        }}
      ]
    }}
  ],
  "learning_tips": "1–2 short, practical and motivating tips"
}}

ONLY output valid JSON. No prefix. No suffix.
"""

PROMPT_TEMPLATE_V1 = """
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
            ""difficulty": "difficulty of the block that is the avarage difficulty of the questions in that block/item",
            "questions": [
                {{
                "question_id": "q123" or "synthetic_1",
                "question_text": "question text",
                "difficulty": "easy/medium/hard",
                "topic": "micro-topic",
                "options": ["option1", "option2", "option3", "option4"],
                "correct_index": "correct option for the question",
                "learning_objective": "Learner gains X"
                }}
            ]
            }}
        ],
        "learning_tips": "1-2 practical, motivational tips"
        }}

        ONLY output valid JSON. No markdown, no explanations, no extraneous text.
        """

ROADMAP_TITLE = "roadmap_title"
ROADMAP_DIFFICULTY = "avg_difficulty"
EASY = "Easy"
MEDIUM = "Medium"
HARD = "Hard"
ROADMAP_DESCRIPTION = "roadmap_description"
ROADMAP_ITEMS = "roadmapItems"
TITLE = "title"
DEFAULT_TITLE = "User Roadmap"
BLOCKS = "blocks"
QUESTIONS = "questions"
TOPIC = "topic"
QUESTION_ID = "question_id"
STATUS = "status"
ID = "id"
medium = "medium"
UNANSWERED = "unanswered"
QUESTION_TEXT = "question_text"
OPTIONS = "options"
CORRECT_INDEX = "correct_index"
IS_BOOKMARKED = "isBookmarked"
DIFFICULTY = "difficulty"
AVG_ROADMAP_DIFFICULTY = "avgRoadmapDifficulty"
SUMMARY = "summary"
PROGRESS_PERCENTAGE = "progressPercentage"
IS_SAVED = "isSaved"
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
IS_EXPANDED = "isExpanded"
LEARNING_OBJECTIVE = "learning_objective"
BLOCK_NUMBER = "block_number"
BLOCK_TITLE = "block_title"
BLOCK_DESC = "block_description"
ESTIMATED_TIME = "estimated_time"
USER_PROFILE = "user_profile"
SUBJECT = "subject"
ADDITIONAL_COMMENTS = "additional_comments"
QUESTIONS_DATA = "questions_data"
SIMILARITY_SCORE = "similarity_score"
TEXT = "text"
SOURCE = "source"
VECTOR_DB_URL = "VECTOR_DB_URL"
VECTOR_DB_KEY = "VECTOR_DB_KEY"
CEREBRAS_API_KEY = "CEREBRAS_API_KEY"
DIFFICULTY_LEVEL = "difficulty_level"
ESTIMATED_DURATION = "estimated_duration"
LEARNING_TIPS = "learning_tips"
TOTAL_BLOCKS = "total_blocks"
ALLOWED_OPERATORS = {"eq", "in", "gte", "lte", "gt", "lt"}
ALLOWED_SORT_ORDERS = {"asc", "desc"}

SORT_FIELD_MAP = {
    "created_at":"created_at",
    "modified_at":"modified_at",
    "progress_percntg":"progress_percntg"
}

FILTER_FIELD_MAP = {
    "difficulty":"avg_difficulty",
    "created_at":"created_at",
    "modified_at":"modified_at"
}




