"""
Vector Memory - Semantic long-term memory for Project Myriad using ChromaDB.

This module handles semantic memory storage and retrieval using vector embeddings.
Unlike simple chronological memory, this allows the AI to recall contextually
relevant past conversations regardless of when they happened.

Architecture:
- ChromaDB: Vector database for semantic search
- sentence-transformers/all-MiniLM-L6-v2: Fast, local embedding model
- Metadata: timestamp, role, user_id, origin_persona, visibility_scope
"""

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Any, Optional
from datetime import datetime
import os


class VectorMemory:
    """Manages semantic long-term memory using ChromaDB and embeddings."""

    def __init__(
        self,
        embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2",
        chroma_db_path: str = "database/chroma_db",
        collection_name: str = "myriad_memories",
    ):
        """
        Initialize the vector memory system.

        Args:
            embedding_model: Sentence transformer model for embeddings
            chroma_db_path: Path to ChromaDB persistent storage
            collection_name: Name of the ChromaDB collection
        """
        # Ensure database directory exists
        os.makedirs(chroma_db_path, exist_ok=True)

        # Initialize embedding model
        print(f"Loading embedding model: {embedding_model}...")
        self.embedding_model = SentenceTransformer(embedding_model)
        print(f"✓ Embedding model loaded")

        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(
            path=chroma_db_path,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True,
            ),
        )

        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"description": "Semantic memory for Project Myriad"},
        )

        print(
            f"✓ ChromaDB collection: {collection_name} ({self.collection.count()} memories)"
        )

    def add_memory(
        self,
        memory_id: str,
        content: str,
        user_id: str,
        origin_persona: str,
        role: str,
        visibility_scope: str = "ISOLATED",
        timestamp: Optional[str] = None,
    ):
        """
        Add a memory to the vector database.

        Args:
            memory_id: Unique ID for this memory (from SQLite)
            content: The message content to embed
            user_id: User identifier
            origin_persona: The persona that recorded this memory
            role: 'user', 'assistant', or 'system'
            visibility_scope: 'GLOBAL' or 'ISOLATED'
            timestamp: ISO timestamp (defaults to now)
        """
        if timestamp is None:
            timestamp = datetime.utcnow().isoformat()

        # Generate embedding
        embedding = self.embedding_model.encode(content).tolist()

        # Add to ChromaDB
        self.collection.add(
            ids=[memory_id],
            embeddings=[embedding],
            documents=[content],
            metadatas=[
                {
                    "user_id": user_id,
                    "origin_persona": origin_persona,
                    "role": role,
                    "visibility_scope": visibility_scope,
                    "timestamp": timestamp,
                }
            ],
        )

    def search_semantic_memories(
        self,
        query: str,
        user_id: str,
        current_persona: str,
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Search for semantically similar memories using vector similarity.

        Applies the Automated Discretion Engine filters:
        - visibility_scope = 'GLOBAL' (shared), OR
        - origin_persona = current_persona (isolated to this persona)

        Args:
            query: The query text to search for
            user_id: User identifier
            current_persona: Currently active persona
            top_k: Number of results to return

        Returns:
            List of memory dictionaries with content, metadata, and distance scores
        """
        # Generate query embedding
        query_embedding = self.embedding_model.encode(query).tolist()

        # Build ChromaDB where filter for Automated Discretion Engine
        where_filter = {
            "$and": [
                {"user_id": {"$eq": user_id}},
                {
                    "$or": [
                        {"visibility_scope": {"$eq": "GLOBAL"}},
                        {"origin_persona": {"$eq": current_persona}},
                    ]
                },
            ]
        }

        # Query ChromaDB
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where_filter,
            include=["documents", "metadatas", "distances"],
        )

        # Format results
        memories = []
        if results["ids"] and results["ids"][0]:
            for i in range(len(results["ids"][0])):
                memory = {
                    "id": results["ids"][0][i],
                    "content": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i],
                    "distance": results["distances"][0][i],
                }
                memories.append(memory)

        return memories

    def get_memory_count(self, user_id: Optional[str] = None) -> int:
        """
        Get count of memories in the database.

        Args:
            user_id: If provided, count only for this user

        Returns:
            Number of memories
        """
        if user_id:
            results = self.collection.get(where={"user_id": {"$eq": user_id}})
            return len(results["ids"]) if results["ids"] else 0
        else:
            return self.collection.count()

    def clear_user_memories(self, user_id: str, persona_id: Optional[str] = None):
        """
        Clear memories for a user.

        Args:
            user_id: User identifier
            persona_id: If provided, only clear memories from this persona
        """
        if persona_id:
            where_filter = {
                "$and": [
                    {"user_id": {"$eq": user_id}},
                    {"origin_persona": {"$eq": persona_id}},
                ]
            }
        else:
            where_filter = {"user_id": {"$eq": user_id}}

        # Get matching IDs
        results = self.collection.get(where=where_filter)

        if results["ids"]:
            self.collection.delete(ids=results["ids"])

    def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about the vector memory collection."""
        return {
            "total_memories": self.collection.count(),
            "collection_name": self.collection.name,
            "embedding_model": self.embedding_model.__class__.__name__,
        }
