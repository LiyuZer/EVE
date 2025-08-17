import os
import chromadb
from typing import List, Dict, Optional
from datetime import datetime
import uuid


# Eve's memory uses given embeddings for a semantic database.
# It stores and retrieves context based on semantic embeddings.
class EveMemory:
    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize memory with a persistent ChromaDB client.
        Priority for path:
        1) Explicit db_path argument
        2) EVE_MEMORY_PATH environment variable
        3) Default "eve_memory.db"
        """
        path = db_path or os.getenv("EVE_MEMORY_PATH", "eve_memory.db")
        self.client = chromadb.PersistentClient(path=path)
        self.collection_name = "eve_memory"
        self.collection = self.client.get_or_create_collection(name=self.collection_name)

    def store_node(self, embedding: List[float], content: str, metadata: Optional[Dict] = None):
        node_hash = str(uuid.uuid4())  # Generate a unique identifier for the node
        if metadata is None:
            metadata = {}
        metadata['timestamp'] = datetime.now().isoformat()
        self.collection.add(
            ids=[node_hash],
            embeddings=[embedding],
            documents=[content],
            metadatas=[metadata]
        )

    def retrieve_node(self, embedding: List[float]) -> Optional[Dict]:
        results = self.collection.query(
            query_embeddings=[embedding],
            n_results=2  # Retrieve top 2 results
        )

        if results['documents']:
            return results['documents'][0]
        else:
            return None

    def clear_memory(self) -> None:
        """Safely clear all items from the collection under the configured path.
        This drops the collection and recreates it, ensuring a fresh, empty state.
        Idempotent: safe to call multiple times.
        """
        try:
            self.client.delete_collection(self.collection_name)
        except Exception:
            # If collection does not exist or is already gone, ignore
            pass
        # Recreate a fresh collection handle
        self.collection = self.client.get_or_create_collection(name=self.collection_name)