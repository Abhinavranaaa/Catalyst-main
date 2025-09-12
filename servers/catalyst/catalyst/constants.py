MAX_QUESTIONS_PER_ROADMAP = 20
TRANSFORMERS_MODEL = "all-MiniLM-L6-v2"
COLLECTION_NAME = "questions"
LLM_MODEL = "llama-3.3-70b"
LLM_MODEL1 = "llama-4-maverick-17b-128e-instruct"
QLOO_URL="https://hackathon.api.qloo.com/v2/insights"
QLOO_URL_SEARCH="https://hackathon.api.qloo.com/search"
QLOO_URL_TAGS="https://hackathon.api.qloo.com/v2/tags"
ADDITIONAL_COMMENTS='additional_comments'
CATALYST_EMAIL="rmitu22@gmail.com"
NOTIFICATION_PROMPT_TEMPLATE="""
You are an intelligent assistant that creates concise and engaging learning notifications 
for users based on their interests. Use the following interests to craft a short notification message 
that motivates the user to continue learning:

User Interests: {interests}

Generate a relevant, motivating notification (max 2 sentences):
"""
LLM_TEMP=0.7
LLM_TEMP1=0.6
LLM_TEMP2=0.4
MAX_TOKENS=4096
MAX_TOKENS1=2048
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