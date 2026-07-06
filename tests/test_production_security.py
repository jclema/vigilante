from fastapi.testclient import TestClient
import pytest

from app.config import Settings, settings
from app.main import app


def test_production_settings_reject_insecure_defaults():
    insecure = Settings(
        app_env="production",
        session_secret="change-me-now",
        seed_demo_data=True,
        storage_backend="memory",
        evidence_bucket_name="",
    )

    with pytest.raises(ValueError) as exc_info:
        insecure.validate_for_startup()

    message = str(exc_info.value)
    assert "SESSION_SECRET" in message
    assert "SEED_DEMO_DATA" in message
    assert "STORAGE_BACKEND" in message
    assert "EVIDENCE_BUCKET_NAME" in message


def test_production_settings_accept_hardened_runtime():
    hardened = Settings(
        app_env="production",
        session_secret="a" * 64,
        seed_demo_data=False,
        storage_backend="firestore",
        evidence_bucket_name="watchmanhub-evidence",
    )

    hardened.validate_for_startup()


def test_allowed_hosts_are_explicit():
    configured = Settings(allowed_hosts="www.watchmanhub.com,watchmanhub.com")

    assert configured.allowed_host_list == ["www.watchmanhub.com", "watchmanhub.com"]


def test_security_headers_are_added_to_http_responses():
    with TestClient(app) as client:
        response = client.get("/login")

    assert response.status_code == 200
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["referrer-policy"] == "strict-origin-when-cross-origin"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["content-security-policy"].startswith("default-src 'self'")


def test_health_endpoints_are_public_and_distinct():
    with TestClient(app) as client:
        health = client.get("/healthz")
        readiness = client.get("/readyz")

    assert health.json() == {"status": "ok"}
    assert readiness.json() == {"status": "ready", "storage_backend": "memory"}


def test_production_rejects_cross_site_form_posts():
    original_env = settings.app_env
    settings.app_env = "production"
    try:
        client = TestClient(app, base_url="https://www.watchmanhub.com")
        response = client.post(
            "/auth/login",
            data={"email": "operator@example.com", "password": "invalid"},
            headers={"Origin": "https://attacker.example"},
        )
    finally:
        settings.app_env = original_env

    assert response.status_code == 403
    assert response.json() == {"detail": "Invalid request origin"}


def test_production_accepts_same_origin_form_posts():
    original_env = settings.app_env
    settings.app_env = "production"
    try:
        client = TestClient(app, base_url="https://www.watchmanhub.com")
        response = client.post(
            "/auth/login",
            data={"email": "operator@example.com", "password": "invalid"},
            headers={"Origin": "https://www.watchmanhub.com"},
        )
    finally:
        settings.app_env = original_env

    assert response.status_code == 400
