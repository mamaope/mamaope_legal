import os
import time
import json
from typing import List, Dict, Tuple, Any
from dotenv import load_dotenv
from pymilvus import MilvusClient
import openai
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

load_dotenv()


class ZillizService:
    """Service for interacting with Zilliz Cloud."""
    def __init__(self):
        """Initializes the MilvusClient and Azure OpenAI client."""
        try:
            self.client = MilvusClient(
                uri=os.getenv('MILVUS_URI'),
                token=os.getenv('MILVUS_TOKEN')
            )
            self.collection_name = os.getenv('MILVUS_COLLECTION_NAME', 'legal_knowledge')
            self.azure_client = openai.AzureOpenAI(
                azure_endpoint=os.getenv('AZURE_OPENAI_ENDPOINT'),
                api_key=os.getenv('AZURE_OPENAI_API_KEY'),
                api_version=os.getenv('API_VERSION', '2024-02-01')
            )
            self.azure_deployment = os.getenv('DEPLOYMENT', 'text-embedding-3-large')
            logger.info("Milvus and Azure OpenAI clients initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize clients: {e}")
            raise

    def check_collection_exists(self) -> bool:
        """Checks if the configured collection exists in Zilliz."""
        try:
            exists = self.client.has_collection(self.collection_name)
            logger.info(f"Collection '{self.collection_name}' exists: {exists}")
            return exists
        except Exception as e:
            logger.error(f"Error checking for collection '{self.collection_name}': {e}")
            return False

    def generate_query_embedding(self, query: str) -> list[float]:
        """Generates a 3072-dim embedding for the query using Azure OpenAI."""
        try:
            embedding_start = time.time()
            query_length = len(query)
            logger.info(f"🔢 Starting embedding generation for query ({query_length} chars)...")
            
            response = self.azure_client.embeddings.create(
                input=[query],
                model=self.azure_deployment
            )
            embedding = response.data[0].embedding
            
            embedding_time = time.time() - embedding_start
            logger.info(f"✨ Embedding generation completed in {embedding_time:.3f}s - Vector dim: {len(embedding)}")
            return embedding
        except Exception as e:
            logger.error(f"Failed to generate query embedding: {e}")
            raise

    def _apply_mmr_diversity_reranking(self, search_results: list, k: int, lambda_param: float = 0.5) -> list:
        """
        Apply Maximal Marginal Relevance (MMR) diversity reranking to the search results.
        
        Args:
            search_results (list): List of search results to rerank.
            k (int): Number of results to return.
            lambda_param (float): Trade-off parameter between relevance and diversity (0 to 1).
            
        Returns:
            list: Reranked list of results.
        """

        if not search_results:
            return []
            
        search_results.sort(key=lambda x: x.get('distance', 0), reverse=True)
        return search_results[:k]

    def search_legal_knowledge(self, query: str, k: int = 5) -> Tuple[List[Dict[str, Any]], List[str]]:
        """
        Searches the legal knowledge collection using semantic similarity.
        Applies MMR diversity reranking to ensure balanced representation across sources.
        Returns context and source citations.
        
        Args:
            query: Search query text
            k: Number of results to return
        """
        search_total_start = time.time()
        logger.info(f"🔍 Starting legal knowledge search (k={k})...")
        
        if not self.check_collection_exists():
            logger.error("Collection not found.")
            return "Collection not found. Please ensure it is created and named correctly.", []

        try:
            # Step 1: Generate query embedding client-side
            embedding_start = time.time()
            query_embedding = self.generate_query_embedding(query)
            embedding_time = time.time() - embedding_start

            retrieve_k = min(k * 3, 30)
            vector_search_start = time.time()
            logger.info(f"🎯 Vector search in '{self.collection_name}' (retrieving {retrieve_k}, returning {k})...")
            
            search_results = self.client.search(
                collection_name=self.collection_name,
                data=[query_embedding],
                limit=retrieve_k,
                output_fields=["content", "file_path", "display_page_number"],
                search_params={"metric_type": "COSINE"}
            )
            
            vector_search_time = time.time() - vector_search_start
            logger.info(f"🎯 Vector search completed in {vector_search_time:.3f}s")

            if not search_results or not search_results[0]:
                logger.warning("No relevant legal information found.")
                return "No relevant legal information found in the knowledge base.", []

            # Step 3: Apply MMR diversity reranking
            rerank_start = time.time()
            reranked_results = self._apply_mmr_diversity_reranking(
                search_results[0], 
                k, 
                lambda_param=0.5
            )
            rerank_time = time.time() - rerank_start
            logger.info(f"🔄 MMR diversity reranking completed in {rerank_time:.3f}s")

            # Step 4: Process and format results
            processing_start = time.time()
            reranked_entities = []
            sources = set()
            total_content_length = 0
            
            for hit in reranked_results:
                entity = hit.get('entity', {})
                content = entity.get('content')

                if content:
                    reranked_entities.append(entity)
                    file_path = entity.get('file_path', 'Unknown document')
                    document_name = os.path.basename(file_path)                    
                    sources.add(document_name)
                    total_content_length += len(content)

            processing_time = time.time() - processing_start

            if not reranked_entities:
                logger.warning("No relevant content extracted from search results.")
                return [], []

            search_total_time = time.time() - search_total_start
            
            # Detailed timing breakdown for search operation
            logger.info(f"📊 SEARCH TIMING BREAKDOWN:")
            logger.info(f"   ├── Embedding Generation: {embedding_time:.3f}s ({embedding_time/search_total_time*100:.1f}%)")
            logger.info(f"   ├── Vector Search: {vector_search_time:.3f}s ({vector_search_time/search_total_time*100:.1f}%)")
            logger.info(f"   ├── MMR Reranking: {rerank_time:.3f}s ({rerank_time/search_total_time*100:.1f}%)")
            logger.info(f"   └── Result Processing: {processing_time:.3f}s ({processing_time/search_total_time*100:.1f}%)")
            logger.info(f"✅ Search completed in {search_total_time:.3f}s - Retrieved {len(reranked_entities)} chunks ({total_content_length} chars) from {len(sources)} unique sources")
            
            return reranked_entities, sorted(list(sources))

        except Exception as e:
            logger.error(f"Error during search in '{self.collection_name}': {e}")
            return f"An error occurred during search: {str(e)}", []

    def load_collection(self):
        """Loads the collection into memory for faster searches."""
        try:
            self.client.load_collection(self.collection_name)
            logger.info(f"Collection '{self.collection_name}' loaded successfully.")
        except Exception as e:
            logger.error(f"Failed to load collection '{self.collection_name}': {e}")
            raise     

vectordb_service = ZillizService()
