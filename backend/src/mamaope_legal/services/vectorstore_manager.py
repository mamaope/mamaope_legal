from src.mamaope_legal.services.vectordb_service import ZillizService
from typing import Tuple, List
import time
import logging
import re, os

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Initialize ZillizService once
vectordb_service = ZillizService()
vectorstore_initialized = False

def initialize_vectorstore():
    """Initializes and loads the Zilliz collection at startup."""
    global vectorstore_initialized
    if not vectorstore_initialized:
        logger.info("Initializing and loading Zilliz collection...")
        try:
            vectordb_service.load_collection()
            vectorstore_initialized = True
            logger.info("Zilliz collection loaded and ready.")
        except Exception as e:
            error_message = f"CRITICAL: Could not load collection '{vectordb_service.collection_name}'. Error: {e}"
            logger.error(error_message)
            raise RuntimeError(error_message)

def find_best_heading(chunks: list[dict]) -> str:
    """
    Find the most likely section or article title
    among nearby chunks.
    """
    for c in chunks:
        text = c.get("content", "").strip()
        lines = text.splitlines()
        for line in lines:
            if len(line.split()) <= 12 and line.isupper():
                return line.title()
            if re.match(r'^(Article|Section|Clause|Chapter|Part)\s+\w+', line, re.IGNORECASE):
                return line.strip()
    return None


def enrich_retrieval_results(results, client, collection_name, neighbor_window=2):
    """
    Process Milvus retrieval results to attach inferred section titles
    and readable source labels dynamically.
    """
    enriched = []
    for hit in results:
        content = hit.get("content", "")
        page = hit.get("display_page_number", "")
        file_path = hit.get("file_path", "")
        
        # Look around this chunk to infer section title
        neighbors = client.query(
            collection_name=collection_name,
            filter=f"display_page_number == '{page}' and file_path == '{file_path}'",
            limit=neighbor_window * 2 + 1,
            output_fields=["content", "display_page_number"]
        )
        header = find_best_heading(neighbors)
        label = header or f"Page {page}"

        enriched.append({
            "label": label,
            "content": content.strip(),
            "page": page,
            "file_path": file_path
        })
    return enriched

def build_context(enriched_chunks: list[dict]) -> Tuple[str, List[str]]:
    """
    Build a well-formatted LLM context with clean source citations.
    """
    context_blocks, sources = [], []
    for item in enriched_chunks:
        src_name = os.path.basename(item["file_path"])
        block = (
            f"[SOURCE: {src_name} ({item['label']})]\n{item['content']}"
        )
        context_blocks.append(block)
        if src_name not in sources:
            sources.append(src_name)
    return "\n\n".join(context_blocks), sources

def search_all_collections(query: str, case_data: str, k: int = 3) -> Tuple[str, List[str]]:
    """
    Perform semantic retrieval and return optimized context for LLM.
    - Only top-k chunks (most relevant) are included.
    """
    start_time = time.time()
    client = vectordb_service.client
    collection_name = vectordb_service.collection_name

    if not vectorstore_initialized or not client:
        logger.error("Vector store not initialized.")
        raise RuntimeError("Vector store not initialized. Call initialize_vectorstore() first.")

    full_search_query = f"{query.strip()}\n{case_data.strip()}".strip()
    logger.info(f"🔍 Running semantic retrieval (query length={len(full_search_query)})")

    try:
        # OPTIMIZATION: Retrieve only 2x chunks instead of 5x for faster search
        # This reduces vector search time significantly
        raw_chunks, all_sources = vectordb_service.search_legal_knowledge(full_search_query, k=k*2)

        if not raw_chunks or not all_sources:
            logger.warning("No relevant context found by vectordb_service.")
            return [], []
        
        # OPTIMIZATION: Skip enrichment to avoid extra DB queries (saves 3-4 seconds)
        # Use raw chunks directly - they already have all needed information
        top_chunks = raw_chunks[:k]

        unique_top_sources = set()
        for chunk in top_chunks:
            unique_top_sources.add(os.path.basename(chunk.get("file_path", "Unknown document")))

        total_time = time.time() - start_time
        logger.info(f"📚 Retrieved {len(top_chunks)} top chunks in {total_time:.2f}s from {len(unique_top_sources)} sources.")
        return top_chunks, list(unique_top_sources)

    except Exception as e:
        logger.error(f"❌ Error during search_all_collections: {e}", exc_info=True)
        return [], []
