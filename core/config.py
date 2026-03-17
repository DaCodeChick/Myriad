"""
Configuration Management for Project Myriad

Centralizes all environment variable parsing and configuration loading.
Provides type-safe configuration objects with validation and defaults.
"""

import os
from dataclasses import dataclass, field
from typing import Optional, Set, List


@dataclass
class DiscordConfig:
    """Discord-specific configuration."""

    token: str
    whitelisted_bot_ids: Set[int] = field(default_factory=set)

    @classmethod
    def from_env(cls) -> "DiscordConfig":
        """Load Discord configuration from environment variables."""
        token = os.getenv("DISCORD_TOKEN")
        if not token:
            raise ValueError("DISCORD_TOKEN not found in environment")

        # Parse comma-separated bot IDs into a set of integers
        whitelisted_bot_ids: Set[int] = set()
        bot_ids_str = os.getenv("WHITELISTED_BOT_IDS", "")
        if bot_ids_str.strip():
            for id_str in bot_ids_str.split(","):
                id_str = id_str.strip()
                if id_str:
                    try:
                        whitelisted_bot_ids.add(int(id_str))
                    except ValueError:
                        print(f"⚠ Invalid bot ID in WHITELISTED_BOT_IDS: {id_str}")

        return cls(
            token=token,
            whitelisted_bot_ids=whitelisted_bot_ids,
        )


@dataclass
class LLMConfig:
    """LLM API configuration."""

    provider: str = "local"  # "local" or "gemini"
    api_key: str = ""
    base_url: str = "https://api.openai.com/v1"
    model: str = "gpt-4"
    gemini_api_key: Optional[str] = None
    gemini_model: str = "gemini-1.5-pro"

    @classmethod
    def from_env(cls) -> "LLMConfig":
        """Load LLM configuration from environment variables."""
        provider = os.getenv("LLM_PROVIDER", "local").lower()

        # For backward compatibility, LLM_API_KEY is still required for local provider
        api_key = os.getenv("LLM_API_KEY", "")

        # Gemini-specific configuration
        gemini_api_key = os.getenv("GEMINI_API_KEY")
        gemini_model = os.getenv("GEMINI_MODEL", "gemini-1.5-pro")

        # Validate provider-specific requirements
        if provider == "local" and not api_key:
            raise ValueError(
                "LLM_API_KEY not found in environment (required for local provider)"
            )
        elif provider == "gemini" and not gemini_api_key:
            raise ValueError(
                "GEMINI_API_KEY not found in environment (required for gemini provider)"
            )

        return cls(
            provider=provider,
            api_key=api_key,
            base_url=os.getenv("LLM_BASE_URL", "https://api.openai.com/v1"),
            model=os.getenv("LLM_MODEL", "gpt-4"),
            gemini_api_key=gemini_api_key,
            gemini_model=gemini_model,
        )


@dataclass
class VisionConfig:
    """Vision API configuration."""

    api_key: str = "not-needed"
    base_url: Optional[str] = None
    model: str = "vision-model"
    enabled: bool = True  # Master toggle for vision processing

    @classmethod
    def from_env(cls) -> "VisionConfig":
        """Load vision configuration from environment variables."""
        return cls(
            api_key=os.getenv("VISION_API_KEY", "not-needed"),
            base_url=os.getenv("VISION_BASE_URL"),
            model=os.getenv("VISION_MODEL", "vision-model"),
            enabled=os.getenv("VISION_ENABLED", "true").lower() == "true",
        )

    @property
    def is_available(self) -> bool:
        """Check if vision is both enabled and configured (has base_url)."""
        return self.enabled and self.base_url is not None


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
    """Database file paths configuration.

    RDSSC Phase 1: Consolidate databases by feature.
    - roleplay_db_path: All roleplay feature tables (limbic, metacognition, lives, etc.)
    - memory_db_path: Memory system tables (memories, user_preferences)
    - graph_db_path: Knowledge graph tables (entities, relationships)
    - visual_db_path: Visual memory tables (visual_profiles)
    - chroma_db_path: Vector embeddings (ChromaDB)
    """

    roleplay_db_path: str = "data/roleplay.db"
    memory_db_path: str = "data/memory.db"
    graph_db_path: str = "data/knowledge_graph.db"
    visual_db_path: str = "data/visual_memory.db"
    chroma_db_path: str = "data/chroma_db"

    # Deprecated - for backward compatibility during migration
    main_db_path: str = "data/memory.db"

    @classmethod
    def from_env(cls) -> "DatabasePaths":
        """Load database paths from environment variables."""
        return cls(
            roleplay_db_path=os.getenv("ROLEPLAY_DB_PATH", "data/roleplay.db"),
            memory_db_path=os.getenv("MEMORY_DB_PATH", "data/memory.db"),
            graph_db_path=os.getenv("GRAPH_DB_PATH", "data/knowledge_graph.db"),
            visual_db_path=os.getenv("VISUAL_DB_PATH", "data/visual_memory.db"),
            chroma_db_path=os.getenv("CHROMA_DB_PATH", "data/chroma_db"),
            main_db_path=os.getenv(
                "MAIN_DB_PATH", os.getenv("MEMORY_DB_PATH", "data/memory.db")
            ),
        )


@dataclass
class UniversalRulesConfig:
    """Universal behavioral rules applied to all personas."""

    rules: Optional[List[str]] = None

    @classmethod
    def from_env(cls) -> "UniversalRulesConfig":
        """Load universal rules from environment variables.

        Rules are pipe-separated in the UNIVERSAL_RULES env var.
        Returns None if not set (allows AgentCore to use defaults).
        """
        rules_str = os.getenv("UNIVERSAL_RULES", "").strip()
        if not rules_str:
            return cls(rules=None)

        # Split by pipe and strip whitespace from each rule
        rules = [rule.strip() for rule in rules_str.split("|") if rule.strip()]
        return cls(rules=rules if rules else None)


@dataclass
class LoggingConfig:
    """Logging configuration for console and file output."""

    brain_console_enabled: bool = False
    eyes_console_enabled: bool = False
    brain_file_enabled: bool = False
    eyes_file_enabled: bool = False
    log_dir: str = "logs"
    init_log_level: str = "INFO"  # DEBUG, INFO, WARNING, ERROR

    @classmethod
    def from_env(cls) -> "LoggingConfig":
        """Load logging configuration from environment variables."""
        return cls(
            brain_console_enabled=os.getenv(
                "ENABLE_BRAIN_CONSOLE_LOGGING", "false"
            ).lower()
            == "true",
            eyes_console_enabled=os.getenv(
                "ENABLE_EYES_CONSOLE_LOGGING", "false"
            ).lower()
            == "true",
            brain_file_enabled=os.getenv("ENABLE_BRAIN_FILE_LOGGING", "false").lower()
            == "true",
            eyes_file_enabled=os.getenv("ENABLE_EYES_FILE_LOGGING", "false").lower()
            == "true",
            log_dir=os.getenv("LOG_DIR", "logs"),
            init_log_level=os.getenv("INIT_LOG_LEVEL", "INFO").upper(),
        )


@dataclass
class MyriadConfig:
    """Complete Project Myriad configuration.

    Aggregates all configuration sections for easy access.
    """

    discord: DiscordConfig
    llm: LLMConfig
    vision: VisionConfig
    memory: MemoryConfig
    tools: ToolsConfig
    database_paths: DatabasePaths
    universal_rules: UniversalRulesConfig
    logging: LoggingConfig

    @property
    def discord_token(self) -> str:
        """Backward compatibility: access token via discord.token."""
        return self.discord.token

    @classmethod
    def from_env(cls) -> "MyriadConfig":
        """Load complete configuration from environment variables.

        Raises:
            ValueError: If required configuration is missing
        """
        return cls(
            discord=DiscordConfig.from_env(),
            llm=LLMConfig.from_env(),
            vision=VisionConfig.from_env(),
            memory=MemoryConfig.from_env(),
            tools=ToolsConfig.from_env(),
            database_paths=DatabasePaths.from_env(),
            universal_rules=UniversalRulesConfig.from_env(),
            logging=LoggingConfig.from_env(),
        )

    def __repr__(self) -> str:
        """Return a safe string representation without sensitive data."""
        whitelist_count = len(self.discord.whitelisted_bot_ids)
        return (
            f"MyriadConfig(\n"
            f"  llm={self.llm.model} @ {self.llm.base_url}\n"
            f"  vision={'enabled' if self.vision.is_available else 'disabled'}\n"
            f"  memory=short_term({self.memory.short_term_limit}), semantic({self.memory.semantic_recall_limit})\n"
            f"  bot_whitelist={whitelist_count} bot(s)\n"
            f")"
        )
