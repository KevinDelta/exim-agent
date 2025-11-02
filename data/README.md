# Data Directory

This directory contains all data-related files for the RAG application.

## Structure

```bash
data/
├── documents/          # Place your documents here for ingestion
│   ├── *.pdf          # PDF files
│   ├── *.txt          # Text files
│   ├── *.md           # Markdown files
│   ├── *.docx         # Word documents
│   ├── *.csv          # CSV files
│   ├── *.json         # JSON files
│   ├── *.html         # HTML files
│   ├── *.xml          # XML files
│   └── *.epub         # EPUB files
│
├── chroma_db/         # ChromaDB vector store (auto-generated)
│   └── ...            # Vector embeddings and metadata
│
├── sql/               # Database schema and setup scripts
│   └── create_compliance_table.sql  # Supabase table creation script
│
└── mem0_history.db    # SQLite database for Mem0 conversation history
```

## Usage

### Adding Documents

1. Place your documents in the `documents/` directory
2. Supported formats: `.txt`, `.pdf`, `.docx`, `.md`, `.csv`, `.json`, `.html`, `.xml`, `.epub`
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

### Setting up Supabase Database

For compliance data storage, run the SQL script in your Supabase dashboard:

1. Go to your Supabase project's SQL Editor
2. Copy and paste the contents of `data/sql/create_compliance_table.sql`
3. Click "Run" to create the compliance_data table

## Notes

- The `chroma_db/` directory is automatically created when you first ingest documents
- Vector embeddings are persisted to disk, so they survive application restarts
- The `sql/` directory contains database setup scripts for external services
- `mem0_history.db` stores conversation history for the Mem0 memory system
- To reset the vector store, use the `/reset-memory` endpoint (implementation pending)
