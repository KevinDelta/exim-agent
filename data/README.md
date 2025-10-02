# Data Directory

This directory contains all data-related files for the RAG application.

## Structure

```
data/
├── documents/          # Place your documents here for ingestion
│   ├── *.pdf          # PDF files
│   ├── *.txt          # Text files
│   ├── *.md           # Markdown files
│   ├── *.docx         # Word documents
│   ├── *.csv          # CSV files
│   ├── *.json         # JSON files
│   ├── *.html         # HTML files
│   └── *.xml          # XML files
│
└── chroma_db/         # ChromaDB vector store (auto-generated)
    └── ...            # Vector embeddings and metadata
```

## Usage

### Adding Documents

1. Place your documents in the `documents/` directory
2. Supported formats: `.txt`, `.pdf`, `.docx`, `.md`, `.csv`, `.json`, `.html`, `.xml`
3. You can organize files in subdirectories - the ingestion process is recursive

### Ingesting Documents

Use the API endpoint to ingest documents:

```bash
# Ingest all documents from the default directory
curl -X POST http://localhost:8000/ingest-documents \
  -H "Content-Type: application/json" \
  -d '{}'

# Ingest from a specific directory
curl -X POST http://localhost:8000/ingest-documents \
  -H "Content-Type: application/json" \
  -d '{"directory_path": "/path/to/your/documents"}'

# Ingest a single file
curl -X POST http://localhost:8000/ingest-documents \
  -H "Content-Type: application/json" \
  -d '{"file_path": "/path/to/your/file.pdf"}'
```

## Notes

- The `chroma_db/` directory is automatically created when you first ingest documents
- Vector embeddings are persisted to disk, so they survive application restarts
- To reset the vector store, use the `/reset-memory` endpoint (implementation pending)
