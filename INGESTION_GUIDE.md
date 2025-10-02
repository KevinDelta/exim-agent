# Document Ingestion Guide

## Overview

The RAG application now has a complete document ingestion pipeline that:
- Parses documents using LlamaIndex
- Creates embeddings using OpenAI's text-embedding-3-small
- Stores vectors in ChromaDB with persistent storage
- Supports multiple file formats

## Architecture

```
┌─────────────────┐
│   Documents     │
│  (data/docs/)   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Ingestion API  │
│  /ingest-docs   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ LlamaIndex      │
│ SimpleReader    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ OpenAI Embed    │
│ text-embed-3-sm │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   ChromaDB      │
│ (data/chroma/)  │
└─────────────────┘
```

## Quick Start

### 1. Ensure your .env is configured

```bash
OPENAI_API_KEY="your-key-here"
```

### 2. Start the API

```bash
# Using Docker
make start-project

# Or locally
source .venv/bin/activate
fastapi dev src/acc_llamaindex/infrastructure/api/main.py
```

### 3. Add documents to ingest

```bash
# Create some test documents
mkdir -p data/documents
echo "This is a test document about AI." > data/documents/test1.txt
echo "RAG combines retrieval with generation." > data/documents/test2.txt
```

### 4. Ingest documents

**Option A: Ingest from default directory**
```bash
curl -X POST http://localhost:8000/ingest-documents \
  -H "Content-Type: application/json" \
  -d '{}'
```

**Option B: Ingest from specific directory**
```bash
curl -X POST http://localhost:8000/ingest-documents \
  -H "Content-Type: application/json" \
  -d '{"directory_path": "./data/documents"}'
```

**Option C: Ingest single file**
```bash
curl -X POST http://localhost:8000/ingest-documents \
  -H "Content-Type: application/json" \
  -d '{"file_path": "./data/documents/test1.txt"}'
```

### 5. Check the response

```json
{
  "success": true,
  "documents_processed": 2,
  "documents_failed": 0,
  "failed_documents": [],
  "message": "Successfully ingested 2 documents",
  "collection_stats": {
    "collection_name": "documents",
    "document_count": 2,
    "status": "active"
  }
}
```

## Configuration

All settings are in `src/acc_llamaindex/config.py`:

| Setting | Default | Description |
|---------|---------|-------------|
| `documents_path` | `./data/documents` | Default directory for documents |
| `chroma_db_path` | `./data/chroma_db` | ChromaDB storage location |
| `chroma_collection_name` | `documents` | Collection name in ChromaDB |
| `chunk_size` | `1024` | Text chunk size for processing |
| `chunk_overlap` | `200` | Overlap between chunks |
| `openai_model` | `gpt-4o-mini` | LLM model for generation |
| `openai_embedding_model` | `text-embedding-3-small` | Embedding model |

## Supported File Formats

- `.txt` - Plain text
- `.pdf` - PDF documents
- `.docx` - Word documents
- `.md` - Markdown files
- `.csv` - CSV files
- `.json` - JSON files
- `.html` - HTML files
- `.xml` - XML files

## Directory Structure

```
data/
├── documents/          # Place your documents here
│   ├── file1.pdf
│   ├── file2.txt
│   └── subfolder/
│       └── file3.md
└── chroma_db/         # Auto-generated vector store
    └── ...
```

## Implementation Details

### Files Created

1. **Infrastructure Layer**
   - `infrastructure/db/chroma_client.py` - ChromaDB client wrapper
   - `infrastructure/llm_providers/openai_provider.py` - LLM initialization

2. **Application Layer**
   - `application/ingest_documents_service/service.py` - Ingestion logic

3. **Domain Layer**
   - `domain/models.py` - Document and IngestionResult models
   - `domain/exceptions.py` - Custom exceptions

4. **API Layer**
   - Updated `infrastructure/api/main.py` - Added startup lifespan and endpoint
   - Updated `infrastructure/api/models.py` - Request/response models

5. **Configuration**
   - Updated `config.py` - All settings and paths

## Next Steps

After ingestion is working, you'll want to implement:

1. **Chat Service** - Query the vector store with RAG
2. **Reset Memory Service** - Clear the vector store
3. **Evaluation Service** - Measure RAG performance

## Troubleshooting

**Issue: "ChromaDB not initialized"**
- Ensure the API startup completed successfully
- Check logs for initialization errors

**Issue: "Directory not found"**
- Verify the path exists: `mkdir -p data/documents`
- Use absolute paths if relative paths fail

**Issue: "No documents found"**
- Check file extensions match supported formats
- Ensure files are in the specified directory

**Issue: OpenAI API errors**
- Verify your `OPENAI_API_KEY` is valid
- Check you have API credits available
