"""ChromaDB collections for compliance data."""

from typing import List, Dict, Any, Optional
from langchain_chroma import Chroma
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
                "score": score
            }
            for doc, score in results
        ]
    
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
                    "special_requirements": ["FCC authorization", "Section 301"]
                }
            },
            {
                "content": "HTS 8708.30.50 for brake pads and brake linings for motor vehicles. General duty rate 2.5%. USMCA preferential rate available. Country of origin marking required.",
                "metadata": {
                    "hts_code": "8708.30.50",
                    "chapter": "87",
                    "duty_rate": "2.5%",
                    "special_requirements": ["Country of origin marking", "USMCA eligible"]
                }
            },
            {
                "content": "HTS 6203.42.40 for men's cotton trousers. Duty rate 16.6% plus cotton content categories. Textile visa may be required from certain countries. Subject to Section 301 China tariffs.",
                "metadata": {
                    "hts_code": "6203.42.40",
                    "chapter": "62",
                    "duty_rate": "16.6%",
                    "special_requirements": ["Textile visa", "Cotton category", "Section 301"]
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
