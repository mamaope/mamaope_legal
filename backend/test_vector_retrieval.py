import os
import time
import sys
import logging
from datetime import datetime
from typing import List, Dict, Any, Tuple
from dotenv import load_dotenv
from src.mamaope_legal.services.vectordb_service import ZillizService
from src.mamaope_legal.services.vectorstore_manager import initialize_vectorstore, search_all_collections

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f'logs/vector_retrieval_test_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

def analyze_source_diversity(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze the diversity of sources in the results."""
    sources = {}
    for result in results:
        source = os.path.basename(result.get('file_path', 'unknown'))
        sources[source] = sources.get(source, 0) + 1
    
    return {
        'unique_sources': len(sources),
        'source_distribution': sources,
        'most_common_source': max(sources.items(), key=lambda x: x[1]) if sources else None,
        'distribution_stats': {
            'min': min(sources.values()) if sources else 0,
            'max': max(sources.values()) if sources else 0,
            'avg': sum(sources.values()) / len(sources) if sources else 0
        }
    }

def run_vector_retrieval_test(
    test_queries: List[str],
    k_values: List[int] = [3, 5, 10],
    case_data: str = ""
) -> None:
    """
    Run comprehensive tests on vector retrieval system.
    
    Args:
        test_queries: List of test queries to evaluate
        k_values: Different numbers of results to retrieve
        case_data: Optional case data to include in context
    """
    # Initialize vector store
    logger.info("🚀 Initializing vector store...")
    initialize_vectorstore()
    vectordb = ZillizService()
    
    # Get direct access to Milvus client for raw search results
    milvus_client = vectordb.client
    collection_name = vectordb.collection_name
    
    overall_start = time.time()
    total_queries = len(test_queries) * len(k_values)
    completed = 0
    
    logger.info(f"\n{'='*80}\n📊 STARTING VECTOR RETRIEVAL TEST\n{'='*80}")
    logger.info(f"Test configuration:")
    logger.info(f"- Number of queries: {len(test_queries)}")
    logger.info(f"- K values tested: {k_values}")
    logger.info(f"- Case data length: {len(case_data)} chars")
    
    test_results = []
    
    for query in test_queries:
        for k in k_values:
            test_start = time.time()
            logger.info(f"\n{'='*50}")
            logger.info(f"Testing query: '{query}' (k={k})")
            
            try:
                # Generate query embedding once
                query_embedding = vectordb.generate_query_embedding(query)
                
                # Perform RAW search to get actual cosine similarity scores from Milvus
                search_start = time.time()
                logger.info(f"🔍 Performing raw vector search for similarity analysis...")
                
                raw_search_results = milvus_client.search(
                    collection_name=collection_name,
                    data=[query_embedding],
                    limit=k,
                    output_fields=["content", "file_path", "display_page_number"],
                    search_params={"metric_type": "COSINE"}
                )
                
                search_time = time.time() - search_start
                
                # Analyze results
                if raw_search_results and raw_search_results[0]:
                    results = raw_search_results[0]
                    
                    # Extract ACTUAL cosine similarities from Milvus search results
                    # These are the real similarity scores between query and stored embeddings
                    similarities = []
                    result_details = []
                    
                    for hit in results:
                        # Milvus returns the cosine similarity in the 'distance' field
                        # For COSINE metric, higher distance = more similar (range typically -1 to 1, normalized to 0-1)
                        similarity = hit.get('distance', 0.0)
                        similarities.append(similarity)
                        
                        entity = hit.get('entity', {})
                        result_details.append({
                            'content': entity.get('content', ''),
                            'file_path': entity.get('file_path', 'Unknown'),
                            'page': entity.get('display_page_number', 'N/A'),
                            'similarity': similarity
                        })
                    
                    avg_similarity = sum(similarities) / len(similarities) if similarities else 0
                    max_similarity = max(similarities) if similarities else 0
                    min_similarity = min(similarities) if similarities else 0
                    
                    # Analyze source diversity
                    diversity_metrics = analyze_source_diversity(result_details)
                    
                    # Log detailed results
                    logger.info(f"\n{'='*60}")
                    logger.info(f"RESULTS ANALYSIS:")
                    logger.info(f"{'='*60}")
                    logger.info(f"- Retrieved chunks: {len(result_details)}")
                    logger.info(f"- Search time: {search_time:.3f}s")
                    logger.info(f"- ACTUAL Cosine Similarity (from Vector DB):")
                    logger.info(f"  • Average: {avg_similarity:.4f}")
                    logger.info(f"  • Maximum: {max_similarity:.4f}")
                    logger.info(f"  • Minimum: {min_similarity:.4f}")
                    logger.info(f"  • Range: {max_similarity - min_similarity:.4f}")
                    logger.info(f"- Source diversity:")
                    logger.info(f"  • Unique sources: {diversity_metrics['unique_sources']}")
                    logger.info(f"  • Source distribution: {diversity_metrics['source_distribution']}")
                    
                    # Interpret similarity scores
                    logger.info(f"\n📊 Similarity Interpretation:")
                    if avg_similarity >= 0.8:
                        logger.info(f"   ✅ EXCELLENT: High semantic relevance")
                    elif avg_similarity >= 0.6:
                        logger.info(f"   ✓ GOOD: Moderate semantic relevance")
                    elif avg_similarity >= 0.4:
                        logger.info(f"   ⚠️  FAIR: Low semantic relevance")
                    else:
                        logger.info(f"   ❌ POOR: Very low semantic relevance")
                    
                    # Store test results
                    test_results.append({
                        'query': query,
                        'k': k,
                        'num_results': len(result_details),
                        'search_time': search_time,
                        'avg_similarity': avg_similarity,
                        'max_similarity': max_similarity,
                        'min_similarity': min_similarity,
                        'diversity_metrics': diversity_metrics
                    })
                    
                    # Print sample results with actual similarities
                    logger.info(f"\n{'='*60}")
                    logger.info(f"TOP RESULTS WITH SIMILARITY SCORES:")
                    logger.info(f"{'='*60}")
                    for i, detail in enumerate(result_details[:3], 1):
                        logger.info(f"\n[Result {i}] Similarity: {detail['similarity']:.4f}")
                        logger.info(f"Source: {os.path.basename(detail['file_path'])} (Page {detail['page']})")
                        logger.info(f"Content preview: {detail['content'][:200]}...")
                
                else:
                    logger.warning("No results found for this query")
                
            except Exception as e:
                logger.error(f"Error processing query '{query}' with k={k}: {str(e)}", exc_info=True)
            
            completed += 1
            logger.info(f"\nProgress: {completed}/{total_queries} tests completed ({completed/total_queries*100:.1f}%)")
    
    # Final statistics
    total_time = time.time() - overall_start
    logger.info(f"\n{'='*80}\n📈 TEST SUMMARY\n{'='*80}")
    logger.info(f"Total time: {total_time:.2f}s")
    logger.info(f"Average time per query: {total_time/completed:.2f}s")
    
    # Calculate aggregate statistics
    if test_results:
        avg_search_time = sum(r['search_time'] for r in test_results) / len(test_results)
        avg_similarity = sum(r['avg_similarity'] for r in test_results) / len(test_results)
        avg_sources = sum(r['diversity_metrics']['unique_sources'] for r in test_results) / len(test_results)
        
        logger.info(f"\nAGGREGATE METRICS:")
        logger.info(f"- Average search time: {avg_search_time:.3f}s")
        logger.info(f"- Average semantic similarity: {avg_similarity:.3f}")
        logger.info(f"- Average unique sources per query: {avg_sources:.1f}")
    
    logger.info(f"\n{'='*80}\nTest completed successfully!\n{'='*80}")

if __name__ == "__main__":
    # Example test queries
    test_queries = [
        "How can a citizen challenge a law that violates their constitutional rights?",
        "How does the Constitution of Uganda ensure the independence of the Judiciary?",
        "What qualifications does one need to be elected as a Member of Parliament in Uganda?",
    ]
    
    # Example case data (optional)
    case_data = ""
    
    # Run the test
    run_vector_retrieval_test(
        test_queries=test_queries,
        k_values=[3, 5, 10],
        case_data=case_data
    )