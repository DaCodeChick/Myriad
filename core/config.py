"""
Configuration Management for Project Myriad

Centralizes all environment variable parsing and configuration loading.
Provides type-safe configuration objects with validation and defaults.
"""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class LLMConfig:
    """LLM API configuration."""

    api_key: str
    base_url: str = "https://api.openai.com/v1"
    model: str = "gpt-4"

    @classmethod
    def from_env(cls) -> "LLMConfig":
        """Load LLM configuration from environment variables."""
        api_key = os.getenv("LLM_API_KEY")
        if not api_key:
            raise ValueError("LLM_API_KEY not found in environment")

        return cls(
            api_key=api_key,
            base_url=os.getenv("LLM_BASE_URL", "https://api.openai.com/v1"),
            model=os.getenv("LLM_MODEL", "gpt-4"),
        )


@dataclass
class VisionConfig:
    """Vision API configuration."""

    api_key: str = "not-needed"
    base_url: Optional[str] = None
    model: str = "vision-model"

    @classmethod
    def from_env(cls) -> "VisionConfig":
        """Load vision configuration from environment variables."""
        return cls(
            api_key=os.getenv("VISION_API_KEY", "not-needed"),
            base_url=os.getenv("VISION_BASE_URL"),
            model=os.getenv("VISION_MODEL", "vision-model"),
        )

    @property
    def enabled(self) -> bool:
        """Check if vision is enabled (has base_url configured)."""
        return self.base_url is not None


@dataclass
class MemoryConfig:
    """Memory system configuration."""

    short_term_limit: int = 10
    vector_memory_enabled: bool = True
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    semantic_recall_limit: int = 5
    chroma_db_path: str = "data/chroma_db"

    @classmethod
    def from_env(cls) -> "MemoryConfig":
        """Load memory configuration from environment variables."""
        return cls(
            short_term_limit=int(os.getenv("SHORT_TERM_MEMORY_LIMIT", "10")),
            vector_memory_enabled=os.getenv("VECTOR_MEMORY_ENABLED", "true").lower()
            == "true",
            embedding_model=os.getenv(
                "EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"
            ),
            semantic_recall_limit=int(os.getenv("SEMANTIC_RECALL_LIMIT", "5")),
            chroma_db_path=os.getenv("CHROMA_DB_PATH", "data/chroma_db"),
        )


@dataclass
class ToolsConfig:
    """Tools system configuration."""

    enabled: bool = True
    max_iterations: int = 5

    @classmethod
    def from_env(cls) -> "ToolsConfig":
        """Load tools configuration from environment variables."""
        return cls(
            enabled=os.getenv("TOOLS_ENABLED", "true").lower() == "true",
            max_iterations=int(os.getenv("MAX_TOOL_ITERATIONS", "5")),
        )


@dataclass
class DatabasePaths:
    """Database file paths configuration."""

    graph_db_path: str = "data/knowledge_graph.db"
    limbic_db_path: str = "data/limbic_state.db"
    metacognition_db_path: str = "data/metacognition.db"

    @classmethod
    def from_env(cls) -> "DatabasePaths":
        """Load database paths from environment variables."""
        return cls(
            graph_db_path=os.getenv("GRAPH_DB_PATH", "data/knowledge_graph.db"),
            limbic_db_path=os.getenv("LIMBIC_DB_PATH", "data/limbic_state.db"),
            metacognition_db_path=os.getenv(
                "METACOGNITION_DB_PATH", "data/metacognition.db"
            ),
        )


@dataclass
class FeatureFlags:
    """Feature enable/disable flags."""

    graph_memory_enabled: bool = True
    limbic_enabled: bool = True
    digital_pharmacy_enabled: bool = True
    cadence_degrader_enabled: bool = True
    metacognition_enabled: bool = True
    lives_enabled: bool = True
    show_thoughts_inline: bool = True

    @classmethod
    def from_env(cls) -> "FeatureFlags":
        """Load feature flags from environment variables."""
        return cls(
            graph_memory_enabled=os.getenv("GRAPH_MEMORY_ENABLED", "true").lower()
            == "true",
            limbic_enabled=os.getenv("LIMBIC_ENABLED", "true").lower() == "true",
            digital_pharmacy_enabled=os.getenv(
                "DIGITAL_PHARMACY_ENABLED", "true"
            ).lower()
            == "true",
            cadence_degrader_enabled=os.getenv(
                "CADENCE_DEGRADER_ENABLED", "true"
            ).lower()
            == "true",
            metacognition_enabled=os.getenv("METACOGNITION_ENABLED", "true").lower()
            == "true",
            lives_enabled=os.getenv("LIVES_ENABLED", "true").lower() == "true",
            show_thoughts_inline=os.getenv("SHOW_THOUGHTS_INLINE", "true").lower()
            == "true",
        )


@dataclass
class UniversalRulesConfig:
    """Universal rules configuration."""

    rules: Optional[list[str]] = None

    @classmethod
    def from_env(cls) -> "UniversalRulesConfig":
        """Load universal rules from environment variables."""
        universal_rules_env = os.getenv("UNIVERSAL_RULES")
        rules = None
        if universal_rules_env:
            # Split by pipe and strip whitespace
            rules = [
                rule.strip() for rule in universal_rules_env.split("|") if rule.strip()
            ]
        return cls(rules=rules)


@dataclass
class MyriadConfig:
    """Complete Project Myriad configuration.

    Aggregates all configuration sections for easy access.
    """

    discord_token: str
    llm: LLMConfig
    vision: VisionConfig
    memory: MemoryConfig
    tools: ToolsConfig
    database_paths: DatabasePaths
    features: FeatureFlags
    universal_rules: UniversalRulesConfig

    @classmethod
    def from_env(cls) -> "MyriadConfig":
        """Load complete configuration from environment variables.

        Raises:
            ValueError: If required configuration is missing
        """
        discord_token = os.getenv("DISCORD_TOKEN")
        if not discord_token:
            raise ValueError("DISCORD_TOKEN not found in environment")

        return cls(
            discord_token=discord_token,
            llm=LLMConfig.from_env(),
            vision=VisionConfig.from_env(),
            memory=MemoryConfig.from_env(),
            tools=ToolsConfig.from_env(),
            database_paths=DatabasePaths.from_env(),
            features=FeatureFlags.from_env(),
            universal_rules=UniversalRulesConfig.from_env(),
        )

    def __repr__(self) -> str:
        """Return a safe string representation without sensitive data."""
        return (
            f"MyriadConfig(\n"
            f"  llm={self.llm.model} @ {self.llm.base_url}\n"
            f"  vision={'enabled' if self.vision.enabled else 'disabled'}\n"
            f"  memory=short_term({self.memory.short_term_limit}), semantic({self.memory.semantic_recall_limit})\n"
            f"  features={sum([self.features.graph_memory_enabled, self.features.limbic_enabled, self.features.digital_pharmacy_enabled, self.features.cadence_degrader_enabled, self.features.metacognition_enabled, self.features.lives_enabled])} enabled\n"
            f")"
        )
