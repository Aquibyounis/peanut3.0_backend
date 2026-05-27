from qdrant_client.models import (
    PointStruct
)

from app.rag.qdrant_client import (
    client,
    COLLECTION_NAME
)

from app.rag.embeddings import (
    generate_embedding
)

from app.rag.chunker import (
    create_semantic_chunks
)

from app.utils.json_loader import (
    load_json_files
)


def ingest_knowledge():

    documents = load_json_files()

    points = []

    point_id = 1

    for doc in documents:

        data = doc["data"]

        chunks = create_semantic_chunks(
            data
        )

        for chunk in chunks:

            text = chunk["text"]

            embedding = generate_embedding(
                text
            )

            if embedding is None:

                print(
                    f"Skipping invalid embedding: {doc['path']}"
                )

                continue

            point = PointStruct(
                id=point_id,
                vector=embedding,
                payload={
                    "entity_id": data.get(
                        "id"
                    ),
                    "type": data.get(
                        "type"
                    ),
                    "title": data.get(
                        "title"
                    ),
                    "chunk_type": chunk.get(
                        "chunk_type"
                    ),
                    "tags": data.get(
                        "tags",
                        []
                    ),
                    "technologies": data.get(
                        "technologies",
                        []
                    ),
                    "source": doc["path"],
                    "text": text
                }
            )

            points.append(point)

            print(
                f"Embedded chunk: {data.get('title')} -> {chunk.get('chunk_type')}"
            )

            point_id += 1

    if not points:

        print(
            "No valid points to ingest."
        )

        return

    client.upsert(
        collection_name=COLLECTION_NAME,
        points=points
    )

    print(
        f"\nSuccessfully ingested {len(points)} chunks."
    )


if __name__ == "__main__":

    ingest_knowledge()