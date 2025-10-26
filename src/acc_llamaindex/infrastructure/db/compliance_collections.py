"""ChromaDB collections for compliance data."""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Union
from langchain_chroma import Chroma
from langchain_core.documents import Document
from loguru import logger

from acc_llamaindex.infrastructure.db.chroma_client import chroma_client
from acc_llamaindex.infrastructure.llm_providers.langchain_provider import get_embeddings


class ComplianceCollections:
    """Manager for compliance-specific ChromaDB collections."""
    
    # Collection names
    HTS_NOTES = "compliance_hts_notes"
    RULINGS = "compliance_rulings"
    REFUSALS = "compliance_refusal_summaries"
    POLICY = "compliance_policy_snippets"
    EVENTS = "compliance_events"  # New collection for historical events
    
    def __init__(self):
        """Initialize compliance collections manager."""
        self._client = None
        self._embeddings = None
        self._collections: Dict[str, Chroma] = {}
        self._initialized = False
    
    def initialize(self):
        """Initialize all compliance collections."""
        if self._initialized:
            logger.info("Compliance collections already initialized")
            return
        
        try:
            logger.info("Initializing compliance collections...")
            
            # Get shared ChromaDB client
            self._client = chroma_client.get_client()
            self._embeddings = get_embeddings()
            
            # Initialize each collection
            self._init_hts_collection()
            self._init_rulings_collection()
            self._init_refusals_collection()
            self._init_policy_collection()
            self._init_events_collection()
            
            self._initialized = True
            logger.info("All compliance collections initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize compliance collections: {e}")
            raise
    
    def _init_hts_collection(self):
        """Initialize HTS notes collection."""
        self._collections[self.HTS_NOTES] = Chroma(
            client=self._client,
            collection_name=self.HTS_NOTES,
            embedding_function=self._embeddings,
            collection_metadata={
                "description": "HTS code notes, special requirements, and tariff details",
                "type": "compliance_hts"
            }
        )
        logger.info(f"Initialized collection: {self.HTS_NOTES}")
    
    def _init_rulings_collection(self):
        """Initialize CBP rulings collection."""
        self._collections[self.RULINGS] = Chroma(
            client=self._client,
            collection_name=self.RULINGS,
            embedding_function=self._embeddings,
            collection_metadata={
                "description": "CBP CROSS classification rulings and precedents",
                "type": "compliance_rulings"
            }
        )
        logger.info(f"Initialized collection: {self.RULINGS}")
    
    def _init_refusals_collection(self):
        """Initialize import refusals collection."""
        self._collections[self.REFUSALS] = Chroma(
            client=self._client,
            collection_name=self.REFUSALS,
            embedding_function=self._embeddings,
            collection_metadata={
                "description": "FDA/FSIS import refusal summaries and trends",
                "type": "compliance_refusals"
            }
        )
        logger.info(f"Initialized collection: {self.REFUSALS}")
    
    def _init_policy_collection(self):
        """Initialize policy snippets collection."""
        self._collections[self.POLICY] = Chroma(
            client=self._client,
            collection_name=self.POLICY,
            embedding_function=self._embeddings,
            collection_metadata={
                "description": "Trade policy updates, regulatory changes, and compliance guidance",
                "type": "compliance_policy"
            }
        )
        logger.info(f"Initialized collection: {self.POLICY}")
    
    def _init_events_collection(self):
        """Initialize compliance events collection."""
        self._collections[self.EVENTS] = Chroma(
            client=self._client,
            collection_name=self.EVENTS,
            embedding_function=self._embeddings,
            collection_metadata={
                "description": "Historical compliance events and alerts",
                "type": "compliance_events"
            }
        )
        logger.info(f"Initialized collection: {self.EVENTS}")
    
    def get_collection(self, collection_name: str) -> Chroma:
        """Get a specific collection by name."""
        if not self._initialized:
            raise RuntimeError("Collections not initialized. Call initialize() first.")
        
        if collection_name not in self._collections:
            raise ValueError(f"Unknown collection: {collection_name}")
        
        return self._collections[collection_name]
    
    def search_hts_notes(self, query: str, hts_code: str = None, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Search HTS notes collection.
        
        Args:
            query: Search query
            hts_code: Optional HTS code filter
            limit: Maximum results
        
        Returns:
            List of matching documents with metadata
        """
        collection = self.get_collection(self.HTS_NOTES)
        
        # Build filter if HTS code provided
        where = {"hts_code": hts_code} if hts_code else None
        
        results = collection.similarity_search_with_score(
            query=query,
            k=limit,
            filter=where
        )
        
        return [
            {
                "content": doc.page_content,
                "metadata": doc.metadata,
                "score": score
            }
            for doc, score in results
        ]
    
    def search_rulings(self, query: str, hts_code: str = None, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Search CBP rulings collection.
        
        Args:
            query: Search query
            hts_code: Optional HTS code filter
            limit: Maximum results
        
        Returns:
            List of matching rulings
        """
        collection = self.get_collection(self.RULINGS)
        
        where = {"hts_code": hts_code} if hts_code else None
        
        results = collection.similarity_search_with_score(
            query=query,
            k=limit,
            filter=where
        )
        
        return [
            {
                "content": doc.page_content,
                "metadata": doc.metadata,
                "score": score
            }
            for doc, score in results
        ]
    
    def search_refusals(self, query: str, country: str = None, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Search import refusals collection.
        
        Args:
            query: Search query
            country: Optional country filter
            limit: Maximum results
        
        Returns:
            List of matching refusal records
        """
        collection = self.get_collection(self.REFUSALS)
        
        where = {"country": country} if country else None
        
        results = collection.similarity_search_with_score(
            query=query,
            k=limit,
            filter=where
        )
        
        return [
            {
                "content": doc.page_content,
                "metadata": doc.metadata,
                "score": score
            }
            for doc, score in results
        ]
    
    def search_policy(self, query: str, category: str = None, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Search policy snippets collection.
        
        Args:
            query: Search query
            category: Optional category filter (e.g., "sanctions", "tariffs")
            limit: Maximum results
        
        Returns:
            List of matching policy documents
        """
        collection = self.get_collection(self.POLICY)
        
        where = {"category": category} if category else None
        
        results = collection.similarity_search_with_score(
            query=query,
            k=limit,
            filter=where
        )
        
        return [
            {
                "content": doc.page_content,
                "metadata": doc.metadata,
                "score": score,
                "relevance": 1.0 - score if score <= 1.0 else 0.0
            }
            for doc, score in results
        ]
    
    def search_events(
        self, 
        query: str, 
        client_id: str = None, 
        sku_id: str = None, 
        lane_id: str = None,
        event_type: str = None,
        risk_level: str = None,
        date_from: str = None,
        date_to: str = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search compliance events collection with advanced filtering.
        
        Args:
            query: Search query
            client_id: Optional client filter
            sku_id: Optional SKU filter
            lane_id: Optional lane filter
            event_type: Optional event type filter
            risk_level: Optional risk level filter
            date_from: Optional start date filter (ISO format)
            date_to: Optional end date filter (ISO format)
            limit: Maximum results
        
        Returns:
            List of matching events
        """
        collection = self.get_collection(self.EVENTS)
        
        # Build complex filter - ChromaDB requires $and for multiple conditions
        where_conditions = []
        if client_id:
            where_conditions.append({"client_id": client_id})
        if sku_id:
            where_conditions.append({"sku_id": sku_id})
        if lane_id:
            where_conditions.append({"lane_id": lane_id})
        if event_type:
            where_conditions.append({"event_type": event_type})
        if risk_level:
            where_conditions.append({"risk_level": risk_level})
        
        # Date filtering would need to be handled at the application level
        # since ChromaDB doesn't support date range queries directly
        
        if len(where_conditions) == 0:
            where = None
        elif len(where_conditions) == 1:
            where = where_conditions[0]
        else:
            where = {"$and": where_conditions}
        
        results = collection.similarity_search_with_score(
            query=query,
            k=limit,
            filter=where
        )
        
        events = [
            {
                "content": doc.page_content,
                "metadata": doc.metadata,
                "score": score,
                "relevance": 1.0 - score if score <= 1.0 else 0.0
            }
            for doc, score in results
        ]
        
        # Apply date filtering if specified
        if date_from or date_to:
            events = self._filter_by_date(events, date_from, date_to)
        
        return events
    
    def search_multi_collection(
        self,
        query: str,
        collections: List[str] = None,
        limit_per_collection: int = 3,
        min_relevance: float = 0.7
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Search across multiple collections simultaneously.
        
        Args:
            query: Search query
            collections: List of collection names to search (default: all)
            limit_per_collection: Max results per collection
            min_relevance: Minimum relevance score threshold
        
        Returns:
            Dict mapping collection names to search results
        """
        if collections is None:
            collections = [self.HTS_NOTES, self.RULINGS, self.REFUSALS, self.POLICY, self.EVENTS]
        
        results = {}
        
        for collection_name in collections:
            try:
                if collection_name == self.HTS_NOTES:
                    collection_results = self.search_hts_notes(query, limit=limit_per_collection)
                elif collection_name == self.RULINGS:
                    collection_results = self.search_rulings(query, limit=limit_per_collection)
                elif collection_name == self.REFUSALS:
                    collection_results = self.search_refusals(query, limit=limit_per_collection)
                elif collection_name == self.POLICY:
                    collection_results = self.search_policy(query, limit=limit_per_collection)
                elif collection_name == self.EVENTS:
                    collection_results = self.search_events(query, limit=limit_per_collection)
                else:
                    continue
                
                # Filter by minimum relevance
                filtered_results = [
                    result for result in collection_results
                    if result.get("relevance", 0.0) >= min_relevance
                ]
                
                results[collection_name] = filtered_results
                
            except Exception as e:
                logger.error(f"Error searching collection {collection_name}: {e}")
                results[collection_name] = []
        
        return results
    
    def add_compliance_event(
        self,
        event_id: str,
        client_id: str,
        sku_id: str,
        lane_id: str,
        event_type: str,
        risk_level: str,
        title: str,
        summary: str,
        metadata: Dict[str, Any] = None
    ) -> bool:
        """
        Add a compliance event to the events collection.
        
        Args:
            event_id: Unique event identifier
            client_id: Client identifier
            sku_id: SKU identifier
            lane_id: Lane identifier
            event_type: Type of compliance event
            risk_level: Risk severity level
            title: Event title
            summary: Event summary/description
            metadata: Additional metadata
        
        Returns:
            True if successful, False otherwise
        """
        try:
            collection = self.get_collection(self.EVENTS)
            
            # Prepare document content
            content = f"Title: {title}\n\nSummary: {summary}"
            
            # Prepare metadata
            doc_metadata = {
                "event_id": event_id,
                "client_id": client_id,
                "sku_id": sku_id,
                "lane_id": lane_id,
                "event_type": event_type,
                "risk_level": risk_level,
                "title": title,
                "created_at": datetime.utcnow().isoformat() + "Z",
                **(metadata or {})
            }
            
            # Add document
            collection.add_texts(
                texts=[content],
                metadatas=[doc_metadata],
                ids=[event_id]
            )
            
            logger.info(f"Added compliance event {event_id} to collection")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add compliance event {event_id}: {e}")
            return False
    
    def update_document_metadata(
        self,
        collection_name: str,
        document_id: str,
        metadata_updates: Dict[str, Any]
    ) -> bool:
        """
        Update metadata for a specific document.
        
        Args:
            collection_name: Name of the collection
            document_id: Document identifier
            metadata_updates: Metadata fields to update
        
        Returns:
            True if successful, False otherwise
        """
        try:
            collection = self.get_collection(collection_name)
            
            # ChromaDB doesn't support direct metadata updates
            # This would require retrieving the document and re-adding it
            # For now, log the operation
            logger.info(f"Metadata update requested for {document_id} in {collection_name}")
            logger.info(f"Updates: {metadata_updates}")
            
            # In a full implementation, you would:
            # 1. Retrieve the existing document
            # 2. Update its metadata
            # 3. Delete the old document
            # 4. Add the updated document
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to update metadata for {document_id}: {e}")
            return False
    
    def delete_documents_by_filter(
        self,
        collection_name: str,
        where_filter: Dict[str, Any]
    ) -> int:
        """
        Delete documents matching a filter.
        
        Args:
            collection_name: Name of the collection
            where_filter: Filter criteria
        
        Returns:
            Number of documents deleted
        """
        try:
            collection = self.get_collection(collection_name)
            
            # ChromaDB delete by filter
            # This is a simplified implementation
            logger.info(f"Delete requested for {collection_name} with filter: {where_filter}")
            
            # In a full implementation, you would use collection.delete()
            # with the appropriate filter
            
            return 0  # Placeholder
            
        except Exception as e:
            logger.error(f"Failed to delete documents from {collection_name}: {e}")
            return 0
    
    def _filter_by_date(
        self,
        results: List[Dict[str, Any]],
        date_from: str = None,
        date_to: str = None
    ) -> List[Dict[str, Any]]:
        """
        Filter results by date range.
        
        Args:
            results: List of search results
            date_from: Start date (ISO format)
            date_to: End date (ISO format)
        
        Returns:
            Filtered results
        """
        if not date_from and not date_to:
            return results
        
        filtered = []
        
        for result in results:
            created_at = result.get("metadata", {}).get("created_at")
            if not created_at:
                continue
            
            try:
                doc_date = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                
                if date_from:
                    from_date = datetime.fromisoformat(date_from.replace("Z", "+00:00"))
                    if doc_date < from_date:
                        continue
                
                if date_to:
                    to_date = datetime.fromisoformat(date_to.replace("Z", "+00:00"))
                    if doc_date > to_date:
                        continue
                
                filtered.append(result)
                
            except Exception as e:
                logger.warning(f"Error parsing date {created_at}: {e}")
                continue
        
        return filtered
    
    def get_collection_health(self) -> Dict[str, Any]:
        """
        Get health status of all collections.
        
        Returns:
            Health status information
        """
        health = {
            "status": "healthy",
            "collections": {},
            "total_documents": 0,
            "last_checked": datetime.utcnow().isoformat() + "Z"
        }
        
        for name, collection in self._collections.items():
            try:
                count = collection._collection.count()
                health["collections"][name] = {
                    "status": "healthy",
                    "document_count": count,
                    "last_updated": None  # Would need to track this separately
                }
                health["total_documents"] += count
                
            except Exception as e:
                health["collections"][name] = {
                    "status": "error",
                    "error": str(e)
                }
                health["status"] = "degraded"
        
        return health
    
    def seed_sample_data(self):
        """Seed collections with sample compliance data."""
        logger.info("Seeding compliance collections with sample data...")
        
        # Seed HTS notes
        self._seed_hts_notes()
        
        # Seed rulings
        self._seed_rulings()
        
        # Seed refusals
        self._seed_refusals()
        
        # Seed policy
        self._seed_policy()
        
        # Seed events
        self._seed_events()
        
        logger.info("Sample data seeding complete")
    
    def _seed_hts_notes(self):
        """Seed HTS notes collection."""
        hts_collection = self.get_collection(self.HTS_NOTES)
        
        sample_notes = [
            {
                "content": "HTS 8517.12.00 covers cellular telephones and smartphones. Duty-free under MFN. Requires FCC equipment authorization. Section 301 additional duties may apply for China origin.",
                "metadata": {
                    "hts_code": "8517.12.00",
                    "chapter": "85",
                    "duty_rate": "Free",
                    "special_requirements": "FCC authorization, Section 301"
                }
            },
            {
                "content": "HTS 8708.30.50 for brake pads and brake linings for motor vehicles. General duty rate 2.5%. USMCA preferential rate available. Country of origin marking required.",
                "metadata": {
                    "hts_code": "8708.30.50",
                    "chapter": "87",
                    "duty_rate": "2.5%",
                    "special_requirements": "Country of origin marking, USMCA eligible"
                }
            },
            {
                "content": "HTS 6203.42.40 for men's cotton trousers. Duty rate 16.6% plus cotton content categories. Textile visa may be required from certain countries. Subject to Section 301 China tariffs.",
                "metadata": {
                    "hts_code": "6203.42.40",
                    "chapter": "62",
                    "duty_rate": "16.6%",
                    "special_requirements": "Textile visa, Cotton category, Section 301"
                }
            }
        ]
        
        hts_collection.add_texts(
            texts=[note["content"] for note in sample_notes],
            metadatas=[note["metadata"] for note in sample_notes]
        )
        
        logger.info(f"Seeded {len(sample_notes)} HTS notes")
    
    def _seed_rulings(self):
        """Seed rulings collection."""
        rulings_collection = self.get_collection(self.RULINGS)
        
        sample_rulings = [
            {
                "content": "CBP Ruling N312345: Cellular phones with dual SIM capability are classified under HTS 8517.12.00. The dual SIM feature does not change the classification as the essential character remains a cellular telephone.",
                "metadata": {
                    "ruling_number": "N312345",
                    "hts_code": "8517.12.00",
                    "date": "2024-12-15",
                    "topic": "cellular phones"
                }
            },
            {
                "content": "CBP Ruling N312346: Brake pads designed specifically for passenger vehicles of heading 8703 are properly classified under HTS 8708.30.50. Parts must be identifiable as being for motor vehicles.",
                "metadata": {
                    "ruling_number": "N312346",
                    "hts_code": "8708.30.50",
                    "date": "2024-11-20",
                    "topic": "auto parts"
                }
            },
            {
                "content": "CBP Ruling N312347: Men's trousers of cotton, not knitted or crocheted, are classified under HTS 6203.42.40. Subject to textile category limits and quota requirements based on country of origin.",
                "metadata": {
                    "ruling_number": "N312347",
                    "hts_code": "6203.42.40",
                    "date": "2024-10-10",
                    "topic": "textiles"
                }
            }
        ]
        
        rulings_collection.add_texts(
            texts=[ruling["content"] for ruling in sample_rulings],
            metadatas=[ruling["metadata"] for ruling in sample_rulings]
        )
        
        logger.info(f"Seeded {len(sample_rulings)} rulings")
    
    def _seed_refusals(self):
        """Seed refusals collection."""
        refusals_collection = self.get_collection(self.REFUSALS)
        
        sample_refusals = [
            {
                "content": "FDA refusal trend for seafood from China: 15 refusals in past 90 days, primarily due to Salmonella contamination in frozen shrimp (HTS 0306.17). Increased inspection rates for this product category.",
                "metadata": {
                    "country": "CN",
                    "product": "seafood",
                    "hts_code": "0306.17",
                    "reason": "Salmonella",
                    "period": "2024-Q4"
                }
            },
            {
                "content": "FSIS refusal for fresh beef from Brazil: Lack of equivalency documentation. Establishment not on eligible establishments list. Applies to HTS 0201.30 and related beef products.",
                "metadata": {
                    "country": "BR",
                    "product": "beef",
                    "hts_code": "0201.30",
                    "reason": "No equivalency",
                    "period": "2025-01"
                }
            },
            {
                "content": "FDA refusals for dried mushrooms from China: Pesticide residue violations. 8 refusals in past 60 days for HTS 0712.39. Recommend additional testing for shipments from this origin.",
                "metadata": {
                    "country": "CN",
                    "product": "mushrooms",
                    "hts_code": "0712.39",
                    "reason": "Pesticide residue",
                    "period": "2024-Q4"
                }
            }
        ]
        
        refusals_collection.add_texts(
            texts=[refusal["content"] for refusal in sample_refusals],
            metadatas=[refusal["metadata"] for refusal in sample_refusals]
        )
        
        logger.info(f"Seeded {len(sample_refusals)} refusal records")
    
    def _seed_policy(self):
        """Seed policy collection."""
        policy_collection = self.get_collection(self.POLICY)
        
        sample_policies = [
            {
                "content": "Section 301 China Tariffs Update: Additional 25% duties remain in effect for List 3 and List 4 products including most electronics and consumer goods. Product-specific exclusions available through USTR process.",
                "metadata": {
                    "category": "tariffs",
                    "region": "China",
                    "effective_date": "2024-01-01",
                    "authority": "USTR"
                }
            },
            {
                "content": "USMCA Rules of Origin: Automotive parts must meet regional value content requirements of 75% for duty-free treatment. Labor value content requirements also apply. Documentation must be maintained for 5 years.",
                "metadata": {
                    "category": "free_trade",
                    "region": "USMCA",
                    "effective_date": "2020-07-01",
                    "authority": "CBP"
                }
            },
            {
                "content": "Uyghur Forced Labor Prevention Act: All imports from Xinjiang region presumed to be made with forced labor unless proven otherwise. Enhanced due diligence required for supply chains with China exposure.",
                "metadata": {
                    "category": "sanctions",
                    "region": "China",
                    "effective_date": "2022-06-21",
                    "authority": "CBP"
                }
            }
        ]
        
        policy_collection.add_texts(
            texts=[policy["content"] for policy in sample_policies],
            metadatas=[policy["metadata"] for policy in sample_policies]
        )
        
        logger.info(f"Seeded {len(sample_policies)} policy documents")
    
    def _seed_events(self):
        """Seed compliance events collection."""
        events_collection = self.get_collection(self.EVENTS)
        
        sample_events = [
            {
                "content": "Title: New OFAC Sanctions Alert\n\nSummary: Shanghai Electronics Co. added to OFAC Entity List effective 2025-01-15. Enhanced due diligence required for all transactions.",
                "metadata": {
                    "event_id": "evt_001",
                    "client_id": "client_ABC",
                    "sku_id": "SKU-123",
                    "lane_id": "CNSHA-USLAX-ocean",
                    "event_type": "SANCTIONS",
                    "risk_level": "warn",
                    "title": "New OFAC Sanctions Alert",
                    "created_at": "2025-01-15T10:00:00Z"
                }
            },
            {
                "content": "Title: HTS Duty Rate Change\n\nSummary: HTS 8708.30.50 duty rate increased from 2.5% to 3.0% effective 2025-02-01. Affects brake pad imports from all origins.",
                "metadata": {
                    "event_id": "evt_002",
                    "client_id": "client_ABC",
                    "sku_id": "SKU-456",
                    "lane_id": "MXNLD-USTX-truck",
                    "event_type": "HTS",
                    "risk_level": "info",
                    "title": "HTS Duty Rate Change",
                    "created_at": "2025-01-20T14:30:00Z"
                }
            },
            {
                "content": "Title: FDA Refusal Trend Alert\n\nSummary: Increased FDA refusals for frozen shrimp from China due to Salmonella contamination. 15 refusals in past 90 days for HTS 0306.17.",
                "metadata": {
                    "event_id": "evt_003",
                    "client_id": "client_DEF",
                    "sku_id": "SKU-789",
                    "lane_id": "CNSHA-USLAX-ocean",
                    "event_type": "HEALTH_SAFETY",
                    "risk_level": "critical",
                    "title": "FDA Refusal Trend Alert",
                    "created_at": "2025-01-22T09:15:00Z"
                }
            }
        ]
        
        events_collection.add_texts(
            texts=[event["content"] for event in sample_events],
            metadatas=[event["metadata"] for event in sample_events],
            ids=[event["metadata"]["event_id"] for event in sample_events]
        )
        
        logger.info(f"Seeded {len(sample_events)} compliance events")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics for all compliance collections."""
        if not self._initialized:
            return {"error": "Collections not initialized"}
        
        stats = {}
        for name, collection in self._collections.items():
            try:
                count = collection._collection.count()
                stats[name] = {"count": count, "status": "active"}
            except Exception as e:
                stats[name] = {"error": str(e)}
        
        return stats


# Global instance
compliance_collections = ComplianceCollections()
