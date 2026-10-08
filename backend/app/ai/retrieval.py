from sqlalchemy.orm import Session
from app.ai.embeddings import get_embedding_client
from app.models.chunk import Chunk


def retrieve_relevant_chunks(
    db: Session,
    tender_id: int,
    organization_id: int,
    query: str,
    top_k: int = 5,
):
    """Retrieves top-k relevant chunks using vector similarity search."""
    embedder = get_embedding_client()
    query_embedding = embedder.embed_text(query)

    results = (
        db.query(Chunk)
        .filter(
            Chunk.tender_id == tender_id
        )
        .order_by(
            Chunk.embedding.cosine_distance(
                query_embedding
            )
        )
        .limit(top_k)
        .all()
    )

    return results


def format_retrieval_context(chunks: list[Chunk]) -> str:
    """Formats retrieved chunks into a unified context string for LLM."""
    if not chunks:
        return ""

    context_parts = []
    for idx, chunk in enumerate(chunks, 1):
        section_info = f"Section: {chunk.section}" if chunk.section else ""
        page_info = f"Page: {chunk.page_number}" if chunk.page_number else ""
        header = f"[Chunk {idx}] {section_info} {page_info}".strip()

        context_parts.append(f"{header}\n{chunk.content}")

    return "\n\n".join(context_parts)
