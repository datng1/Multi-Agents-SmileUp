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
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-3.1-pro-preview")
    gemini_fallback_models: list[str] = field(default_factory=lambda: _list("GEMINI_FALLBACK_MODELS") or ["gemini-3.1-pro-preview", "gemini-3-pro", "gemini-2.5-pro", "gemini-2.5-flash"])
    gemini_image_model: str = os.getenv("GEMINI_IMAGE_MODEL", "gemini-2.5-flash-image")
    gemini_image_fallback_models: list[str] = field(default_factory=lambda: _list("GEMINI_IMAGE_FALLBACK_MODELS") or ["gemini-2.5-flash-image", "gemini-2.5-flash-image-preview", "gemini-2.0-flash-preview-image-generation"])
    competitor_page_ids: list[str] = field(default_factory=lambda: _list("COMPETITOR_PAGE_IDS"))
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-5.4-mini")
    anthropic_model: str = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5-20250929")
    cmo_jury_enabled: bool = _bool("CMO_JURY_ENABLED", True)
    agent_api_reasoning_enabled: bool = _bool("AGENT_API_REASONING_ENABLED", True)
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    dry_run: bool = _bool("DRY_RUN", True)
    mock_mode: bool = _bool("MOCK_MODE", False)
    facebook_request_delay_seconds: float = float(os.getenv("FACEBOOK_REQUEST_DELAY_SECONDS", "0.2"))
    ad_library_enabled: bool = _bool("AD_LIBRARY_ENABLED", True)
    ad_library_keywords: str = os.getenv("AD_LIBRARY_KEYWORDS", "nha khoa răng sứ răng đẹp cấy implant")
    ad_library_country: str = os.getenv("AD_LIBRARY_COUNTRY", "VN")
    ad_library_max_ads: int = int(os.getenv("AD_LIBRARY_MAX_ADS", "12"))
    ad_library_cache_ttl_hours: float = float(os.getenv("AD_LIBRARY_CACHE_TTL_HOURS", "24"))
    auth_enabled: bool = _bool("AUTH_ENABLED", False)
    admin_username: str = os.getenv("ADMIN_USERNAME", "")
    admin_password: str = os.getenv("ADMIN_PASSWORD", "")
    auth_secret: str = os.getenv("AUTH_SECRET", "")

    @property
    def warnings(self) -> list[str]:
        warnings: list[str] = []
        if not (self.gemini_api_key or self.openai_api_key or self.anthropic_api_key):
            warnings.append("No LLM API key configured")
        if not self.facebook_access_token:
            warnings.append("FACEBOOK_ACCESS_TOKEN missing")
        if not self.facebook_page_id:
            warnings.append("FACEBOOK_PAGE_ID missing")
        return warnings

    @property
    def ai_provider(self) -> str:
        if self.openai_api_key:
            return "OpenAI"
        if self.gemini_api_key:
            return "Gemini"
        if self.anthropic_api_key:
            return "Anthropic"
        return "Local fallback"

    @property
    def effective_mock_mode(self) -> bool:
        return self.mock_mode or bool(self.warnings)


settings = Settings()

OPENAI_API_KEY = settings.openai_api_key
ANTHROPIC_API_KEY = settings.anthropic_api_key
GEMINI_API_KEY = settings.gemini_api_key
GEMINI_MODEL = settings.gemini_model
GEMINI_FALLBACK_MODELS = settings.gemini_fallback_models
GEMINI_IMAGE_MODEL = settings.gemini_image_model
GEMINI_IMAGE_FALLBACK_MODELS = settings.gemini_image_fallback_models
OPENAI_MODEL = settings.openai_model
ANTHROPIC_MODEL = settings.anthropic_model
CMO_JURY_ENABLED = settings.cmo_jury_enabled
AGENT_API_REASONING_ENABLED = settings.agent_api_reasoning_enabled
AI_PROVIDER = settings.ai_provider
FACEBOOK_ACCESS_TOKEN = settings.facebook_access_token
FACEBOOK_PAGE_ID = settings.facebook_page_id
COMPETITOR_PAGE_IDS = settings.competitor_page_ids
DRY_RUN = settings.dry_run
MOCK_MODE = settings.effective_mock_mode
CONFIG_WARNINGS = settings.warnings
AD_LIBRARY_ENABLED = settings.ad_library_enabled
AD_LIBRARY_KEYWORDS = settings.ad_library_keywords
AD_LIBRARY_COUNTRY = settings.ad_library_country
AD_LIBRARY_MAX_ADS = settings.ad_library_max_ads
AD_LIBRARY_CACHE_TTL_HOURS = settings.ad_library_cache_ttl_hours
AUTH_ENABLED = settings.auth_enabled
ADMIN_USERNAME = settings.admin_username
ADMIN_PASSWORD = settings.admin_password
AUTH_SECRET = settings.auth_secret
