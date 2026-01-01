import re

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
