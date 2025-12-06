import os
import logging
from flask import current_app

# Configure logging
logger = logging.getLogger(__name__)

class RAGService:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(RAGService, cls).__new__(cls)
            cls._instance.initialized = False
        return cls._instance

    def initialize(self):
        if self.initialized:
            return

        try:
            import chromadb
            from chromadb.config import Settings
            from sentence_transformers import SentenceTransformer
            
            # Setup persistence directory
            base_dir = os.path.abspath(os.path.dirname(__file__))
            persist_dir = os.path.join(base_dir, '..', '..', 'instance', 'chroma_db')
            os.makedirs(persist_dir, exist_ok=True)
            
            # Initialize Chroma Client
            self.client = chromadb.PersistentClient(path=persist_dir)
            
            # Initialize Embedding Model (downloaded on first run)
            # 'all-MiniLM-L6-v2' is fast and good for general purpose
            self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
            
            self.initialized = True
            logger.info(f"RAG Service initialized. DB Path: {persist_dir}")
            
        except ImportError as e:
            logger.error(f"RAG dependencies missing: {e}")
            self.initialized = False
        except Exception as e:
            logger.error(f"RAG initialization failed: {e}")
            self.initialized = False

    def _get_collection(self, project_id):
        if not self.initialized:
            return None
        
        collection_name = f"project_{project_id}_docs"
        try:
            return self.client.get_or_create_collection(name=collection_name)
        except Exception as e:
            logger.error(f"Error getting collection {collection_name}: {e}")
            return None

    def _generate_embeddings(self, texts):
        if not self.initialized:
            return []
        return self.embedding_model.encode(texts).tolist()

    def upsert_document(self, project_id, doc_filename, content):
        """
        Splits document into chunks and indexes them.
        """
        if not self.initialized or not content.strip():
            return False

        collection = self._get_collection(project_id)
        if not collection:
            return False

        # Simple chunking strategy: Split by double newlines (paragraphs)
        # then group if too small.
        paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
        
        if not paragraphs:
            return False

        # Prepare data for Chroma
        ids = []
        documents = []
        metadatas = []
        embeddings = []

        # First, delete existing entries for this file to avoid duplicates
        # Chroma doesn't support "delete by metadata" easily in all versions, 
        # but we can try to manage IDs deterministically or just query-delete.
        # For simplicity in this MVP, we might just append, but that causes bloat.
        # Better: Use filename in ID.
        
        # Let's delete old chunks for this file first
        try:
            collection.delete(where={"filename": doc_filename})
        except Exception:
            pass # Collection might be empty

        for i, para in enumerate(paragraphs):
            chunk_id = f"{doc_filename}_{i}"
            ids.append(chunk_id)
            documents.append(para)
            metadatas.append({"filename": doc_filename, "chunk_index": i})
        
        # Generate embeddings in batch
        embeddings = self._generate_embeddings(documents)

        try:
            collection.add(
                ids=ids,
                documents=documents,
                embeddings=embeddings,
                metadatas=metadatas
            )
            logger.info(f"Indexed {len(documents)} chunks for {doc_filename}")
            return True
        except Exception as e:
            logger.error(f"Error indexing document {doc_filename}: {e}")
            return False

    def query_context(self, project_id, query_text, n_results=3):
        """
        Retrieves relevant context for a query.
        """
        if not self.initialized:
            return ""

        collection = self._get_collection(project_id)
        if not collection:
            return ""

        try:
            query_embedding = self._generate_embeddings([query_text])
            
            results = collection.query(
                query_embeddings=query_embedding,
                n_results=n_results
            )
            
            # results['documents'] is a list of lists
            if not results['documents']:
                return ""
                
            context_parts = []
            for i, doc_list in enumerate(results['documents']):
                for j, doc_text in enumerate(doc_list):
                    meta = results['metadatas'][i][j]
                    filename = meta.get('filename', 'Unknown')
                    context_parts.append(f"--- From {filename} ---\n{doc_text}")
            
            return "\n\n".join(context_parts)
            
        except Exception as e:
            logger.error(f"Error querying context: {e}")
            return ""

# Global instance
rag_service = RAGService()
