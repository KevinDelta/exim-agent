#!/bin/bash

echo "Testing document ingestion..."
echo ""

echo "1. Testing with default directory (no parameters):"
curl -X POST http://localhost:8000/ingest-documents \
  -H "Content-Type: application/json" \
  -d '{}'
echo -e "\n"

echo "2. Testing with explicit relative path:"
curl -X POST http://localhost:8000/ingest-documents \
  -H "Content-Type: application/json" \
  -d '{"directory_path": "./data/documents"}'
echo -e "\n"

echo "3. Testing with subdirectory (PDF files only):"
curl -X POST http://localhost:8000/ingest-documents \
  -H "Content-Type: application/json" \
  -d '{"directory_path": "./data/documents/pdf"}'
echo -e "\n"
