import os
from dataclasses import dataclass, field

try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:
    pass


def _bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


def _list(name: str) -> list[str]:
    return [item.strip() for item in os.getenv(name, "").split(",") if item.strip()]


@dataclass(frozen=True)
class Settings:
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    facebook_access_token: str = os.getenv("FACEBOOK_ACCESS_TOKEN", "")
    facebook_page_id: str = os.getenv("FACEBOOK_PAGE_ID", "")
    competitor_page_ids: list[str] = field(default_factory=lambda: _list("COMPETITOR_PAGE_IDS"))
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    anthropic_model: str = os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-latest")
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    dry_run: bool = _bool("DRY_RUN", True)
    mock_mode: bool = _bool("MOCK_MODE", False)
    facebook_request_delay_seconds: float = float(os.getenv("FACEBOOK_REQUEST_DELAY_SECONDS", "0.2"))

    @property
    def warnings(self) -> list[str]:
        warnings: list[str] = []
        if not self.openai_api_key:
            warnings.append("OPENAI_API_KEY missing")
        if not self.anthropic_api_key:
            warnings.append("ANTHROPIC_API_KEY missing")
        if not self.facebook_access_token:
            warnings.append("FACEBOOK_ACCESS_TOKEN missing")
        if not self.facebook_page_id:
            warnings.append("FACEBOOK_PAGE_ID missing")
        return warnings

    @property
    def effective_mock_mode(self) -> bool:
        return self.mock_mode or bool(self.warnings)


settings = Settings()

OPENAI_API_KEY = settings.openai_api_key
ANTHROPIC_API_KEY = settings.anthropic_api_key
FACEBOOK_ACCESS_TOKEN = settings.facebook_access_token
FACEBOOK_PAGE_ID = settings.facebook_page_id
COMPETITOR_PAGE_IDS = settings.competitor_page_ids
DRY_RUN = settings.dry_run
MOCK_MODE = settings.effective_mock_mode
CONFIG_WARNINGS = settings.warnings
