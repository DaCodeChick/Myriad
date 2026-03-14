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
        chroma_db_path: str = "data/chroma_db",
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
        life_id: Optional[str] = None,
        timestamp: Optional[str] = None,
        importance_score: int = 5,
    ):
        """
        Add a memory to the vector database.

        Args:
            memory_id: Unique ID for this memory (from SQLite)
            content: The message content to embed
            user_id: User identifier
            origin_persona: The persona that recorded this memory
            role: 'user', 'assistant', or 'system'
            visibility_scope: 'GLOBAL', 'USER_SHARED', or 'ISOLATED'
            life_id: Timeline/session ID (optional)
            timestamp: ISO timestamp (defaults to now)
            importance_score: Importance rating 1-10 (default=5)
                1-3: Trivial/casual information
                4-6: Standard facts
                7-9: Significant information
                10: Core anchors (trauma, hard limits)
        """
        if timestamp is None:
            timestamp = datetime.utcnow().isoformat()

        # Clamp importance_score to valid range
        importance_score = max(1, min(10, importance_score))

        # Generate embedding
        embedding = self.embedding_model.encode(content).tolist()

        # Build metadata
        metadata = {
            "user_id": user_id,
            "origin_persona": origin_persona,
            "role": role,
            "visibility_scope": visibility_scope,
            "timestamp": timestamp,
            "importance_score": importance_score,
        }

        # Add life_id if provided
        if life_id:
            metadata["life_id"] = life_id

        # Add to ChromaDB
        self.collection.add(
            ids=[memory_id],
            embeddings=[embedding],
            documents=[content],
            metadatas=[metadata],
        )

    def search_semantic_memories(
        self,
        query: str,
        user_id: str,
        current_persona: str,
        top_k: int = 5,
        life_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search for semantically similar memories using weighted priority scoring.

        Applies the Automated Discretion Engine filters:
        - visibility_scope = 'GLOBAL' (shared across all users/personas), OR
        - visibility_scope = 'USER_SHARED' (shared across this user's personas), OR
        - origin_persona = current_persona (isolated to this persona)
        - life_id = current life (if provided)

        Weighted Priority Scoring:
        - Final Score = (semantic_similarity × SIMILARITY_WEIGHT) + (importance × IMPORTANCE_WEIGHT)
        - Memories are ranked by final score, not just semantic distance

        Args:
            query: The query text to search for
            user_id: User identifier
            current_persona: Currently active persona
            top_k: Number of results to return
            life_id: Optional life/timeline ID to filter by

        Returns:
            List of memory dictionaries with content, metadata, and weighted scores
        """
        # Load weights from environment (fallback to 50/50 split)
        similarity_weight = float(os.getenv("MEMORY_SIMILARITY_WEIGHT", "0.5"))
        importance_weight = float(os.getenv("MEMORY_IMPORTANCE_WEIGHT", "0.5"))

        # Generate query embedding
        query_embedding = self.embedding_model.encode(query).tolist()

        # Build ChromaDB where filter for Automated Discretion Engine
        where_filter = {
            "$and": [
                {"user_id": {"$eq": user_id}},
                {
                    "$or": [
                        {"visibility_scope": {"$eq": "GLOBAL"}},
                        {"visibility_scope": {"$eq": "USER_SHARED"}},
                        {"origin_persona": {"$eq": current_persona}},
                    ]
                },
            ]
        }

        # Add life_id filter if provided
        if life_id:
            where_filter["$and"].append({"life_id": {"$eq": life_id}})

        # Query ChromaDB - fetch more results than needed for re-ranking
        # We fetch 3x top_k to ensure we have enough high-importance memories
        fetch_limit = min(top_k * 3, 50)  # Cap at 50 to avoid excessive fetching

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=fetch_limit,
            where=where_filter,
            include=["documents", "metadatas", "distances"],
        )

        # Format and apply weighted scoring
        memories = []
        if results["ids"] and results["ids"][0]:
            for i in range(len(results["ids"][0])):
                metadata = results["metadatas"][0][i]
                distance = results["distances"][0][i]

                # Convert distance to similarity score (0.0-1.0)
                # ChromaDB typically uses L2 distance, range ~0.0-2.0
                similarity = max(0.0, 1.0 - (distance / 2.0))

                # Get importance score from metadata (default to 5 if missing)
                importance_score = metadata.get("importance_score", 5)
                normalized_importance = importance_score / 10.0

                # Calculate weighted final score
                final_score = (similarity * similarity_weight) + (
                    normalized_importance * importance_weight
                )

                memory = {
                    "id": results["ids"][0][i],
                    "content": results["documents"][0][i],
                    "metadata": metadata,
                    "distance": distance,
                    "similarity": similarity,
                    "final_score": final_score,
                }
                memories.append(memory)

        # Sort by final_score (highest first) and return top_k
        memories.sort(key=lambda m: m["final_score"], reverse=True)
        return memories[:top_k]

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

    def delete_memories_by_ids(self, memory_ids: List[str]):
        """
        Delete specific memories by their IDs.
        Used when rewinding to a save state (FORGET option).

        Args:
            memory_ids: List of memory IDs to delete
        """
        if memory_ids:
            try:
                self.collection.delete(ids=memory_ids)
            except Exception as e:
                print(f"Warning: Failed to delete some vector memories: {e}")

    def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about the vector memory collection."""
        return {
            "total_memories": self.collection.count(),
            "collection_name": self.collection.name,
            "embedding_model": self.embedding_model.__class__.__name__,
        }
