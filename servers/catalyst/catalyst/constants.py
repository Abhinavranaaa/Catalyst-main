MAX_QUESTIONS_PER_ROADMAP = 30  # legacy — kept for reference
SIMILARITY_THRESHOLD = 0.60       # min cosine similarity to include a question (0–1)
MAX_QUESTIONS_FETCH_CAP = 120      # hard upper bound sent to Qdrant
TRANSFORMERS_MODEL = "all-MiniLM-L6-v2"
COLLECTION_NAME_CONSTANT = "COLLECTION_NAME_VDB"
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
MAX_TOKENS_ROADMAP=8192
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
US_CENTRAL1 = "US_CENTRAL1"
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

PROMPT_TEMPLATE_V3 = """
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

Each question includes a `similarity_score` (0.0–1.0). This is the cosine similarity between the
question and the requested topic. Higher means more topically relevant. Use this signal when deciding
which questions to drop — questions with a lower similarity_score should be dropped first when they
also fail the content rules below.

IMPORTANT:
- You may ONLY use questions provided in the QUESTION BANK
- Every question_id in the output MUST exist in the input
- If a question is irrelevant, it must be DROPPED (not replaced)
- You MUST evaluate ALL questions before constructing blocks
- Question selection must be deterministic and rule-based, not preference-based

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
   - Remove redundant or off-topic questions ONLY using the rules below
   - Maintain a strict, continuous learning order:
     - Earlier blocks enable later blocks
     - No conceptual jumps or regressions
   - Preserve original question wording and intent

   STRICT QUESTION SELECTION RULES:
   A question may be DROPPED ONLY if one or more of the following is true:
   - The question topic does not belong to the requested subject or primary topic
   - The question tests an identical concept already covered by an easier or clearer question
   - The question difficulty creates a progression break (advanced before foundation)
   - The question does not contribute to learning progression toward later blocks
   - The question is unrelated to the learner’s weak areas AND does not support core foundations
   - The question has a low similarity_score (below ~0.60) AND fails at least one of the above rules

   When two questions are otherwise equally valid, prefer the one with the higher similarity_score.
   DO NOT drop questions randomly.
   DO NOT drop questions solely because the set is large.
   Prefer keeping questions unless a rule above explicitly applies.

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

PROMPT_TEMPLATE_V4 = """
You are an expert curriculum designer applying Bloom's Taxonomy and learning-science
principles to organize a fixed question bank into a personalized roadmap.

CRITICAL: You ONLY arrange existing questions. You do NOT invent, rephrase, alter,
translate, or shorten any question text or option.

═══════════════════════════════════════════════
INPUTS
═══════════════════════════════════════════════
USER PROFILE
{user_profile}

LEARNING CONTEXT
- Subject: {subject}
- Primary Topic: {topic}
- Additional Comments: {additional_comments}

QUESTION BANK (every item is eligible by default)
{questions_data}

Each question carries a `similarity_score` ∈ [0.0, 1.0]. Higher = more topically relevant.
This is a Qdrant cosine similarity from a topic-aware retrieval. Treat it as a relevance
signal, NOT as a learning-quality signal. The bank has already been pre-filtered above a
relevance floor; do not re-filter aggressively on this score alone.

═══════════════════════════════════════════════
SELECTION POLICY  (DEFAULT ACTION = INCLUDE)
═══════════════════════════════════════════════
Your default action for every question is INCLUDE.

A question may be DROPPED ONLY if it triggers AT LEAST ONE explicit, named criterion
below. For every drop you make, you must internally pair the question with the exact
criterion code (C1–C5). If no criterion applies, you MUST INCLUDE the question.

ALLOWED DROP CRITERIA — exhaustive list, no others are valid:
  C1  OFF_SUBJECT
      The question's subject is unambiguously outside "{subject}".
  C2  OFF_TOPIC
      The question is unrelated to "{topic}" AND has similarity_score below 0.55.
      (Both conditions must hold. Low score alone is NOT sufficient.)
  C3  EXACT_DUPLICATE
      Another retained question tests the SAME concept at the SAME difficulty and
      would be redundant. When in doubt, KEEP both — varied phrasings aid retention.
  C4  LANGUAGE_BROKEN
      Question text is corrupted, truncated, or unparseable as natural language.
  C5  MISSING_OPTIONS
      `options` is empty/null OR `correct_index` is < 0.

DROPS THAT ARE NEVER ALLOWED:
- "Too easy" or "too hard" — solved by ordering, not removal.
- "similarity_score is low" alone — must combine with C2.
- "Output is getting long" — block count is dynamic; retain everything valid.
- Any subjective preference, style, or aesthetic judgment.

RETENTION FLOOR: at least 80% of input questions MUST appear in the final blocks
unless C1, C4, or C5 forced removals beyond that share. If you fall below 80% you
must reconsider your drops and add borderline cases back.

═══════════════════════════════════════════════
ORDERING POLICY  (BLOOM'S TAXONOMY + COGNITIVE SCAFFOLDING)
═══════════════════════════════════════════════
Map every retained question to ONE Bloom's level using its phrasing and difficulty:
  L1 REMEMBER    — recall, define, identify, list, state, name
  L2 UNDERSTAND  — explain, summarize, classify, paraphrase, give example
  L3 APPLY       — solve, compute, use, demonstrate (often "easy" numerical / direct)
  L4 ANALYZE     — compare, differentiate, derive, decompose (often "medium" multi-step)
  L5 EVALUATE    — justify, critique, choose best, validate (often "hard" reasoning)
  L6 CREATE      — design, formulate, combine into novel solution (rare in MCQ; allow if present)

ORDERING RULES (apply in priority order):
  1. MONOTONIC ASCENT
     Earlier blocks must target lower Bloom's levels than later blocks. No regression
     across blocks on the same micro-topic.
  2. INTRA-BLOCK COHERENCE
     Every question in a block must share a single micro-topic AND span at most TWO
     adjacent Bloom's levels (e.g. L2–L3, never L1–L4).
  3. INTERLEAVING FOR HABITUATION
     When a micro-topic has multiple questions at the same Bloom's level, place them
     adjacently inside the block. Repeated retrieval of the same concept in varied
     phrasings is the mechanism by which habituation forms.
  4. SPACED REINFORCEMENT
     A micro-topic introduced at L1–L2 in an early block may reappear in a later
     block at L3+ to consolidate it via retrieval practice. This is encouraged when
     the bank supports it.
  5. PROFILE-AWARE ENTRY POINT
     - If the user profile lists this topic among "weak_topics" or signals low
       accuracy, front-load L1–L2 blocks before advancing.
     - If the user profile lists this topic among "strong_topics" or signals high
       accuracy, you MAY compress L1 and start at L2–L3, but never skip a level
       entirely.
  6. NO ORPHANS
     If a micro-topic has only one question, attach it to the closest block by
     Bloom's level and conceptual proximity. Do NOT create singleton blocks.

BLOCK SIZING (dynamic, emerges from data):
- Block count is determined by the natural cluster structure of micro-topics × Bloom's
  levels. Do NOT pad to a target count. Do NOT trim to a target count.
- Each block contains 2–8 questions.
- Total blocks across the roadmap should typically fall between 4 and 10 for a 30-item
  bank, but may be more or fewer if the data dictates.

═══════════════════════════════════════════════
LEARNING-OBJECTIVE WRITING
═══════════════════════════════════════════════
Each `learning_objective` must:
- Be ONE sentence.
- Begin with a Bloom verb that matches the question's mapped level.
- Be specific to the question's micro-topic, not generic.
- NOT reveal the answer.
Examples (good): "Identify Newton's three laws by name and statement."
                 "Apply F = ma to a single-body system on an inclined plane."
                 "Compare static and kinetic friction in a block-on-block setup."
Examples (bad):  "Understand the topic." (too generic)
                 "The answer is 9.8 m/s²." (reveals answer)

═══════════════════════════════════════════════
OUTPUT CONTRACT (STRICT)
═══════════════════════════════════════════════
- Output EXACTLY one valid JSON object.
- No text before or after the JSON. No prose. No markdown fences. No code blocks.
- No `<think>`, `<analysis>`, or any tagged commentary blocks anywhere.
- Use double quotes only. No trailing commas. No comments inside JSON.
- Every `question_id` MUST be an exact string copied from the input bank.
- Every `question_text` MUST be the exact text from the input (no rephrasing, no truncation).
- Every `topic` per question MUST be a SPECIFIC micro-topic — do NOT just repeat "{topic}".
- Maintain the key order shown in the schema below.

═══════════════════════════════════════════════
OUTPUT FORMAT  (this exact schema, this exact key order)
═══════════════════════════════════════════════
{{
  "roadmap_title": "Personalized Learning Path for {topic}",
  "roadmap_description": "Two concise sentences: what the learner will master, and how the path progresses cognitively (e.g. Remember → Apply → Analyze → Evaluate).",
  "total_blocks": <integer>,
  "estimated_duration": "<e.g. '2 hours'>",
  "difficulty_level": "<beginner | intermediate | advanced | mixed>",
  "blocks": [
    {{
      "block_number": 1,
      "block_title": "Foundational micro-topic name",
      "block_description": "What this block trains, the Bloom's level it targets, and why it precedes the next block.",
      "estimated_time": "<e.g. '20 minutes'>",
      "questions": [
        {{
          "question_id": "<existing_id_from_input>",
          "question_text": "<exact text from input>",
          "topic": "<specific micro-topic>",
          "learning_objective": "<Bloom-verb sentence specific to this question>"
        }}
      ]
    }}
  ],
  "learning_tips": "1–2 short, motivating, evidence-grounded study tips relevant to the user's profile."
}}

OUTPUT ONLY THE JSON OBJECT.
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

LLM_MODEL_ROADMAP = "LLM_MODEL_ROADMAP"
LLM_MODEL_NOTIFICATIONS = "LLM_MODEL_NOTIFICATIONS"
LLM_MODEL_PROFILE = "LLM_MODEL_PROFILE"
GROK_API_KEY = "GROK_API_KEY"
OPENAI_API_KEY = "OPENAI_API_KEY"
LLM_PROVIDER = "LLM_PROVIDER"
GROK = "grok"
OPENAI = "openai"

SLIDING_WINDOW_LUA = """
local key = KEYS[1]
local limit = tonumber(ARGV[1])
local window = tonumber(ARGV[2])
local now = tonumber(ARGV[3])
local member = ARGV[4]

local window_start = now - window

-- Remove expired entries
redis.call("ZREMRANGEBYSCORE", key, 0, window_start)

-- Count current entries
local current = redis.call("ZCARD", key)

if current >= limit then
    return {0, current}
end

-- Add new request
redis.call("ZADD", key, now, member)

-- Ensure key expires eventually
redis.call("EXPIRE", key, window + 60)

return {1, current + 1}
"""

ROADMAP_QUEUE = 'ROADMAP_QUEUE'
ROADMAP_PROCESS_URL = 'ROADMAP_PROCESS_URL'
MAX_ROADMAPS_PER_WINDOW = 3
WINDOW = 86400
HEATMAP_DAYS=30
LLM_MODEL_ROADMAP = "LLM_MODEL_ROADMAP"




