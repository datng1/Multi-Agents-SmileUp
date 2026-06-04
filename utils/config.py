import os
import re
import json
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


def _multi_list(name: str, default: str = "") -> list[str]:
    raw = os.getenv(name, default)
    return [item.strip() for item in re.split(r"[\n,]+", raw) if item.strip()]


def _json_object(name: str) -> dict:
    raw = os.getenv(name, "").strip()
    if not raw:
        return {}
    try:
        value = json.loads(raw)
    except Exception:
        return {}
    return value if isinstance(value, dict) else {}


def _auth_users() -> dict[str, str]:
    users = {str(username).strip(): str(password) for username, password in _json_object("AUTH_USERS_JSON").items()}
    admin_username = os.getenv("ADMIN_USERNAME", "").strip()
    admin_password = os.getenv("ADMIN_PASSWORD", "")
    if admin_username and admin_password and admin_username not in users:
        users[admin_username] = admin_password
    return {username: password for username, password in users.items() if username and password}


def _auth_page_permissions() -> dict[str, list[str]]:
    permissions: dict[str, list[str]] = {
        "cuongsmileup": [
            "954145057772731",
            "840668499122232",
        ],
        "vitsmileup": [
            "111884500869678",
            "1775662159384248",
        ]
    }
    raw_permissions = _json_object("AUTH_PAGE_PERMISSIONS_JSON")
    for username, page_ids in raw_permissions.items():
        if isinstance(page_ids, list):
            cleaned = [str(page_id).strip() for page_id in page_ids if str(page_id).strip()]
        else:
            cleaned = [item.strip() for item in str(page_ids).split(",") if item.strip()]
        safe_username = str(username).strip()
        if safe_username:
            permissions[safe_username] = cleaned
    return permissions


def _facebook_publish_pages() -> list[dict[str, str]]:
    tokens = _json_object("FACEBOOK_PAGE_TOKENS_JSON")
    names = _json_object("FACEBOOK_PAGE_NAMES_JSON")
    pages: list[dict[str, str]] = []
    for page_id, token in tokens.items():
        safe_page_id = str(page_id).strip()
        safe_token = str(token).strip()
        if not safe_page_id or not safe_token:
            continue
        pages.append(
            {
                "page_id": safe_page_id,
                "name": str(names.get(safe_page_id) or f"Page {safe_page_id}").strip(),
                "access_token": safe_token,
            }
        )

    legacy_page_id = os.getenv("FACEBOOK_PAGE_ID", "").strip()
    legacy_token = os.getenv("FACEBOOK_ACCESS_TOKEN", "").strip()
    if not pages and legacy_page_id and legacy_token:
        pages.append(
            {
                "page_id": legacy_page_id,
                "name": str(names.get(legacy_page_id) or f"Page {legacy_page_id}").strip(),
                "access_token": legacy_token,
            }
        )
    return pages


DEFAULT_COMPETITOR_AD_LIBRARY_URLS = "\n".join(
    [
        "https://www.facebook.com/ads/library/?active_status=active&ad_type=all&country=ALL&is_targeted_country=false&media_type=all&search_type=page&sort_data[mode]=total_impressions&sort_data[direction]=desc&source=page-transparency-widget&view_all_page_id=110734571784682",
        "https://www.facebook.com/ads/library/?active_status=active&ad_type=all&country=ALL&is_targeted_country=false&media_type=all&search_type=page&sort_data[mode]=total_impressions&sort_data[direction]=desc&source=page-transparency-widget&view_all_page_id=787928884397319",
        "https://www.facebook.com/ads/library/?active_status=active&ad_type=all&country=ALL&is_targeted_country=false&media_type=all&search_type=page&sort_data[mode]=total_impressions&sort_data[direction]=desc&source=page-transparency-widget&view_all_page_id=112564051627698",
        "https://www.facebook.com/ads/library/?active_status=active&ad_type=all&country=ALL&is_targeted_country=false&media_type=all&search_type=page&sort_data[mode]=total_impressions&sort_data[direction]=desc&source=page-transparency-widget&view_all_page_id=523667784157191",
        "https://www.facebook.com/ads/library/?active_status=active&ad_type=all&country=ALL&is_targeted_country=false&media_type=all&search_type=page&sort_data[mode]=total_impressions&sort_data[direction]=desc&source=page-transparency-widget&view_all_page_id=746526788551014",
        "https://www.facebook.com/ads/library/?active_status=active&ad_type=all&country=ALL&is_targeted_country=false&media_type=all&search_type=page&sort_data[mode]=total_impressions&sort_data[direction]=desc&source=page-transparency-widget&view_all_page_id=112901911595862",
        "https://www.facebook.com/ads/library/?active_status=active&ad_type=all&country=ALL&is_targeted_country=false&media_type=all&search_type=page&sort_data[mode]=total_impressions&sort_data[direction]=desc&source=page-transparency-widget&view_all_page_id=183094894877720",
        "https://www.facebook.com/ads/library/?active_status=active&ad_type=all&country=ALL&is_targeted_country=false&media_type=all&search_type=page&sort_data[mode]=total_impressions&sort_data[direction]=desc&source=page-transparency-widget&view_all_page_id=141815746680256",
        "https://www.facebook.com/ads/library/?active_status=active&ad_type=all&country=ALL&is_targeted_country=false&media_type=all&search_type=page&sort_data[mode]=total_impressions&sort_data[direction]=desc&source=page-transparency-widget&view_all_page_id=100304372631888",
    ]
)


@dataclass(frozen=True)
class Settings:
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    facebook_access_token: str = os.getenv("FACEBOOK_ACCESS_TOKEN", "")
    facebook_page_id: str = os.getenv("FACEBOOK_PAGE_ID", "")
    facebook_publish_pages: list[dict[str, str]] = field(default_factory=_facebook_publish_pages)
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-3.1-pro-preview")
    gemini_fallback_models: list[str] = field(default_factory=lambda: _list("GEMINI_FALLBACK_MODELS") or ["gemini-3.1-pro-preview", "gemini-3-pro", "gemini-2.5-pro", "gemini-2.5-flash"])
    competitor_page_ids: list[str] = field(default_factory=lambda: _list("COMPETITOR_PAGE_IDS"))
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-5.5")
    openai_image_model: str = "gpt-image-2"
    openai_image_fallback_models: list[str] = field(default_factory=list)
    openai_image_max_creatives: int = int(os.getenv("OPENAI_IMAGE_MAX_CREATIVES", "0"))
    openai_image_photo_creatives: int = int(os.getenv("OPENAI_IMAGE_PHOTO_CREATIVES", "6"))
    openai_image_page_care_creatives: int = int(os.getenv("OPENAI_IMAGE_PAGE_CARE_CREATIVES", "3"))
    openai_image_max_model_attempts: int = 1
    openai_image_request_timeout_seconds: int = int(os.getenv("OPENAI_IMAGE_REQUEST_TIMEOUT_SECONDS", "180"))
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
    ad_library_max_ads: int = int(os.getenv("AD_LIBRARY_MAX_ADS", "15"))
    ad_library_cache_ttl_hours: float = float(os.getenv("AD_LIBRARY_CACHE_TTL_HOURS", "24"))
    ad_library_competitor_urls: list[str] = field(default_factory=lambda: _multi_list("AD_LIBRARY_COMPETITOR_URLS", DEFAULT_COMPETITOR_AD_LIBRARY_URLS))
    ad_library_competitor_ratio: float = float(os.getenv("AD_LIBRARY_COMPETITOR_RATIO", "0.8"))
    auth_enabled: bool = _bool("AUTH_ENABLED", False)
    admin_username: str = os.getenv("ADMIN_USERNAME", "")
    admin_password: str = os.getenv("ADMIN_PASSWORD", "")
    auth_users: dict[str, str] = field(default_factory=_auth_users)
    auth_admin_usernames: list[str] = field(default_factory=lambda: _list("AUTH_ADMIN_USERNAMES") or ([os.getenv("ADMIN_USERNAME", "").strip()] if os.getenv("ADMIN_USERNAME", "").strip() else []))
    auth_page_permissions: dict[str, list[str]] = field(default_factory=_auth_page_permissions)
    auth_secret: str = os.getenv("AUTH_SECRET", "")

    @property
    def warnings(self) -> list[str]:
        warnings: list[str] = []
        if not (self.gemini_api_key or self.openai_api_key or self.anthropic_api_key):
            warnings.append("No LLM API key configured")
        if not self.facebook_publish_pages:
            warnings.append("FACEBOOK publish pages missing")
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
OPENAI_MODEL = settings.openai_model
OPENAI_IMAGE_MODEL = settings.openai_image_model
OPENAI_IMAGE_FALLBACK_MODELS = settings.openai_image_fallback_models
OPENAI_IMAGE_MAX_CREATIVES = max(0, settings.openai_image_max_creatives)
OPENAI_IMAGE_PHOTO_CREATIVES = max(0, settings.openai_image_photo_creatives)
OPENAI_IMAGE_PAGE_CARE_CREATIVES = max(0, settings.openai_image_page_care_creatives)
OPENAI_IMAGE_MAX_MODEL_ATTEMPTS = max(1, settings.openai_image_max_model_attempts)
OPENAI_IMAGE_REQUEST_TIMEOUT_SECONDS = max(60, settings.openai_image_request_timeout_seconds)
ANTHROPIC_MODEL = settings.anthropic_model
CMO_JURY_ENABLED = settings.cmo_jury_enabled
AGENT_API_REASONING_ENABLED = settings.agent_api_reasoning_enabled
AI_PROVIDER = settings.ai_provider
FACEBOOK_ACCESS_TOKEN = settings.facebook_access_token
FACEBOOK_PAGE_ID = settings.facebook_page_id
FACEBOOK_PUBLISH_PAGES = settings.facebook_publish_pages
COMPETITOR_PAGE_IDS = settings.competitor_page_ids
DRY_RUN = settings.dry_run
MOCK_MODE = settings.effective_mock_mode
CONFIG_WARNINGS = settings.warnings
AD_LIBRARY_ENABLED = settings.ad_library_enabled
AD_LIBRARY_KEYWORDS = settings.ad_library_keywords
AD_LIBRARY_COUNTRY = settings.ad_library_country
AD_LIBRARY_MAX_ADS = settings.ad_library_max_ads
AD_LIBRARY_CACHE_TTL_HOURS = settings.ad_library_cache_ttl_hours
AD_LIBRARY_COMPETITOR_URLS = settings.ad_library_competitor_urls
AD_LIBRARY_COMPETITOR_RATIO = settings.ad_library_competitor_ratio
AUTH_ENABLED = settings.auth_enabled
ADMIN_USERNAME = settings.admin_username
ADMIN_PASSWORD = settings.admin_password
AUTH_USERS = settings.auth_users
AUTH_ADMIN_USERNAMES = settings.auth_admin_usernames
AUTH_PAGE_PERMISSIONS = settings.auth_page_permissions
AUTH_SECRET = settings.auth_secret
