from __future__ import annotations

import os
from dataclasses import dataclass


def _to_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


@dataclass(slots=True)
class Settings:
    app_name: str = os.getenv("APP_NAME", "Vigilante")
    app_env: str = os.getenv("APP_ENV", "development")
    dashboard_username: str = os.getenv("DASHBOARD_USERNAME", "operator")
    dashboard_password: str = os.getenv("DASHBOARD_PASSWORD", "change-me")
    super_admin_email: str = os.getenv("SUPER_ADMIN_EMAIL", "joework.co@gmail.com")
    session_secret: str = os.getenv("SESSION_SECRET", "change-me-now")
    google_maps_api_key: str = os.getenv("GOOGLE_MAPS_API_KEY", "")
    google_oauth_client_id: str = os.getenv("GOOGLE_OAUTH_CLIENT_ID", "")
    google_oauth_client_secret: str = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET", "")
    google_oauth_redirect_uri: str = os.getenv("GOOGLE_OAUTH_REDIRECT_URI", "")
    google_gbp_webhook_secret: str = os.getenv("GOOGLE_GBP_WEBHOOK_SECRET", "")
    google_gbp_account_id: str = os.getenv("GOOGLE_GBP_ACCOUNT_ID", "")
    google_gbp_access_token: str = os.getenv("GOOGLE_GBP_ACCESS_TOKEN", "")
    alert_webhook_url: str = os.getenv("ALERT_WEBHOOK_URL", "")
    smtp_host: str = os.getenv("SMTP_HOST", "")
    smtp_port: int = int(os.getenv("SMTP_PORT", "587"))
    smtp_username: str = os.getenv("SMTP_USERNAME", "")
    smtp_password: str = os.getenv("SMTP_PASSWORD", "")
    smtp_from_email: str = os.getenv("SMTP_FROM_EMAIL", "")
    smtp_starttls: bool = _to_bool(os.getenv("SMTP_STARTTLS"), True)
    google_cloud_project: str = os.getenv("GOOGLE_CLOUD_PROJECT", "vigilante-pilot")
    google_cloud_region: str = os.getenv("GOOGLE_CLOUD_REGION", "us-central1")
    evidence_bucket_name: str = os.getenv("EVIDENCE_BUCKET_NAME", "")
    evidence_local_dir: str = os.getenv("EVIDENCE_LOCAL_DIR", "/tmp/vigilante-evidence")
    storage_backend: str = os.getenv("STORAGE_BACKEND", "memory")
    seed_demo_data: bool = _to_bool(os.getenv("SEED_DEMO_DATA"), True)
    enable_gemini: bool = _to_bool(os.getenv("ENABLE_GEMINI"), False)
    enable_google_vision_ocr: bool = _to_bool(os.getenv("ENABLE_GOOGLE_VISION_OCR"), False)
    enable_browser_enforcement: bool = _to_bool(os.getenv("ENABLE_BROWSER_ENFORCEMENT"), False)
    enable_stagehand_fallback: bool = _to_bool(os.getenv("ENABLE_STAGEHAND_FALLBACK"), False)
    browser_auto_submit_cooldown_hours: int = int(os.getenv("BROWSER_AUTO_SUBMIT_COOLDOWN_HOURS", "24"))


settings = Settings()
