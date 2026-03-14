"""
Knowledge Graph Search - Keyword extraction and entity search for Project Myriad.

This module handles search and query operations for the knowledge graph:
- Keyword extraction from text (NLP)
- Entity search by keywords
- Context formatting for LLM injection

Part of RDSSC Phase 6: Split graph_memory.py into focused modules.
"""

import re
import sqlite3
from typing import List, Dict, Any


class GraphSearch:
    """Handles keyword extraction and search operations for the knowledge graph."""

    def __init__(self, db_path: str, graph_repository):
        """
        Initialize graph search.

        Args:
            db_path: Path to SQLite database file
            graph_repository: GraphRepository instance for entity lookups
        """
        self.db_path = db_path
        self.repository = graph_repository

    def extract_keywords(self, text: str, min_length: int = 3) -> List[str]:
        """
        Extract potential keywords from text for entity matching.

        Simple implementation: Split on whitespace, remove punctuation,
        filter by length, and capitalize for proper noun matching.

        Args:
            text: Input text to extract keywords from
            min_length: Minimum keyword length (default: 3)

        Returns:
            List of extracted keywords
        """
        # Remove common punctuation but keep alphanumeric and spaces
        cleaned = re.sub(r"[^\w\s]", " ", text)

        # Split into words
        words = cleaned.split()

        # Filter by length and remove common stop words
        stop_words = {
            "the",
            "is",
            "are",
            "was",
            "were",
            "and",
            "or",
            "but",
            "in",
            "on",
            "at",
            "to",
            "for",
            "of",
            "with",
            "by",
            "from",
            "as",
            "an",
            "a",
            "this",
            "that",
            "these",
            "those",
            "what",
            "when",
            "where",
            "who",
            "why",
            "how",
        }

        keywords = [
            word
            for word in words
            if len(word) >= min_length and word.lower() not in stop_words
        ]

        # Return unique keywords, preserving case for proper noun matching
        return list(set(keywords))

    def search_entities_by_keywords(self, keywords: List[str]) -> List[Dict[str, Any]]:
        """
        Search for entities matching any of the provided keywords.
        Results are sorted by importance_score (highest first).

        Args:
            keywords: List of search terms

        Returns:
            List of matching entities with their relationships, sorted by importance
        """
        if not keywords:
            return []

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Build query to search for any keyword in entity names
        # Sort by importance_score descending (highest importance first)
        placeholders = " OR ".join(["name LIKE ? COLLATE NOCASE"] * len(keywords))
        query_params = [f"%{kw}%" for kw in keywords]

        cursor.execute(
            f"""
            SELECT DISTINCT name, importance_score
            FROM entities
            WHERE {placeholders}
            ORDER BY importance_score DESC
        """,
            query_params,
        )

        rows = cursor.fetchall()
        conn.close()

        # Get relationships for each matching entity
        results = []
        for row in rows:
            entity_name = row[0]
            entity_importance = row[1] if len(row) > 1 else 5  # Default to 5 if missing
            relationships = self.repository.get_relationships_for_entity(entity_name)
            if relationships:
                results.append(
                    {
                        "entity": entity_name,
                        "importance": entity_importance,
                        "relationships": relationships,
                    }
                )

        return results

    def get_knowledge_context(self, user_message: str) -> str:
        """
        Extract keywords from user message and retrieve relevant knowledge graph context.
        Results are prioritized by importance_score.

        This is the main retrieval function called by AgentCore.

        Args:
            user_message: The user's input message

        Returns:
            Formatted knowledge graph context for injection into system prompt
        """
        # Extract keywords from message
        keywords = self.extract_keywords(user_message)

        if not keywords:
            return ""

        # Search for matching entities
        results = self.search_entities_by_keywords(keywords)

        if not results:
            return ""

        # Format as context for LLM with importance indicators
        context = "\n\n## KNOWLEDGE GRAPH CONTEXT:\n\n"
        context += (
            "Relevant facts from your knowledge graph (sorted by importance):\n\n"
        )

        for result in results:
            entity = result["entity"]
            relationships = result["relationships"]

            context += f"**{entity}:**\n"
            for rel in relationships:
                # Add importance indicator for high-priority relationships
                importance = rel.get("importance_score", 5)
                indicator = ""
                if importance >= 8:
                    indicator = " [CRITICAL]"
                elif importance >= 7:
                    indicator = " [IMPORTANT]"

                context += f"  • {rel['source']} ({rel['source_type']}) {rel['relation']} {rel['target']} ({rel['target_type']}){indicator}\n"
            context += "\n"

        context += "Use this knowledge to inform your response, but only mention it if relevant to the conversation.\n"

        return context
