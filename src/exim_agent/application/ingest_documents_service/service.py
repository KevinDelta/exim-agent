import os
from pathlib import Path

from langchain_community.document_loaders import (
    DirectoryLoader,
    TextLoader,
    UnstructuredMarkdownLoader,
    UnstructuredHTMLLoader,
    CSVLoader,
    JSONLoader,
)
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from loguru import logger

from exim_agent.config import config
from exim_agent.domain.exceptions import DocumentIngestionError
from exim_agent.domain.models import Document, DocumentStatus, IngestionResult
from exim_agent.infrastructure.db.chroma_client import chroma_client


class IngestDocumentsService:
    """Service for ingesting documents into the vector store."""

    def __init__(self):
        # Use absolute paths from settings (already resolved in config)
        self.documents_path = Path(config.documents_path)
        self.supported_extensions = config.supported_file_extensions
        
        # Initialize text splitter
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=config.chunk_size,
            chunk_overlap=config.chunk_overlap,
            length_function=len,
            is_separator_regex=False,
        )
        
        logger.info(f"IngestDocumentsService initialized with documents_path: {self.documents_path}")
    
    def _get_loader_for_extension(self, file_path: str):
        """Get the appropriate document loader for a file extension."""
        ext = Path(file_path).suffix.lower()
        
        loader_map = {
            ".txt": lambda p: TextLoader(p),
            ".md": lambda p: UnstructuredMarkdownLoader(p),
            ".pdf": lambda p: PyPDFLoader(p),
            ".html": lambda p: UnstructuredHTMLLoader(p),
            ".csv": lambda p: CSVLoader(p),
            ".json": lambda p: JSONLoader(p, jq_schema=".", text_content=False),
        }
        
        # Default to TextLoader for unsupported extensions
        return loader_map.get(ext, lambda p: TextLoader(p))(file_path)

    def ingest_documents_from_directory(self, directory_path: str | None = None) -> IngestionResult:
        """
        Ingest all documents from a directory into ChromaDB.
        Args:
            directory_path: Optional path to directory. If None, uses default from settings.   
        Returns:
            IngestionResult with processing statistics
        """
        try:
            # Use provided path or default from config
            if directory_path:
                # Convert to absolute path if relative
                ingest_path = Path(directory_path)
                if not ingest_path.is_absolute():
                    ingest_path = ingest_path.resolve()
            else:
                # Use configured documents path (absolute path from .env)
                ingest_path = self.documents_path
            
            if not ingest_path.exists():
                raise DocumentIngestionError(f"Directory not found: {ingest_path}")
            
            logger.info(f"Starting document ingestion from: {ingest_path}")
            
            # Get list of files to process
            documents = self._discover_documents(ingest_path)
            
            if not documents:
                return IngestionResult(
                    success=True,
                    documents_processed=0,
                    documents_failed=0,
                    message=f"No documents found in {ingest_path}"
                )
            
            logger.info(f"Found {len(documents)} documents to process")
            
            # Process documents
            processed_count = 0
            failed_count = 0
            failed_docs = []
            all_splits = []
            
            # Load and split documents by extension
            for doc in documents:
                try:
                    logger.info(f"Loading document: {doc.file_name}")
                    loader = self._get_loader_for_extension(str(doc.file_path))
                    loaded_docs = loader.load()
                    
                    # Split documents into chunks
                    splits = self.text_splitter.split_documents(loaded_docs)
                    all_splits.extend(splits)
                    processed_count += 1
                    
                except Exception as e:
                    logger.error(f"Failed to process {doc.file_name}: {e}")
                    failed_count += 1
                    failed_docs.append(doc.file_name)
            
            if all_splits:
                logger.info(f"Created {len(all_splits)} text chunks from {processed_count} documents")
                
                # Add documents to vector store in batches to avoid provider limits
                vector_store = chroma_client.get_vector_store()
                batch_size = max(1, config.ingestion_batch_size)
                for start_index in range(0, len(all_splits), batch_size):
                    batch = all_splits[start_index:start_index + batch_size]
                    vector_store.add_documents(batch)
                
                logger.info(
                    "Successfully added %s chunks to vector store (batch size=%s)",
                    len(all_splits),
                    batch_size,
                )
            
            # Get collection stats
            stats = chroma_client.get_collection_stats()
            
            return IngestionResult(
                success=True,
                documents_processed=processed_count,
                documents_failed=failed_count,
                failed_documents=failed_docs,
                message=f"Successfully ingested {processed_count} documents ({len(all_splits)} chunks)",
                collection_stats=stats
            )
            
        except Exception as e:
            logger.error(f"Document ingestion failed: {e}")
            raise DocumentIngestionError(f"Ingestion failed: {e}")

    def ingest_single_file(self, file_path: str) -> IngestionResult:
        """
        Ingest a single document file.
        Args:
            file_path: Path to the file to ingest    
        Returns:
            IngestionResult with processing statistics
        """
        try:
            path = Path(file_path).resolve()
            
            if not path.exists():
                raise DocumentIngestionError(f"File not found: {file_path}")
            
            if not path.is_file():
                raise DocumentIngestionError(f"Path is not a file: {file_path}")
            
            logger.info(f"Ingesting single file: {file_path}")
            
            # Load document using appropriate loader
            loader = self._get_loader_for_extension(str(path))
            loaded_documents = loader.load()
            
            # Split documents into chunks
            splits = self.text_splitter.split_documents(loaded_documents)
            
            logger.info(f"Created {len(splits)} text chunks from {path.name}")
            
            # Add documents to vector store
            vector_store = chroma_client.get_vector_store()
            vector_store.add_documents(splits)
            
            logger.info(f"Successfully indexed file: {path.name}")
            
            # Get collection stats
            stats = chroma_client.get_collection_stats()
            
            return IngestionResult(
                success=True,
                documents_processed=1,
                documents_failed=0,
                message=f"Successfully ingested {path.name} ({len(splits)} chunks)",
                collection_stats=stats
            )
            
        except Exception as e:
            logger.error(f"Failed to ingest file {file_path}: {e}")
            raise DocumentIngestionError(f"Failed to ingest file: {e}")

    def _discover_documents(self, directory: Path) -> list[Document]:
        """
        Discover all supported documents in a directory.
        Args:
            directory: Path to search for documents   
        Returns:
            List of Document objects
        """
        documents = []
        
        for ext in self.supported_extensions:
            for file_path in directory.rglob(f"*{ext}"):
                if file_path.is_file():
                    doc = Document(
                        file_path=file_path,
                        file_name=file_path.name,
                        file_type=file_path.suffix,
                        size_bytes=file_path.stat().st_size,
                        status=DocumentStatus.PENDING
                    )
                    documents.append(doc)
        
        return documents


# Global service instance
ingest_service = IngestDocumentsService()
