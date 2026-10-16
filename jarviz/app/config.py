"""Configuración desde variables de entorno (sin secretos en el código)."""
import os
from dataclasses import dataclass, field


def _int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    # Se leen al crear la instancia (no al importar), para respetar cambios de entorno.
    db_path: str = field(default_factory=lambda: os.environ.get("JARVIZ_DB_PATH", "data/jarviz.db"))
    anthropic_key_present: bool = field(default_factory=lambda: bool(os.environ.get("ANTHROPIC_API_KEY")))
    model: str = field(default_factory=lambda: os.environ.get("JARVIZ_MODEL", "claude-opus-5-5"))
    max_autonomy: int = field(default_factory=lambda: max(1, min(5, _int("JARVIZ_MAX_AUTONOMY", 3))))
    session_hours: int = field(default_factory=lambda: _int("JARVIZ_SESSION_HOURS", 12))
    conversation_retention_days: int = field(default_factory=lambda: _int("JARVIZ_CONVERSATION_RETENTION_DAYS", 30))
    allowed_origins: tuple = field(default_factory=lambda: tuple(o for o in os.environ.get("JARVIZ_ALLOWED_ORIGINS", "").split(",") if o))


def get_settings() -> Settings:
    return Settings()
