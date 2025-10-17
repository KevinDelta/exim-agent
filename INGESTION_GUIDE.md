# Document Ingestion Guide

## Overview

The RAG application has a complete document ingestion pipeline powered by **LangChain v1** that:

- Parses documents using LangChain document loaders
- Splits text into chunks using RecursiveCharacterTextSplitter
- Creates embeddings using OpenAI's text-embedding-3-small
- Stores vectors in ChromaDB with persistent storage
- Supports multiple file formats
- Provides RAG-based chat capabilities with retrieval

## Architecture

```Bash
┌─────────────────┐
│   Documents     │
│  (data/docs/)   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Ingestion API  │
│ /ingest-docs    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  LangChain      │
│ Doc Loaders     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Text Splitter   │
│ Chunk Documents │
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
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Chat Service   │
│ LangChain Agent │
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

 Option A: Ingest from default directory

```bash
curl -X POST http://localhost:8000/ingest-documents \
  -H "Content-Type: application/json" \
  -d '{}'
```

 Option B: Ingest from specific directory

```bash

curl -X POST http://localhost:8000/ingest-documents \
  -H "Content-Type: application/json" \
  -d '{"directory_path": "./data/documents"}'
```

 Option C: Ingest single file

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

```bash
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

### Files Created/Updated (LangChain v1)

1. **Infrastructure Layer**
   - `infrastructure/db/chroma_client.py` - ChromaDB client with LangChain Chroma vector store
   - `infrastructure/llm_providers/langchain_provider.py` - ChatOpenAI and OpenAIEmbeddings initialization

2. **Application Layer**
   - `application/ingest_documents_service/service.py` - Document ingestion with LangChain loaders and text splitters
   - `application/chat_service/service.py` - **NEW** RAG chat service using LangChain v1 agents

3. **Domain Layer**
   - `domain/models.py` - Document and IngestionResult models
   - `domain/exceptions.py` - Custom exceptions

4. **API Layer**
   - Updated `infrastructure/api/main.py` - Added chat endpoint and agent initialization
   - Updated `infrastructure/api/models.py` - ChatRequest/ChatResponse and other models

5. **Configuration**
   - Updated `config.py` - LangChain settings, RAG configuration, and paths

## Chat Service (NEW)

The application now includes a fully functional RAG chat service:

### Features

- **LangChain v1 Agents**: Uses `create_agent()` with retriever tool
- **Context Retrieval**: Automatically retrieves relevant documents from vector store
- **Conversation History**: Supports multi-turn conversations
- **Streaming Support**: Can stream responses in real-time (future enhancement)

### Usage

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What are two core ideas i need to know about AI?",
    "conversation_history": []
  }'
```

### Response Format

```json
{
  "response": "Based on the documents in the knowledge base...",
  "success": true,
  "error": null
}
```

## Troubleshooting

Issue: "ChromaDB not initialized"

- Ensure the API startup completed successfully
- Check logs for initialization errors

Issue: "Directory not found"

- Verify the path exists: `mkdir -p data/documents`
- Use absolute paths if relative paths fail

Issue: "No documents found"

- Check file extensions match supported formats
- Ensure files are in the specified directory

Issue: OpenAI API errors

- Verify your `OPENAI_API_KEY` is valid
- Check you have API credits available
