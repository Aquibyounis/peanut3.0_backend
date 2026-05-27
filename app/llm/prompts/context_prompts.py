"""
Peanut 3.0 - Secondary Prompts
"""

QUERY_REWRITER_PROMPT = """
Rewrite this user query into an optimized semantic search query.
Expand related concepts naturally.
Keep response concise.

User Query:
{query}
"""

FOLLOWUP_GENERATION_PROMPT = """
Based on the following conversation, generate exactly 3 intelligent follow-up questions.

User asked: {query}
Assistant answered: {response}
Context: {context}

Rules:
- Questions must be contextually related
- Questions should help the user explore deeper
- Questions should be concise (under 15 words each)
- Return ONLY a JSON array of 3 strings, nothing else

Example output: ["What technologies were used in this project?", "How does the RAG pipeline handle edge cases?", "What was the biggest challenge?"]
"""

def build_query_rewrite_prompt(query: str) -> str:
    return QUERY_REWRITER_PROMPT.replace("{query}", query)

def build_followup_prompt(query: str, response: str, context: str = "") -> str:
    return (
        FOLLOWUP_GENERATION_PROMPT
        .replace("{query}", query)
        .replace("{response}", response[:500])
        .replace("{context}", context[:300])
    )
