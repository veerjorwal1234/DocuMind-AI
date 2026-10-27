import os
import faiss
import numpy as np
from typing import List, Dict, Any, Optional, Tuple, cast
from langchain.schema import Document
from sentence_transformers import SentenceTransformer

class VectorStore:
    """Handles document embeddings and vector search using FAISS."""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize the vector store.
        
        Args:
            model_name: Name of the sentence transformer model to use
        """
        try:
            self.model = SentenceTransformer(model_name)
            self.dimension = self.model.get_sentence_embedding_dimension()
            self.index = faiss.IndexFlatL2(self.dimension)
            self.documents: List[Any] = []
        except Exception as e:
            raise Exception(f"Error initializing vector store: {str(e)}")
        
    def add_documents(self, documents: List[Any]) -> None:
        """
        Add documents to the vector store.
        
        Args:
            documents: List of documents with page_content to add
        """
        if not documents:
            return
            
        try:
            # Duck-type document objects to support LangChain Document, MockDocument, etc.
            texts = [doc.page_content for doc in documents if hasattr(doc, 'page_content')]
            if not texts:
                return
                
            embeddings = self.model.encode(texts)
            
            # Add documents to the store
            self.documents.extend(documents)
            
            # Add embeddings to the index
            if len(embeddings) > 0:
                self.index.add(np.array(embeddings).astype('float32'))
        except Exception as e:
            raise Exception(f"Error adding documents: {str(e)}")
    
    def similarity_search(self, query: str, k: int = 4) -> List[Any]:
        """
        Perform a similarity search for the query.
        
        Args:
            query: Query string
            k: Number of results to return
            
        Returns:
            List of similar documents ranked by relevance
        """
        if not self.documents:
            return []
            
        try:
            # Get query embedding
            query_embedding = self.model.encode([query])
            
            # Search the index
            D, I = self.index.search(np.array(query_embedding).astype('float32'), k)
            
            # Return the top k documents
            results: List[Any] = []
            for i, idx in enumerate(I[0]):
                if 0 <= idx < len(self.documents):
                    doc = self.documents[idx]
                    # Attach distance score to document metadata if available
                    if hasattr(doc, "metadata") and isinstance(doc.metadata, dict):
                        doc.metadata["distance"] = float(D[0][i]) if i < len(D[0]) else 0.0
                    results.append(doc)
            return results
        except Exception as e:
            raise Exception(f"Error performing similarity search: {str(e)}")
            
    def similarity_search_with_score(self, query: str, k: int = 4) -> List[Tuple[Any, float]]:
        """
        Perform similarity search returning documents with their L2 distance scores.
        
        Args:
            query: Query string
            k: Number of results to return
            
        Returns:
            List of (Document, score) tuples
        """
        if not self.documents:
            return []
            
        try:
            query_embedding = self.model.encode([query])
            D, I = self.index.search(np.array(query_embedding).astype('float32'), k)
            results: List[Tuple[Any, float]] = []
            for i, idx in enumerate(I[0]):
                if 0 <= idx < len(self.documents):
                    dist = float(D[0][i]) if i < len(D[0]) else 0.0
                    results.append((self.documents[idx], dist))
            return results
        except Exception as e:
            raise Exception(f"Error performing similarity search with score: {str(e)}")
    
    def save_index(self, path: str) -> None:
        """
        Save the FAISS index to disk.
        
        Args:
            path: Path to save the index
        """
        faiss.write_index(self.index, path)
        
    def load_index(self, path: str) -> None:
        """
        Load a FAISS index from disk.
        
        Args:
            path: Path to the saved index
        """
        if os.path.exists(path):
            self.index = faiss.read_index(path)