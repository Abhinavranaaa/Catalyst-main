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
MAX_TOKENS_ROADMAP=16384
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
This is a Qdrant cosine similarity from a topic-aware retrieval, pre-filtered above a
relevance floor. Use it as ONE input to your judgment, not as a gate.

The relevance decision is YOURS to make from three signals together:
  (a) `subject` of the bank vs the question's apparent subject
  (b) `topic` of the bank vs the concept the question's text is actually testing
  (c) the actual `question_text` and `options` — read them and judge whether mastering
      this item helps a learner master "{topic}" within "{subject}"
Do not defer to similarity_score alone in either direction. A high score can still be
off-topic (lexical match without conceptual fit); a moderate score can still be on-topic.

═══════════════════════════════════════════════
SELECTION POLICY  (DEFAULT ACTION = INCLUDE)
═══════════════════════════════════════════════
Your default action for every question is INCLUDE.

A question may be DROPPED ONLY if it triggers AT LEAST ONE explicit, named criterion
below. For every drop you make, you must internally pair the question with the exact
criterion code (C1–C5). If no criterion applies, you MUST INCLUDE the question.

ALLOWED DROP CRITERIA — exhaustive list, no others are valid. EVERY drop must be
listed in the output `dropped_questions` array with its code and a one-sentence reason.

  C1  OFF_SUBJECT
      After reading the question text, you judge the item belongs to a subject other
      than "{subject}" (e.g. a Biology item in a Mathematics bank). Reason must name
      the subject the question actually belongs to.
  C2  OFF_TOPIC
      After reading subject, topic, AND the actual question_text + options, you judge
      that mastering this item does NOT meaningfully help a learner master "{topic}"
      within "{subject}". Score is informational only — do not cite "low score" as
      the reason; cite WHAT concept the question tests and WHY that concept is outside
      "{topic}". Apply this strictly: if the concept is adjacent or foundational to
      "{topic}", KEEP it.
  C3  NEAR_VERBATIM_DUPLICATE
      Another retained question has NEARLY IDENTICAL wording (>90% word overlap) AND
      identical options. Conceptual overlap alone is NOT enough — varied phrasings
      of the same concept aid retention and MUST be kept.
  C4  UNUSABLE_TEXT
      `text` field is empty, null, or so corrupted that the question cannot be
      understood as a question by a competent reader.
  C5  UNUSABLE_ANSWER_KEY
      `options` is empty/null or has fewer than 2 entries, OR `correct_index` is
      null / < 0 / out of range for the options array.

DROPS THAT ARE NEVER ALLOWED — these are NOT valid reasons to drop a question:
- `difficulty` is null, missing, or "unknown" — difficulty is OPTIONAL metadata.
  Default any missing difficulty to "medium" and keep the question.
- `topic` is null, missing, or generic — infer a micro-topic from the text.
- `explanation` is null or missing — explanation is OPTIONAL metadata.
- `source`, `subject`, or any other metadata field is null or missing.
- "Too easy" or "too hard" — solved by ordering, not removal.
- "similarity_score is low" alone — must combine with C2.
- "Output is getting long" — block count is dynamic; retain everything valid.
- Any subjective preference, style, or aesthetic judgment.

ACCOUNTABILITY + RETENTION CONTRACT:
Let N = total questions in the input bank.
Let K = number of question_ids that appear in `blocks[*].questions[*]`.
Let D = number of question_ids that appear in `dropped_questions`.

HARD RULES (must hold or output is invalid):
  H1. EVERY input question_id MUST appear in EXACTLY ONE of `blocks` or
      `dropped_questions`. Silent drops are forbidden — no input ID may vanish
      without an explicit entry in `dropped_questions`.
  H2. K + D == N (every input is accounted for).
  H3. Hard retention floor: K >= ceil(N * 0.70). If you fall below this, you have
      over-dropped on judgment calls — re-examine your C2 and C3 decisions and
      restore borderline items.

SOFT TARGET: aim for K >= ceil(N * 0.85). It is acceptable to drop below 85%
ONLY when you can justify each drop with a clear C1/C2/C4/C5 reason. Quality
is the goal; high retention is preferred when quality is not compromised.

Self-audit BEFORE emitting JSON:
  1. Count N (input bank size).
  2. Count K (blocks) and D (dropped_questions). Verify K + D == N.
  3. Review every dropped item: can you write a one-sentence reason that
     references the question_text and topic? If not, restore it.
  4. If K / N < 0.70, you have over-curated — restore borderline items until
     you are at or above 70%.

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

BLOCK SIZING (dynamic, emerges from data — driven by retention contract):
- Block count is determined by the natural cluster structure of micro-topics × Bloom's
  levels. Do NOT pad to a target count. Do NOT trim to a target count.
- Each block contains 2–8 questions.
- Total blocks scale with input size. Rough guide: ceil(K / 6) blocks where K is the
  retained question count. For an input of 40+ questions expect 7–12 blocks, not 5–6.
- If you find yourself producing 5–6 blocks of 2 questions each from a 30+ question
  bank, you are under-retaining — revisit your drops.

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
  "dropped_questions": [
    {{
      "question_id": "<existing_id_from_input>",
      "criterion_code": "<one of: C1 | C2 | C3 | C4 | C5>",
      "reason": "<one sentence citing what the question tests and why it was dropped>"
    }}
  ],
  "learning_tips": "1–2 short, motivating, evidence-grounded study tips relevant to the user's profile."
}}

`dropped_questions` MUST be present. It is `[]` when nothing was dropped, otherwise
it contains an entry for every input ID not placed in blocks. K + D must equal N.

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




