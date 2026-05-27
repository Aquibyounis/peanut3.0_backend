import tiktoken

def count_tokens(text: str) -> int:
    try:
        encoding = tiktoken.get_encoding("cl100k_base")
        return len(encoding.encode(text))
    except Exception:
        return estimate_tokens(text)

def truncate_to_tokens(text: str, max_tokens: int) -> str:
    try:
        encoding = tiktoken.get_encoding("cl100k_base")
        tokens = encoding.encode(text)
        if len(tokens) <= max_tokens:
            return text
        return encoding.decode(tokens[:max_tokens])
    except Exception:
        words = text.split()
        max_words = int(max_tokens / 1.3)
        return " ".join(words[:max_words])

def estimate_tokens(text: str) -> int:
    return int(len(text.split()) * 1.3)
