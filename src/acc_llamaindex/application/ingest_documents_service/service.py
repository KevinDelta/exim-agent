from pathlib import Path

from llama_index.core import SimpleDirectoryReader, VectorStoreIndex
from loguru import logger

from acc_llamaindex.config import settings
from acc_llamaindex.domain.exceptions import DocumentIngestionError
from acc_llamaindex.domain.models import Document, DocumentStatus, IngestionResult
from acc_llamaindex.infrastructure.db.chroma_client import chroma_client


class IngestDocumentsService:
    """Service for ingesting documents into the vector store."""

    def __init__(self):
        self.documents_path = Path(settings.documents_path)
        self.supported_extensions = settings.supported_file_extensions

    def ingest_documents_from_directory(self, directory_path: str | None = None) -> IngestionResult:
        """
        Ingest all documents from a directory into ChromaDB.
        
        Args:
            directory_path: Optional path to directory. If None, uses default from settings.
            
        Returns:
            IngestionResult with processing statistics
        """
        try:
            # Use provided path or default
            ingest_path = Path(directory_path) if directory_path else self.documents_path
            
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
            
            try:
                # Load documents using LlamaIndex
                reader = SimpleDirectoryReader(
                    input_dir=str(ingest_path),
                    recursive=True,
                    required_exts=self.supported_extensions
                )
                loaded_documents = reader.load_data()
                
                logger.info(f"Loaded {len(loaded_documents)} documents")
                
                # Create index and store in ChromaDB
                storage_context = chroma_client.get_storage_context()
                index = VectorStoreIndex.from_documents(
                    loaded_documents,
                    storage_context=storage_context,
                    show_progress=True
                )
                
                processed_count = len(loaded_documents)
                logger.info(f"Successfully indexed {processed_count} documents")
                
            except Exception as e:
                logger.error(f"Error processing documents: {e}")
                failed_count = len(documents)
                failed_docs = [doc.file_name for doc in documents]
                raise DocumentIngestionError(f"Failed to process documents: {e}")
            
            # Get collection stats
            stats = chroma_client.get_collection_stats()
            
            return IngestionResult(
                success=True,
                documents_processed=processed_count,
                documents_failed=failed_count,
                failed_documents=failed_docs,
                message=f"Successfully ingested {processed_count} documents",
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
            path = Path(file_path)
            
            if not path.exists():
                raise DocumentIngestionError(f"File not found: {file_path}")
            
            if not path.is_file():
                raise DocumentIngestionError(f"Path is not a file: {file_path}")
            
            logger.info(f"Ingesting single file: {file_path}")
            
            # Load single document
            reader = SimpleDirectoryReader(input_files=[str(path)])
            loaded_documents = reader.load_data()
            
            # Create index and store in ChromaDB
            storage_context = chroma_client.get_storage_context()
            index = VectorStoreIndex.from_documents(
                loaded_documents,
                storage_context=storage_context
            )
            
            logger.info(f"Successfully indexed file: {path.name}")
            
            # Get collection stats
            stats = chroma_client.get_collection_stats()
            
            return IngestionResult(
                success=True,
                documents_processed=1,
                documents_failed=0,
                message=f"Successfully ingested {path.name}",
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
