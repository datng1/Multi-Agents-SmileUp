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


def _split_multi(raw: str) -> list[str]:
    return [item.strip() for item in re.split(r"[\n,]+", raw) if item.strip()]


def _multi_list(name: str, default: str = "") -> list[str]:
    return _split_multi(os.getenv(name, default))


def _merged_multi_list(name: str, default: str = "") -> list[str]:
    merged: list[str] = []
    for item in _split_multi(default) + _multi_list(name, ""):
        if item and item not in merged:
            merged.append(item)
    return merged


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
    facebook_access_token: str = os.getenv("FACEBOOK_ACCESS_TOKEN", "")
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-3.1-pro-preview")
    gemini_fallback_models: list[str] = field(default_factory=lambda: _list("GEMINI_FALLBACK_MODELS") or ["gemini-3.1-pro-preview"])
    competitor_page_ids: list[str] = field(default_factory=lambda: _list("COMPETITOR_PAGE_IDS"))
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-5.6-sol")
    openai_reasoning_effort: str = os.getenv("OPENAI_REASONING_EFFORT", "high")
    openai_timeout_seconds: int = max(30, int(os.getenv("OPENAI_TIMEOUT_SECONDS", "180")))
    agent_api_reasoning_enabled: bool = _bool("AGENT_API_REASONING_ENABLED", True)
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    mock_mode: bool = _bool("MOCK_MODE", False)
    facebook_request_delay_seconds: float = float(os.getenv("FACEBOOK_REQUEST_DELAY_SECONDS", "0.2"))
    ad_library_enabled: bool = _bool("AD_LIBRARY_ENABLED", True)
    ad_library_keywords: str = os.getenv("AD_LIBRARY_KEYWORDS", "nha khoa răng sứ răng đẹp cấy implant")
    ad_library_country: str = os.getenv("AD_LIBRARY_COUNTRY", "VN")
    ad_library_max_ads: int = int(os.getenv("AD_LIBRARY_MAX_ADS", "100"))
    ad_library_cache_ttl_hours: float = float(os.getenv("AD_LIBRARY_CACHE_TTL_HOURS", "24"))
    ad_library_competitor_urls: list[str] = field(default_factory=lambda: _merged_multi_list("AD_LIBRARY_COMPETITOR_URLS", DEFAULT_COMPETITOR_AD_LIBRARY_URLS))
    ad_library_competitor_ratio: float = float(os.getenv("AD_LIBRARY_COMPETITOR_RATIO", "0.8"))
    smileup_average_case_value: float = float(os.getenv("SMILEUP_AVERAGE_CASE_VALUE", "0"))
    smileup_gross_margin_rate: float = float(os.getenv("SMILEUP_GROSS_MARGIN_RATE", "0"))
    smileup_qualified_lead_to_booking_rate: float = float(os.getenv("SMILEUP_QUALIFIED_LEAD_TO_BOOKING_RATE", "0"))
    smileup_booking_show_rate: float = float(os.getenv("SMILEUP_BOOKING_SHOW_RATE", "0"))
    smileup_consultation_close_rate: float = float(os.getenv("SMILEUP_CONSULTATION_CLOSE_RATE", "0"))
    smileup_max_acquisition_share: float = float(os.getenv("SMILEUP_MAX_ACQUISITION_SHARE", "0"))
    auth_enabled: bool = _bool("AUTH_ENABLED", False)
    admin_username: str = os.getenv("ADMIN_USERNAME", "")
    admin_password: str = os.getenv("ADMIN_PASSWORD", "")
    auth_users: dict[str, str] = field(default_factory=_auth_users)
    auth_admin_usernames: list[str] = field(default_factory=lambda: _list("AUTH_ADMIN_USERNAMES") or ([os.getenv("ADMIN_USERNAME", "").strip()] if os.getenv("ADMIN_USERNAME", "").strip() else []))
    auth_secret: str = os.getenv("AUTH_SECRET", "")

    @property
    def warnings(self) -> list[str]:
        warnings: list[str] = []
        if not self.openai_api_key:
            warnings.append("OPENAI_API_KEY is required for CMO and complex tasks")
        if not self.gemini_api_key:
            warnings.append("GEMINI_API_KEY is required for easy analysis tasks")
        return warnings

    @property
    def ai_provider(self) -> str:
        if self.openai_api_key:
            return "OpenAI"
        if self.gemini_api_key:
            return "Gemini"
        return "Local fallback"

    @property
    def effective_mock_mode(self) -> bool:
        return self.mock_mode


settings = Settings()

OPENAI_API_KEY = settings.openai_api_key
GEMINI_API_KEY = settings.gemini_api_key
GEMINI_MODEL = settings.gemini_model
GEMINI_FALLBACK_MODELS = settings.gemini_fallback_models
OPENAI_MODEL = settings.openai_model
OPENAI_REASONING_EFFORT = settings.openai_reasoning_effort
OPENAI_TIMEOUT_SECONDS = settings.openai_timeout_seconds
AGENT_API_REASONING_ENABLED = settings.agent_api_reasoning_enabled
AI_PROVIDER = settings.ai_provider
FACEBOOK_ACCESS_TOKEN = settings.facebook_access_token
COMPETITOR_PAGE_IDS = settings.competitor_page_ids
MOCK_MODE = settings.effective_mock_mode
CONFIG_WARNINGS = settings.warnings
AD_LIBRARY_ENABLED = settings.ad_library_enabled
AD_LIBRARY_KEYWORDS = settings.ad_library_keywords
AD_LIBRARY_COUNTRY = settings.ad_library_country
AD_LIBRARY_MAX_ADS = settings.ad_library_max_ads
AD_LIBRARY_CACHE_TTL_HOURS = settings.ad_library_cache_ttl_hours
AD_LIBRARY_COMPETITOR_URLS = settings.ad_library_competitor_urls
AD_LIBRARY_COMPETITOR_RATIO = settings.ad_library_competitor_ratio
SMILEUP_BUSINESS_ECONOMICS = {
    "average_case_value": settings.smileup_average_case_value,
    "gross_margin_rate": settings.smileup_gross_margin_rate,
    "qualified_lead_to_booking_rate": settings.smileup_qualified_lead_to_booking_rate,
    "booking_show_rate": settings.smileup_booking_show_rate,
    "consultation_close_rate": settings.smileup_consultation_close_rate,
    "max_acquisition_share_of_gross_profit": settings.smileup_max_acquisition_share,
}
AUTH_ENABLED = settings.auth_enabled
ADMIN_USERNAME = settings.admin_username
ADMIN_PASSWORD = settings.admin_password
AUTH_USERS = settings.auth_users
AUTH_ADMIN_USERNAMES = settings.auth_admin_usernames
AUTH_SECRET = settings.auth_secret
