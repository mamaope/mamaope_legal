import os
import io
import sys
import json
import time
import uuid
import argparse
import logging
import mimetypes
import traceback
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from dotenv import load_dotenv
import boto3
import magic
from tqdm import tqdm
from unstructured.partition.auto import partition
from unstructured.partition.text import partition_text
from pypdf import PdfReader
import openai
from pymilvus import (
    connections,
    FieldSchema,
    CollectionSchema,
    DataType,
    Collection,
    utility,
)
from PIL import Image

load_dotenv() 

# Azure OpenAI settings (from .env)
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT") 
AZURE_OPENAI_REGION = os.getenv("AZURE_OPENAI_REGION")
DEPLOYMENT = os.getenv("DEPLOYMENT") 
API_VERSION = os.getenv("API_VERSION", "2024-02-01")

# Milvus/Zilliz (from .env)
MILVUS_URI = os.getenv("MILVUS_URI")
MILVUS_TOKEN = os.getenv("MILVUS_TOKEN")
MILVUS_DB_NAME = os.getenv("MILVUS_DB_NAME", "default")
MILVUS_COLLECTION_NAME = os.getenv("MILVUS_COLLECTION_NAME", "mamaope_legal")

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
EMBEDDING_BATCH_SIZE = int(os.getenv("EMBEDDING_BATCH_SIZE", "64"))

# AWS S3 
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

# ---- Logging ----
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("ingestion")

# ---- Helpers ----

def init_azure_openai():
    if not AZURE_OPENAI_API_KEY or not AZURE_OPENAI_ENDPOINT or not DEPLOYMENT:
        logger.error("Azure OpenAI config missing in .env. Check AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT, DEPLOYMENT.")
        raise RuntimeError("Azure OpenAI configuration missing.")
    # Configure openai library for Azure
    openai.api_type = "azure"
    openai.api_key = AZURE_OPENAI_API_KEY
    openai.api_base = AZURE_OPENAI_ENDPOINT.rstrip("/") 
    openai.api_version = API_VERSION
    logger.info("Azure OpenAI client configured.")

def azure_embed_texts(texts: List[str]) -> List[List[float]]:
    """
    Batch call to Azure OpenAI embeddings. Expects DEPLOYMENT to be set in env.
    Returns list of vectors.
    """
    # guard
    if not texts:
        return []

    vectors = []
    for i in range(0, len(texts), EMBEDDING_BATCH_SIZE):
        batch = texts[i : i + EMBEDDING_BATCH_SIZE]
        try:
            response = openai.Embedding.create(
                input=batch,
                engine=DEPLOYMENT
            )
            # response.data is a list of objects with 'embedding'
            for item in response.data:
                vectors.append(item.embedding)
            time.sleep(0.1)  # small throttle
        except Exception as e:
            logger.exception(f"Azure embedding failed for batch starting at {i}: {e}")
            # fallback: insert zero vectors (or raise) — here we raise to force visibility
            raise
    return vectors

def is_executable_in_path(cmd: str) -> bool:
    """Return True if shell command exists in PATH."""
    from shutil import which
    return which(cmd) is not None

def detect_mime_from_bytes(content: bytes, filename: Optional[str]=None) -> str:
    """
    Return MIME string for given bytes using python-magic fallback to mimetypes.
    """
    try:
        mm = magic.Magic(mime=True)
        mime = mm.from_buffer(content)
        return mime or (mimetypes.guess_type(filename)[0] if filename else "application/octet-stream")
    except Exception:
        return mimetypes.guess_type(filename)[0] if filename else "application/octet-stream"

def read_local_file(path: str) -> bytes:
    with open(path, "rb") as f:
        return f.read()

# ---- Milvus helpers ----

def connect_milvus():
    """
    Connects to Milvus using MILVUS_URI (Zilliz managed). The method depends on how your Zilliz instance authentication is set up.
    We'll assume MILVUS_URI is an https URL to a managed endpoint and MILVUS_TOKEN is an auth token for cloud.
    """
    if not MILVUS_URI:
        raise RuntimeError("MILVUS_URI not set in .env")
    endpoint = MILVUS_URI
    # pymilvus expects host and port; for cloud serverless service, use connections.connect with uri param
    try:
        connections.connect(uri=endpoint, token=MILVUS_TOKEN)
        logger.info(f"Connected to Milvus at {endpoint}")
    except Exception as e:
        logger.exception("Failed to connect to Milvus. Check MILVUS_URI and MILVUS_TOKEN.")
        raise

def ensure_milvus_collection(collection_name: str, dim: int) -> Collection:
    """
    Ensure the Milvus collection exists. If not, create with schema:
    - id (primary key)
    - embedding (FLOAT_VECTOR, dim)
    - payload (JSON string)
    """
    fields = [
        FieldSchema(name="id", dtype=DataType.VARCHAR, max_length=64, is_primary=True, auto_id=False),
        FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=dim),
        FieldSchema(name="payload", dtype=DataType.VARCHAR, max_length=8192),
    ]
    schema = CollectionSchema(fields, description="RAG document chunks")

    if utility.has_collection(collection_name):
        col = Collection(collection_name)
        logger.info(f"Collection '{collection_name}' exists.")
        return col
    else:
        col = Collection(collection_name, schema=schema)
        # create an index on embedding vector (HNSW recommended) - dimension known
        index_params = {
            "index_type": "HNSW",
            "metric_type": "COSINE",
            "params": {"M": 16, "efConstruction": 200}
        }
        col.create_index(field_name="embedding", index_params=index_params)
        col.load()
        logger.info(f"Created and loaded new collection '{collection_name}' with dim={dim}.")
        return col

def upsert_to_milvus(collection: Collection, ids: List[str], vectors: List[List[float]], metas: List[Dict[str, Any]]):
    """
    Insert rows into Milvus. metas are JSON-serializable metadata per vector.
    """
    payloads = [json.dumps(m) for m in metas]
    try:
        collection.insert([ids, vectors, payloads])
        logger.info(f"Inserted {len(ids)} vectors to Milvus collection {collection.name}.")
    except Exception as e:
        logger.exception("Milvus insert failed.")
        raise

# ---- Text extraction & chunking ----

def get_pdf_page_labels_bytes(content: bytes) -> List[str]:
    """Return list of page labels from PDF bytes if pypdf available."""
    try:
        if not PdfReader:
            return []
        reader = PdfReader(io.BytesIO(content))
        n = len(reader.pages)
        # create labels as strings (1-based)
        return [str(i+1) for i in range(n)]
    except Exception:
        return []

def parse_with_unstructured(file_bytes: bytes, filename: str, prefer_hi_res: bool=True) -> Tuple[List[Dict[str,Any]], str]:
    """
    Return list of 'elements' and the strategy used.
    Uses unstructured.partition with hi_res then falls back to fast.
    """
    if partition is None:
        raise RuntimeError("unstructured.partition not available (install 'unstructured' package).")
    file_like = io.BytesIO(file_bytes)
    ext = os.path.splitext(filename)[1].lower()
    is_pdf = ext == ".pdf"
    strategy = "hi_res" if prefer_hi_res else "fast"
    last_exc = None
    for strat in ([strategy] if strategy == "fast" else ["hi_res","fast"]):
        try:
            elems = partition(
                file=file_like,
                strategy=strat,
                languages=["eng"],
                include_page_breaks=True,
                infer_table_structure=True,
                extract_images_in_pdf=is_pdf,
                extract_image_block_types=["Image", "Table", "Figure"]
            )
            logger.info(f"partition(...) succeeded for {filename} using strategy '{strat}'")
            return elems, strat
        except Exception as e:
            last_exc = e
            logger.warning(f"partition strategy '{strat}' failed for {filename}: {e}")
            file_like.seek(0)
            continue
    logger.error(f"All partition strategies failed for {filename}: {last_exc}")
    raise last_exc

def element_text(elem) -> str:
    return getattr(elem, "text", "") or ""

def heading_based_chunking(elements: List[Any], max_chars: int=1000, overlap: int=150) -> List[Dict[str,Any]]:
    """
    Chunk elements using headings as boundaries if possible; otherwise do char-based splits.
    Returns list of dicts: {'text': ..., 'page': ..., 'section': ...}
    """
    chunks = []
    buffer = ""
    section = None
    page = None

    def flush_buf():
        nonlocal buffer, section, page
        t = buffer.strip()
        if t:
            chunks.extend(split_text_to_chunks(t, page=page, section=section, max_chars=max_chars, overlap=overlap))
        buffer = ""

    for elem in elements:
        text = element_text(elem).strip()
        if not text:
            continue
        # Infer page number metadata if available on element
        page_meta = getattr(elem, "metadata", None)
        try:
            candidate_page = getattr(page_meta, "page_number", None)
            if candidate_page:
                page = candidate_page
        except Exception:
            pass

        is_heading = False
        if len(text) < 200 and (text.endswith(":") or text.isupper() or text.startswith("Section") or text.startswith("CHAPTER")):
            is_heading = True

        if is_heading:
            # flush current buffer before starting new section
            flush_buf()
            section = text.strip()
            continue

        # append content
        if buffer:
            buffer += "\n\n" + text
        else:
            buffer = text

        # If buffer large, flush
        if len(buffer) > max_chars * 1.5:
            flush_buf()
            # keep section continuous
    # final flush
    flush_buf()
    return chunks

def split_text_to_chunks(text: str, page: Optional[int]=None, section: Optional[str]=None, max_chars: int=800, overlap: int=150) -> List[Dict[str,Any]]:
    """
    Split a long text into overlapping chunks (character-level) with metadata.
    """
    text = text.strip()
    if not text:
        return []
    chunks = []
    start = 0
    L = len(text)
    while start < L:
        end = min(L, start + max_chars)
        chunk_text = text[start:end].strip()
        meta = {"page": page, "section": section}
        chunks.append({"text": chunk_text, "meta": meta})
        if end == L:
            break
        start = end - overlap if (end - overlap) > start else end
    return chunks

# ---- High-level processing pipeline ----

class Ingestor:
    def __init__(self, milvus_collection_name: str):
        self.milvus_collection_name = milvus_collection_name
        init_azure_openai()
        connect_milvus()
        # collection will be created at first upsert when we know dim
        self.collection = None

    def process_one(self, file_bytes: bytes, filename: str, source: str) -> List[Dict[str,Any]]:
        """
        Process a single file bytes, return list of chunks with metadata
        """
        mime = detect_mime_from_bytes(file_bytes, filename)
        logger.info(f"Detected MIME for {filename}: {mime}")

        prefer_hi_res = True
        # If PDF but it's text-based, prefer fast; if likely image/scanned, prefer hi_res
        if mime and "pdf" in mime:
            # quick heuristics to detect scanned pdf (no textual content)
            try:
                if PdfReader:
                    reader = PdfReader(io.BytesIO(file_bytes))
                    if any(page.extract_text() for page in reader.pages if page.extract_text()):
                        # has embedded text -> fast is fine
                        prefer_hi_res = False
            except Exception:
                # if pypdf fails, keep prefer_hi_res True (let unstructured try)
                pass

        # run unstructured partition with fallback
        try:
            elements, strat = parse_with_unstructured(file_bytes, filename, prefer_hi_res=prefer_hi_res)
        except Exception as e:
            logger.warning(f"Parsing {filename} failed; as last resort try text partition or pypdf text extraction: {e}")
            # try pypdf text extraction fallback
            try:
                if PdfReader:
                    reader = PdfReader(io.BytesIO(file_bytes))
                    full_text = "\n\n".join([p.extract_text() or "" for p in reader.pages])
                    elements = partition_text(text=full_text)
                else:
                    raise
            except Exception as e2:
                logger.exception(f"Total parsing failure for {filename}: {e2}")
                raise

        # chunk
        chunks = heading_based_chunking(elements)
        # attach top-level metadata
        enriched = []
        for ch in chunks:
            meta = {
                "source": source,
                "filename": os.path.basename(filename),
                "ingested_at": datetime.utcnow().isoformat() + "Z",
                "page": ch["meta"].get("page"),
                "section": ch["meta"].get("section")
            }
            text = ch["text"]
            # simple cleaning
            text = " ".join(text.split())
            if not text or len(text) < 30:
                continue
            enriched.append({"text": text, "meta": meta})
        logger.info(f"From file {filename} produced {len(enriched)} chunks.")
        return enriched

    def ingest_batch(self, items: List[Dict[str,Any]]):
        """
        items: list of dict with keys: 'text','meta'
        Embeds each text, upserts to Milvus.
        """
        texts = [it["text"] for it in items]
        metas = [it["meta"] for it in items]

        vectors = azure_embed_texts(texts)
        dim = len(vectors[0])
        # ensure collection exists
        if self.collection is None:
            self.collection = ensure_milvus_collection(self.milvus_collection_name, dim)

        # generate IDs
        ids = [str(uuid.uuid4()) for _ in vectors]
        # upsert
        upsert_to_milvus(self.collection, ids, vectors, metas)


# ---- File sources: local dir or S3 ----

def list_local_files(input_dir: str) -> List[str]:
    files = []
    for root, _, filenames in os.walk(input_dir):
        for fn in filenames:
            if fn.startswith("."):
                continue
            files.append(os.path.join(root, fn))
    return files

def list_s3_objects(bucket: str, prefix: str="") -> List[Dict[str,str]]:
    s3 = boto3.client("s3",
                      aws_access_key_id=AWS_ACCESS_KEY_ID,
                      aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
                      region_name=AWS_REGION)
    paginator = s3.get_paginator("list_objects_v2")
    out = []
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        for obj in page.get("Contents", []):
            out.append({"Key": obj["Key"], "Size": obj["Size"]})
    return out

def download_s3_object_bytes(bucket: str, key: str) -> bytes:
    s3 = boto3.client("s3",
                      aws_access_key_id=AWS_ACCESS_KEY_ID,
                      aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
                      region_name=AWS_REGION)
    obj = s3.get_object(Bucket=bucket, Key=key)
    return obj["Body"].read()

# ---- CLI / Runner ----

def main():
    parser = argparse.ArgumentParser(description="Robust single-file ingestion script")
    parser.add_argument("--input-dir", type=str, help="Local input directory containing docs")
    parser.add_argument("--s3-bucket", type=str, help="S3 bucket to read docs from (optional)")
    parser.add_argument("--s3-prefix", type=str, default="", help="S3 prefix for objects")
    parser.add_argument("--batch-size", type=int, default=32, help="Number of chunks per embedding batch")
    parser.add_argument("--quarantine-dir", type=str, default="./quarantine", help="Where to move failed files (local only)")
    parser.add_argument("--dry-run", action="store_true", help="Parse and chunk but do not embed/store")
    args = parser.parse_args()

    if not args.input_dir and not args.s3_bucket:
        parser.error("Provide --input-dir or --s3-bucket")

    os.makedirs(args.quarantine_dir, exist_ok=True)

    ing = Ingestor(MILVUS_COLLECTION_NAME)

    # gather file list
    work_queue = []
    if args.input_dir:
        files = list_local_files(args.input_dir)
        for f in files:
            work_queue.append({"source": "local", "path": f})
    if args.s3_bucket:
        objs = list_s3_objects(args.s3_bucket, args.s3_prefix)
        for obj in objs:
            work_queue.append({"source": "s3", "path": obj["Key"]})

    logger.info(f"Found {len(work_queue)} files to process.")

    # process one-by-one, but embed in batches
    batch_accum = []
    for entry in tqdm(work_queue, desc="Files"):
        try:
            if entry["source"] == "local":
                path = entry["path"]
                file_bytes = read_local_file(path)
                filename = path
                source = f"file://{path}"
            else:
                key = entry["path"]
                file_bytes = download_s3_object_bytes(args.s3_bucket, key)
                filename = key
                source = f"s3://{args.s3_bucket}/{key}"

            chunks = ing.process_one(file_bytes, filename, source)
            for c in chunks:
                batch_accum.append({"text": c["text"], "meta": c["meta"]})
                if len(batch_accum) >= args.batch_size:
                    if args.dry_run:
                        logger.info(f"[dry-run] would embed {len(batch_accum)} chunks")
                        batch_accum = []
                    else:
                        ing.ingest_batch(batch_accum)
                        batch_accum = []
        except Exception as e:
            logger.exception(f"Failed processing {entry}. Moving to quarantine.")
            # try to save file locally for later analysis
            try:
                qname = os.path.join(args.quarantine_dir, os.path.basename(entry.get("path", "failed")) + "_" + datetime.utcnow().strftime("%Y%m%dT%H%M%SZ"))
                if entry["source"] == "local":
                    os.rename(entry["path"], qname)
                else:
                    # write the bytes we downloaded (if available)
                    with open(qname, "wb") as fh:
                        fh.write(file_bytes)
                logger.info(f"Moved failed file to quarantine: {qname}")
            except Exception:
                logger.exception("Quarantine move failed.")

    # final partial batch
    if batch_accum:
        if args.dry_run:
            logger.info(f"[dry-run] would embed {len(batch_accum)} chunks (final batch)")
        else:
            ing.ingest_batch(batch_accum)

    logger.info("Ingestion run complete.")

if __name__ == "__main__":
    main()
