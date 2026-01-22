import re
from rest_framework.response import Response
from rest_framework import status
import jwt
from rest_framework.exceptions import AuthenticationFailed


THINK_BLOCK_PATTERN = re.compile(
    r"<think>.*?</think>",
    flags=re.IGNORECASE | re.DOTALL
)

def remove_think_blocks(text: str) -> str:
    """
    Removes <think>...</think> blocks from LLM output.
    Does NOT modify sentence count, length, or formatting.
    """

    if not text:
        return ""

    # Remove <think> blocks
    return THINK_BLOCK_PATTERN.sub("", text).strip()

def authenticate(request)->str:
    token = request.COOKIES.get("jwt")
    if not token:
        raise AuthenticationFailed("Unauthenticated")
    try:
        payload = jwt.decode(token, "secret", algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise AuthenticationFailed("Unauthenticated")

    user_id = payload["id"]
    if not user_id:
        return Response(
            {"error": "Missing User ID in headers"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    return user_id

