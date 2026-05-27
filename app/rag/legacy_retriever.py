from app.rag.embeddings import (
    generate_embedding
)

from app.rag.qdrant_client import (
    client,
    COLLECTION_NAME
)

from app.rag.query_rewriter import (
    rewrite_query
)


def retrieve_context(query: str):

    rewritten_query = rewrite_query(
        query
    )

    query_embedding = generate_embedding(
        rewritten_query
    )

    results = client.query_points(
        collection_name=COLLECTION_NAME,
        query=query_embedding,
        limit=8
    )

    contexts = []

    print("\n========== RETRIEVED ==========\n")

    for point in results.points:

        payload = point.payload

        print(
            f"\nTITLE: {payload.get('title')}"
        )

        print(
            f"SECTION: {payload.get('chunk_type')}"
        )

        print(payload["text"])

        contexts.append(
            payload["text"]
        )

    return "\n\n".join(contexts)