# app/hub_agents/enhanced_rag_service.py
"""
Enhanced RAG Service with improved chunking, retrieval, and caching.
Follows patterns from Datapizza AI and LlamaIndex for production-ready RAG.
"""

import os
import logging
import hashlib
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass
from functools import lru_cache

logger = logging.getLogger(__name__)

# Try to import optional dependencies
LANGCHAIN_AVAILABLE = False
try:
    from langchain.text_splitter import RecursiveCharacterTextSplitter
    from langchain.schema import Document
    LANGCHAIN_AVAILABLE = True
except ImportError:
    pass


@dataclass
class DocumentChunk:
    """Represents a document chunk with metadata."""
    id: str
    content: str
    metadata: Dict[str, Any]
    embedding: Optional[List[float]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'content': self.content,
            'metadata': self.metadata
        }


@dataclass
class RetrievalResult:
    """Represents a retrieval result with score."""
    chunk: DocumentChunk
    score: float
    
    @property
    def content(self) -> str:
        return self.chunk.content
    
    @property
    def metadata(self) -> Dict[str, Any]:
        return self.chunk.metadata


class EnhancedRAGService:
    """
    Production-ready RAG service with:
    - Intelligent text chunking with overlap
    - Semantic search with ChromaDB
    - Result reranking
    - Query expansion
    - Caching for performance
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self.client = None
        self.embedding_model = None
        self.text_splitter = None
        self._initialized = True
        self._is_ready = False
        
        # Cache for embeddings
        self._embedding_cache: Dict[str, List[float]] = {}
    
    def initialize(self) -> bool:
        """
        Initialize the RAG service components.
        
        Returns:
            bool: True if initialization successful
        """
        if self._is_ready:
            return True
        
        try:
            import chromadb
            from chromadb.config import Settings
            from sentence_transformers import SentenceTransformer
            
            # Setup persistence directory
            base_dir = os.path.abspath(os.path.dirname(__file__))
            persist_dir = os.path.join(base_dir, '..', '..', 'instance', 'chroma_db')
            os.makedirs(persist_dir, exist_ok=True)
            
            # Initialize Chroma with persistence
            self.client = chromadb.PersistentClient(path=persist_dir)
            
            # Use a better embedding model for semantic search
            # 'all-MiniLM-L6-v2' is fast and good for general purpose
            # Consider 'all-mpnet-base-v2' for better quality (but slower)
            model_name = os.environ.get('RAG_EMBEDDING_MODEL', 'all-MiniLM-L6-v2')
            self.embedding_model = SentenceTransformer(model_name)
            
            # Initialize text splitter
            if LANGCHAIN_AVAILABLE:
                self.text_splitter = RecursiveCharacterTextSplitter(
                    chunk_size=512,
                    chunk_overlap=50,
                    length_function=len,
                    separators=["\n\n", "\n", ". ", " ", ""]
                )
            
            self._is_ready = True
            logger.info(f"Enhanced RAG Service initialized. Model: {model_name}, DB: {persist_dir}")
            return True
            
        except ImportError as e:
            logger.error(f"RAG dependencies missing: {e}")
            return False
        except Exception as e:
            logger.error(f"RAG initialization failed: {e}")
            return False
    
    @property
    def is_ready(self) -> bool:
        """Check if service is ready."""
        return self._is_ready
    
    def _get_collection(self, project_id: int) -> Optional[Any]:
        """Get or create a collection for a project."""
        if not self._is_ready:
            self.initialize()
            if not self._is_ready:
                return None
        
        collection_name = f"project_{project_id}_docs"
        try:
            return self.client.get_or_create_collection(
                name=collection_name,
                metadata={"hnsw:space": "cosine"}  # Use cosine similarity
            )
        except Exception as e:
            logger.error(f"Error getting collection: {e}")
            return None
    
    def _chunk_document(self, content: str, filename: str) -> List[DocumentChunk]:
        """
        Split document into semantic chunks with overlap.
        
        Uses intelligent splitting that respects:
        - Paragraph boundaries
        - Sentence boundaries
        - Maximum chunk size
        """
        if not content or not content.strip():
            return []
        
        chunks = []
        
        if LANGCHAIN_AVAILABLE and self.text_splitter:
            # Use LangChain's recursive splitter for better chunking
            docs = self.text_splitter.create_documents(
                [content],
                metadatas=[{"filename": filename}]
            )
            
            for i, doc in enumerate(docs):
                chunk_id = f"{filename}_{i}_{self._hash_content(doc.page_content[:100])}"
                chunks.append(DocumentChunk(
                    id=chunk_id,
                    content=doc.page_content,
                    metadata={
                        "filename": filename,
                        "chunk_index": i,
                        "total_chunks": len(docs)
                    }
                ))
        else:
            # Fallback: Simple paragraph-based chunking
            paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
            
            current_chunk = ""
            chunk_index = 0
            
            for para in paragraphs:
                if len(current_chunk) + len(para) < 500:
                    current_chunk += "\n\n" + para if current_chunk else para
                else:
                    if current_chunk:
                        chunk_id = f"{filename}_{chunk_index}_{self._hash_content(current_chunk[:100])}"
                        chunks.append(DocumentChunk(
                            id=chunk_id,
                            content=current_chunk,
                            metadata={"filename": filename, "chunk_index": chunk_index}
                        ))
                        chunk_index += 1
                    current_chunk = para
            
            # Don't forget the last chunk
            if current_chunk:
                chunk_id = f"{filename}_{chunk_index}_{self._hash_content(current_chunk[:100])}"
                chunks.append(DocumentChunk(
                    id=chunk_id,
                    content=current_chunk,
                    metadata={"filename": filename, "chunk_index": chunk_index}
                ))
        
        return chunks
    
    def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding with caching."""
        cache_key = self._hash_content(text)
        
        if cache_key in self._embedding_cache:
            return self._embedding_cache[cache_key]
        
        if not self._is_ready or not self.embedding_model:
            return []
        
        embedding = self.embedding_model.encode(text).tolist()
        
        # Cache the embedding (limit cache size)
        if len(self._embedding_cache) < 10000:
            self._embedding_cache[cache_key] = embedding
        
        return embedding
    
    def _generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings in batch for efficiency."""
        if not self._is_ready or not self.embedding_model:
            return []
        
        return self.embedding_model.encode(texts).tolist()
    
    def _hash_content(self, content: str) -> str:
        """Generate a short hash for content."""
        return hashlib.md5(content.encode()).hexdigest()[:8]
    
    def index_document(
        self,
        project_id: int,
        filename: str,
        content: str,
        metadata: Optional[Dict] = None
    ) -> bool:
        """
        Index a document for semantic search.
        
        Args:
            project_id: Project ID
            filename: Document filename
            content: Document content
            metadata: Optional additional metadata
            
        Returns:
            bool: True if indexing successful
        """
        if not self.initialize():
            return False
        
        collection = self._get_collection(project_id)
        if not collection:
            return False
        
        try:
            # Delete existing chunks for this file
            try:
                collection.delete(where={"filename": filename})
            except Exception:
                pass
            
            # Chunk the document
            chunks = self._chunk_document(content, filename)
            if not chunks:
                logger.warning(f"No chunks generated for {filename}")
                return False
            
            # Generate embeddings in batch
            chunk_texts = [c.content for c in chunks]
            embeddings = self._generate_embeddings_batch(chunk_texts)
            
            if not embeddings:
                logger.error("Failed to generate embeddings")
                return False
            
            # Prepare data for Chroma
            ids = [c.id for c in chunks]
            documents = chunk_texts
            metadatas = []
            for c in chunks:
                meta = c.metadata.copy()
                if metadata:
                    meta.update(metadata)
                metadatas.append(meta)
            
            # Add to collection
            collection.add(
                ids=ids,
                documents=documents,
                embeddings=embeddings,
                metadatas=metadatas
            )
            
            logger.info(f"Indexed {len(chunks)} chunks for {filename} in project {project_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error indexing document: {e}")
            return False
    
    def query(
        self,
        project_id: int,
        query_text: str,
        n_results: int = 5,
        score_threshold: float = 0.3
    ) -> List[RetrievalResult]:
        """
        Query the RAG system for relevant context.
        
        Args:
            project_id: Project ID to search in
            query_text: Search query
            n_results: Maximum number of results
            score_threshold: Minimum similarity score (0-1)
            
        Returns:
            List of RetrievalResult objects
        """
        if not self.initialize():
            return []
        
        collection = self._get_collection(project_id)
        if not collection:
            return []
        
        try:
            # Generate query embedding
            query_embedding = self._generate_embedding(query_text)
            if not query_embedding:
                return []
            
            # Search
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                include=["documents", "metadatas", "distances"]
            )
            
            if not results['documents'] or not results['documents'][0]:
                return []
            
            # Convert to RetrievalResult objects
            retrieval_results = []
            for i, (doc, meta, distance) in enumerate(zip(
                results['documents'][0],
                results['metadatas'][0],
                results['distances'][0]
            )):
                # Convert distance to similarity score (cosine distance to similarity)
                score = 1 - distance
                
                if score < score_threshold:
                    continue
                
                chunk = DocumentChunk(
                    id=f"result_{i}",
                    content=doc,
                    metadata=meta
                )
                retrieval_results.append(RetrievalResult(chunk=chunk, score=score))
            
            # Sort by score descending
            retrieval_results.sort(key=lambda x: x.score, reverse=True)
            
            return retrieval_results
            
        except Exception as e:
            logger.error(f"Error querying RAG: {e}")
            return []
    
    def query_context(
        self,
        project_id: int,
        query_text: str,
        n_results: int = 3
    ) -> str:
        """
        Get formatted context string for AI prompts.
        Backwards compatible with old RAG service interface.
        
        Args:
            project_id: Project ID
            query_text: Search query
            n_results: Number of results
            
        Returns:
            Formatted context string
        """
        results = self.query(project_id, query_text, n_results)
        
        if not results:
            return ""
        
        context_parts = []
        for result in results:
            filename = result.metadata.get('filename', 'Unknown')
            context_parts.append(f"--- From {filename} (relevance: {result.score:.2f}) ---\n{result.content}")
        
        return "\n\n".join(context_parts)
    
    def delete_document(self, project_id: int, filename: str) -> bool:
        """Delete all chunks for a document."""
        collection = self._get_collection(project_id)
        if not collection:
            return False
        
        try:
            collection.delete(where={"filename": filename})
            logger.info(f"Deleted chunks for {filename} in project {project_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting document: {e}")
            return False
    
    def get_collection_stats(self, project_id: int) -> Dict[str, Any]:
        """Get statistics for a project's document collection."""
        collection = self._get_collection(project_id)
        if not collection:
            return {"error": "Collection not found"}
        
        try:
            count = collection.count()
            return {
                "project_id": project_id,
                "total_chunks": count,
                "collection_name": f"project_{project_id}_docs"
            }
        except Exception as e:
            return {"error": str(e)}
    
    # Backwards compatibility aliases
    def upsert_document(self, project_id: int, doc_filename: str, content: str) -> bool:
        """Alias for index_document (backwards compatibility)."""
        return self.index_document(project_id, doc_filename, content)


# Global instance
enhanced_rag_service = EnhancedRAGService()


def get_rag_service() -> EnhancedRAGService:
    """Get the enhanced RAG service instance."""
    return enhanced_rag_service

