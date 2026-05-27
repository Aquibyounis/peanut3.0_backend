def create_semantic_chunks(data):

    chunks = []

    title = data.get(
        "title",
        "Unknown"
    )

    chunk_fields = [
        "summary",
        "description",
        "architecture",
        "features",
        "technologies",
        "responsibilities",
        "concepts",
        "learnings",
        "keywords"
    ]

    for field in chunk_fields:

        value = data.get(field)

        if not value:
            continue

        if isinstance(value, list):

            value = "\n".join(
                [f"- {v}" for v in value]
            )

        chunk_text = f"""
TITLE:
{title}

SECTION:
{field}

CONTENT:
{value}
"""

        chunks.append(
            {
                "chunk_type": field,
                "text": chunk_text.strip()
            }
        )

    return chunks