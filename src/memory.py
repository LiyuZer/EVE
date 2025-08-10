import chromadb
from typing import List, Dict, Optional
from datetime import datetime
import uuid


# Eve's memory uses given embeddings for a semantic database.
# It stores and retrieves context based on semantic embeddings.
class EveMemory:
    def __init__(self, db_path : str = "eve_memory.db"):
        self.client = chromadb.PersistentClient(path=db_path)
        self.collection = self.client.get_or_create_collection(name="eve_memory")

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
