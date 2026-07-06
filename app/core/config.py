from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_dir: Path = Field(default=ROOT / "artifacts" / "v1.0.0", alias="MODEL_DIR")
    product_lookup_path: Path = Field(
        default=ROOT / "app" / "data" / "product_lookup.csv",
        alias="PRODUCT_LOOKUP_PATH",
    )
    service_version: str = Field(default="1.0.0", alias="SERVICE_VERSION")
    max_batch_size: int = Field(default=500, alias="MAX_BATCH_SIZE")
    default_top_k: int = Field(default=3, alias="DEFAULT_TOP_K")
    shadow_mode: bool = Field(default=False, alias="SHADOW_MODE")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
