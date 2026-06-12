"""Application configuration loaded from environment variables.

Uses pydantic-settings to validate and expose all configuration
values required by current and future subsystems (Gemini, Pinecone,
Neo4j, Supabase).  No defaults are provided for secret keys so that
missing values surface immediately during startup.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration read from ``.env`` or OS environment."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ── Gemini ───────────────────────────────────────────────
    gemini_api_key: str = ""

    # ── Pinecone ─────────────────────────────────────────────
    pinecone_api_key: str = ""
    pinecone_index_name: str = ""

    # ── Neo4j ────────────────────────────────────────────────
    neo4j_uri: str = ""
    neo4j_user: str = ""
    neo4j_password: str = ""

    # ── GitHub Models ─────────────────────────────────────────
    github_token: str = ""

    # ── MegaRAG Hyperparameters (from paper) ─────────────────
    top_k_entities: int = 60          # paper default
    top_k_relations: int = 60         # paper default
    top_m_pages: int = 6              # paper default
    refinement_subgraph_size: int = 120  # paper default

    # ── Supabase ─────────────────────────────────────────────
    supabase_url: str = ""
    supabase_key: str = ""
    max_upload_mb: int = 50

    local_image_store: str = "data/page_images"   # local folder for PNGs


settings = Settings()

