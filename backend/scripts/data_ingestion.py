import os
import io
import re
import boto3
import argparse
import time
import logging
import base64
from dotenv import load_dotenv
from pymilvus import MilvusClient, DataType
import openai
import fitz 
from ollama import generate
from unstructured.partition.auto import partition
from unstructured.chunking.title import chunk_by_title
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type, before_sleep_log

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Suppress MuPDF warnings
logging.getLogger("fitz").setLevel(logging.WARNING)

# Load environment variables
load_dotenv()

# Configuration
S3_BUCKET_NAME = os.getenv('AWS_S3_BUCKET', 'mamaope-legal')
S3_INPUT_PREFIX = 'input/'
MILVUS_URI = os.getenv('MILVUS_URI')
MILVUS_TOKEN = os.getenv('MILVUS_TOKEN')
COLLECTION_NAME = os.getenv('MILVUS_COLLECTION_NAME', 'mamaope_legal')

# Initialize Azure OpenAI client
azure_client = openai.AzureOpenAI(
    azure_endpoint=os.getenv('AZURE_OPENAI_ENDPOINT'),
    api_key=os.getenv('AZURE_OPENAI_API_KEY'),
    api_version=os.getenv('API_VERSION', '2024-02-01')
)
AZURE_DEPLOYMENT = os.getenv('DEPLOYMENT', 'text-embedding-3-large')
EMBEDDING_DIM = 3072  # For text-embedding-3-large

def initialize_zilliz_collection(refresh: bool = False):
    """
    Connects to Milvus and initializes the collection with schema for Azure embeddings.
    """
    setup_client = MilvusClient(uri=MILVUS_URI, token=MILVUS_TOKEN)
    
    try:
        if refresh and setup_client.has_collection(collection_name=COLLECTION_NAME):
            logger.info(f"Refresh mode: Dropping existing collection '{COLLECTION_NAME}'...")
            setup_client.drop_collection(collection_name=COLLECTION_NAME)
            logger.info("Collection dropped.")

        if not setup_client.has_collection(collection_name=COLLECTION_NAME):
            logger.info(f"Creating collection '{COLLECTION_NAME}'...")
            schema = MilvusClient.create_schema(auto_id=True, enable_dynamic_field=False)
            schema.add_field(field_name="id", datatype=DataType.INT64, is_primary=True)
            schema.add_field(field_name="content", datatype=DataType.VARCHAR, max_length=65535)
            schema.add_field(field_name="file_path", datatype=DataType.VARCHAR, max_length=1024, is_partition_key=True)
            schema.add_field(field_name="display_page_number", datatype=DataType.VARCHAR, max_length=100)        
            
            schema.add_field(field_name="vector", datatype=DataType.FLOAT_VECTOR, dim=EMBEDDING_DIM, is_nullable=False)
            index_params = MilvusClient.prepare_index_params()
            index_params.add_index(field_name="vector", index_type="AUTOINDEX", metric_type="COSINE")
            
            setup_client.create_collection(
                collection_name=COLLECTION_NAME,
                schema=schema,
                index_params=index_params
            )
            logger.info(f"Collection '{COLLECTION_NAME}' created successfully.")
            logger.info("Waiting 5 seconds for collection to initialize...")
            time.sleep(5)
        else:
            logger.info(f"Collection '{COLLECTION_NAME}' already exists. Proceeding with update.")
    
    except Exception as e:
        logger.error(f"Failed to initialize collection: {e}")
        raise
    finally:
        setup_client.close()

def describe_image(image_data: bytes) -> str:
    """
    Uses Ollama LLaVA to generate a textual description of an image/chart/graph.
    Fail-safe: Fallback to empty string on error.
    """
    try:
        img_base64 = base64.b64encode(image_data).decode('utf-8')
        response = generate('llava', 'Describe this image in detail, focusing on any charts, graphs, tables, or data points. Be precise for searchability:', images=[img_base64])
        return response['response']
    except Exception as e:
        logger.warning(f"Failed to describe image: {e}")
        return "Visual element (description unavailable)."

def get_pdf_page_labels(content: bytes) -> list[str]:
    """
    Extracts actual display page labels from PDF (e.g., roman numerals) using PyMuPDF.
    Returns list of labels, indexed by physical page (0-based).
    """
    try:
        with fitz.open(stream=content, filetype="pdf") as doc:
            return [doc[i].get_label() or str(i + 1) for i in range(len(doc))]
    except Exception as e:
        logger.warning(f"Failed to extract PDF page labels: {e}")
        return []

def extract_content(file_key: str, content: bytes) -> list[dict]:
    """
    Extracts semantic chunks using Unstructured, handling text, tables, images/charts/graphs.
    Fail-safe: Skips failed elements, cleans temp files. Falls back to 'auto' strategy if 'hi_res' fails.
    """
    logger.info(f"Parsing file with Unstructured: {file_key}...")
    chunks = []
    temp_files = []  # Track for cleanup
    
    try:
        file_extension = os.path.splitext(file_key)[1].lower()
        is_pdf = file_extension == '.pdf'
        
        # Get page labels if PDF
        page_labels = get_pdf_page_labels(content) if is_pdf else []
        
        file_like = io.BytesIO(content)
        strategy = "hi_res"  # Default
        
        try:
            # Partition: Auto-detects type, hi_res for visuals/layouts
            elements = partition(
                file=file_like,
                strategy=strategy,  # Best for tables/images/charts
                languages=["eng"], 
                include_page_breaks=True,
                infer_table_structure=True,
                extract_images_in_pdf=is_pdf, 
                extract_image_block_types=["Image", "Table", "Figure"]
            )
        except Exception as partition_err:
            logger.warning(f"'hi_res' strategy failed for {file_key}: {partition_err}. Falling back to 'auto'.")
            strategy = "auto"
            file_like.seek(0)  # Reset stream
            elements = partition(
                file=file_like,
                strategy=strategy,
                languages=["eng"], 
                include_page_breaks=True,
                infer_table_structure=True,
                extract_images_in_pdf=is_pdf, 
                extract_image_block_types=["Image", "Table", "Figure"]
            )
        
        # Semantic chunking: Groups by titles/sections for important parts
        chunked_elements = chunk_by_title(
            elements,
            max_characters=512,
            combine_text_under_n_chars=200,
            new_after_n_chars=400
        )
        
        for elem in chunked_elements:
            try:
                chunk_text = elem.text.strip()
                if not chunk_text:
                    continue
                
                # Handle tables as structured HTML
                if elem.category == "Table" and hasattr(elem.metadata, 'text_as_html'):
                    chunk_text = elem.metadata.text_as_html
                
                # Handle images/charts/graphs: Describe with LLaVA
                image_path = getattr(elem.metadata, 'image_path', None)
                if elem.category in ["Image", "Figure"] and image_path:
                    with open(image_path, "rb") as img_file:
                        image_data = img_file.read()
                    description = describe_image(image_data)
                    chunk_text = f"Description of visual element: {description}\nOriginal text: {chunk_text}"
                    temp_files.append(image_path)  # Track for cleanup
                
                # Page number: Use label if available, else physical as string (handles roman/etc.)
                physical_page = getattr(elem.metadata, 'page_number', 1) - 1  # 0-based
                display_page = page_labels[physical_page] if page_labels and physical_page < len(page_labels) else str(physical_page + 1)
                
                chunks.append({'text': chunk_text, 'page': display_page})
            except Exception as e:
                logger.warning(f"Skipped chunk in {file_key}: {e}")
                continue
        
        logger.info(f"Extracted {len(chunks)} chunks from {file_key} using strategy '{strategy}'.")
        return chunks
    except Exception as e:
        logger.error(f"Failed to parse {file_key}: {e}")
        return []
    finally:
        # Cleanup temp files
        for temp in temp_files:
            try:
                os.remove(temp)
            except Exception:
                pass

@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=4, max=60),
    retry=retry_if_exception_type(openai.RateLimitError),
    before_sleep=before_sleep_log(logger, logging.INFO)
)
def generate_embeddings_batch(texts: list[str]) -> list[list[float]]:
    """
    Generates embeddings for a batch of texts using Azure OpenAI.
    """
    logger.info(f"Generating Azure OpenAI embeddings for {len(texts)} texts using deployment '{AZURE_DEPLOYMENT}'...")
    try:
        response = azure_client.embeddings.create(
            input=texts,
            model=AZURE_DEPLOYMENT
        )
        embeddings = [item.embedding for item in response.data]
        logger.info(f"Successfully generated {len(embeddings)} embeddings.")
        return embeddings
    except openai.RateLimitError as e:
        retry_after = e.response.headers.get('Retry-After', 60)
        logger.info(f"Rate limit hit. Retrying after {retry_after} seconds.")
        raise
    except Exception as e:
        logger.error(f"Embedding generation failed: {e}")
        raise

def generate_embeddings(texts: list[str], batch_size: int = 50) -> list[list[float]]:
    """
    Generates embeddings in smaller batches to respect Azure rate limits and memory.
    Fail-safe: Skips failed batches.
    """
    all_embeddings = []
    for i in range(0, len(texts), batch_size):
        batch_texts = texts[i:i + batch_size]
        logger.info(f"Processing embedding batch {i//batch_size + 1}/{len(texts)//batch_size + 1} ({len(batch_texts)} texts)...")
        try:
            embeddings = generate_embeddings_batch(batch_texts)
            all_embeddings.extend(embeddings)
        except Exception as e:
            logger.error(f"Failed embedding batch {i//batch_size + 1}: {e}. Skipping.")
            all_embeddings.extend([[] for _ in batch_texts])
        time.sleep(1)  # Rate buffer
    return all_embeddings

def file_exists_in_milvus(insert_client, file_key: str) -> bool:
    """
    Checks if file_path already exists in Milvus (for incremental skip).
    """
    try:
        res = insert_client.query(collection_name=COLLECTION_NAME, filter=f'file_path == "{file_key}"', limit=1)
        return bool(res)
    except Exception as e:
        logger.warning(f"Failed to check existence for {file_key}: {e}")
        return False

def main(refresh: bool, specific_file: str = None):
    """Main function to run the ingestion process. Fail-safe with skips."""
    if refresh:
        logger.info("--- Starting Data Ingestion in FULL REFRESH mode ---")
    else:
        logger.info("--- Starting Data Ingestion in INCREMENTAL UPDATE mode ---")

    try:
        # Initialize collection
        initialize_zilliz_collection(refresh=refresh)
    except Exception as e:
        logger.critical(f"Collection init failed: {e}. Aborting.")
        return

    # Create fresh Milvus client for insertion
    logger.info("Creating a fresh client for data insertion...")
    insert_client = MilvusClient(uri=MILVUS_URI, token=MILVUS_TOKEN)

    # Initialize S3 client
    s3 = boto3.client(
        's3',
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
        region_name=os.getenv('AWS_REGION')
    )

    try:
        # List files in S3 bucket
        response = s3.list_objects_v2(Bucket=S3_BUCKET_NAME, Prefix=S3_INPUT_PREFIX)
        supported_extensions = {'.pdf', '.docx', '.txt', '.csv', '.pptx', '.html', '.jpg', '.png', '.tiff'}
        all_s3_files = [
            obj['Key'] for obj in response.get('Contents', [])
            if os.path.splitext(obj['Key'])[1].lower() in supported_extensions
        ]
        if specific_file:
            all_s3_files = [specific_file] if specific_file in all_s3_files else []
        
        logger.info(f"Found {len(all_s3_files)} supported files to process: {all_s3_files}")
        
        total_chunks_ingested = 0
        for file_key in all_s3_files:
            if not refresh and file_exists_in_milvus(insert_client, file_key):
                logger.info(f"Skipping {file_key} (already in Milvus).")
                continue
            
            logger.info(f"Processing file: {file_key}...")
            try:
                # Download file from S3
                file_obj = s3.get_object(Bucket=S3_BUCKET_NAME, Key=file_key)
                file_content = file_obj['Body'].read()
                
                # Extract chunks
                chunks = extract_content(file_key, file_content)
                if not chunks:
                    logger.warning(f"No content extracted from {file_key}. Skipping.")
                    continue
                
                # Generate embeddings (filter out empty)
                texts = [chunk['text'] for chunk in chunks if chunk['text']]
                embeddings = generate_embeddings(texts)
                # Filter valid (non-empty embeddings)
                valid_data = [
                    (chunk, emb) for chunk, emb in zip(chunks, embeddings) if emb
                ]
                if not valid_data:
                    logger.warning(f"No valid embeddings for {file_key}. Skipping.")
                    continue
                
                # Prepare data for insertion
                data_to_insert = [
                    {
                        "content": chunk['text'], 
                        "file_path": file_key, 
                        "display_page_number": chunk['page'],
                        "vector": emb
                    }
                    for chunk, emb in valid_data
                ]
                
                # Insert in smaller batches
                batch_size = 50
                for i in range(0, len(data_to_insert), batch_size):
                    batch = data_to_insert[i:i + batch_size]
                    try:
                        res = insert_client.insert(collection_name=COLLECTION_NAME, data=batch)
                        total_chunks_ingested += res['insert_count']
                        logger.info(f"Inserted batch {i//batch_size + 1} ({len(batch)} chunks) for {file_key}")
                    except Exception as e:
                        logger.error(f"Failed to insert batch {i//batch_size + 1} for {file_key}: {e}")
                
                logger.info(f"Successfully inserted {len(data_to_insert)} chunks for {file_key}.")

            except Exception as e:
                logger.error(f"Failed to process file {file_key}: {e}")
                continue
        
        logger.info("--- Ingestion Complete ---")
        logger.info(f"Total chunks ingested in this run: {total_chunks_ingested}")
        
    except Exception as e:
        logger.error(f"Error listing S3 files: {e}")
    
    finally:
        insert_client.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the Zilliz ingestion script for knowledge base.")
    parser.add_argument(
        '--refresh',
        action='store_true',
        help='If set, drops the existing collection and re-ingests all documents.'
    )
    parser.add_argument(
        '--file',
        type=str,
        default=None,
        help='Specific file to process (e.g., input/document.pdf).'
    )
    args = parser.parse_args()
    main(refresh=args.refresh, specific_file=args.file)
    