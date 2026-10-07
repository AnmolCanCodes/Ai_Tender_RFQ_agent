"""
LangGraph state machine orchestration for end-to-end tender document analysis.
Executes an audit-tracked DAG: Document Ingestion -> Chunking -> Overview Extraction
-> Categorized Requirement Extraction -> Result Compilation with error boundary checks.
"""

import logging
from typing import Any, TypedDict
from langgraph.graph import StateGraph, START, END

from app.ai.extraction import extract_requirements_from_chunks, extract_tender_overview
from app.ai.embeddings import get_embedding_client
from app.ingestion.cleaner import clean_page_text, remove_repetitive_headers_and_footers
from app.ingestion.chunker import ProcessedChunk, chunk_extracted_pages
from app.ingestion.pdf_loader import ExtractedPage, extract_text_from_pdf

logger = logging.getLogger("app.ai.graph")


class TenderAnalysisState(TypedDict):
    """Execution state tracked across LangGraph pipeline nodes."""
    tender_id: int
    organization_id: int
    document_id: int
    document_path: str
    extracted_text: str
    extracted_pages: list[dict[str, Any]]
    chunks: list[dict[str, Any]]
    tender_overview: dict[str, Any]
    requirements: list[dict[str, Any]]
    is_completed: bool
    error_message: str | None


def extract_document_node(state: TenderAnalysisState) -> dict[str, Any]:
    """Node 1: Safely extracts and cleans raw text pages from the PDF document."""
    doc_path = state["document_path"]
    try:
        pdf_res = extract_text_from_pdf(doc_path)
        raw_texts = [p.text for p in pdf_res.pages]
        cleaned_texts = remove_repetitive_headers_and_footers(raw_texts)

        pages_payload: list[dict[str, Any]] = []
        for idx, text in enumerate(cleaned_texts, 1):
            pages_payload.append({
                "page_number": idx,
                "text": text,
                "char_count": len(text),
            })

        full_text = "\n\n".join(cleaned_texts)
        return {
            "extracted_text": full_text,
            "extracted_pages": pages_payload,
        }
    except Exception as exc:
        logger.error("Document extraction node failed: %s", exc)
        return {
            "extracted_text": "",
            "extracted_pages": [],
            "error_message": f"PDF extraction failure: {exc}",
        }


def chunk_and_embed_node(state: TenderAnalysisState) -> dict[str, Any]:
    """Node 2: Segments text into procurement chunks and generates dense embeddings."""
    pages_data = state.get("extracted_pages", [])
    if not pages_data:
        return {"chunks": []}

    pages = [
        ExtractedPage(page_number=p["page_number"], text=p["text"], char_count=p["char_count"])
        for p in pages_data
    ]

    processed_chunks = chunk_extracted_pages(pages, chunk_size=1000, chunk_overlap=150)
    texts_to_embed = [c.content for c in processed_chunks]

    embedder = get_embedding_client()
    embeddings = embedder.embed_batch(texts_to_embed)

    chunk_dicts: list[dict[str, Any]] = []
    for c, emb in zip(processed_chunks, embeddings):
        chunk_dicts.append({
            "page_number": c.page_number,
            "section": c.section,
            "chunk_index": c.chunk_index,
            "content": c.content,
            "embedding": emb,
        })

    return {"chunks": chunk_dicts}


def extract_metadata_node(state: TenderAnalysisState) -> dict[str, Any]:
    """Node 3: Leverages LLM to extract high-level tender overview details."""
    text = state.get("extracted_text", "")
    if not text:
        return {"tender_overview": {}}

    overview = extract_tender_overview(text)
    return {"tender_overview": overview}


def extract_requirements_node(state: TenderAnalysisState) -> dict[str, Any]:
    """Node 4: Extracts categorized eligibility, financial, and technical requirements."""
    chunk_dicts = state.get("chunks", [])
    if not chunk_dicts:
        return {"requirements": []}

    reconstructed_chunks = [
        ProcessedChunk(
            page_number=c["page_number"],
            section=c.get("section"),
            chunk_index=c["chunk_index"],
            content=c["content"],
            char_count=len(c["content"]),
        )
        for c in chunk_dicts
    ]

    reqs = extract_requirements_from_chunks(reconstructed_chunks)
    return {"requirements": reqs}


def compile_results_node(state: TenderAnalysisState) -> dict[str, Any]:
    """Node 5: Finalizes graph execution and verifies completeness."""
    has_error = bool(state.get("error_message"))
    return {
        "is_completed": not has_error,
    }


def create_tender_analysis_graph() -> StateGraph:
    """Builds and wires the LangGraph StateGraph pipeline."""
    graph = StateGraph(TenderAnalysisState)

    graph.add_node("extract_document", extract_document_node)
    graph.add_node("chunk_and_embed", chunk_and_embed_node)
    graph.add_node("extract_metadata", extract_metadata_node)
    graph.add_node("extract_requirements", extract_requirements_node)
    graph.add_node("compile_results", compile_results_node)

    graph.add_edge(START, "extract_document")
    graph.add_edge("extract_document", "chunk_and_embed")
    graph.add_edge("chunk_and_embed", "extract_metadata")
    graph.add_edge("extract_metadata", "extract_requirements")
    graph.add_edge("extract_requirements", "compile_results")
    graph.add_edge("compile_results", END)

    return graph


# Compiled runnable graph
tender_analysis_app = create_tender_analysis_graph().compile()


def run_tender_analysis_graph(
    tender_id: int,
    organization_id: int,
    document_id: int,
    document_path: str,
) -> TenderAnalysisState:
    """
    Executes the full compiled LangGraph workflow synchronously.
    """
    initial_state: TenderAnalysisState = {
        "tender_id": tender_id,
        "organization_id": organization_id,
        "document_id": document_id,
        "document_path": document_path,
        "extracted_text": "",
        "extracted_pages": [],
        "chunks": [],
        "tender_overview": {},
        "requirements": [],
        "is_completed": False,
        "error_message": None,
    }

    result = tender_analysis_app.invoke(initial_state)
    return result
