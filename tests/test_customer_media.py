from pathlib import Path
from urllib.error import HTTPError

from fastapi.testclient import TestClient

from app.agents.forensic import ForensicAgent
from app.agents.scout import ScoutAgent
from app.main import app
from app.models import ConnectionStatus, EvidenceArtifact, GbpConnection
from app.services.auth import encrypt_secret
from app.services.gbp_media import (
    CustomerMediaItem,
    GbpCustomerMediaClient,
    GbpCustomerMediaIngestService,
    GbpOrganizationConnectionResolver,
    GbpResolvedCredentials,
)
from app.services.demo_data import suspicious_assets
from app.store import InMemoryRepository, repository as app_repository


class FakeMediaClient:
    def __init__(self, items):
        self.items = items

    def list_customer_media(self, location_name: str, page_size: int = 20):
        return self.items[:page_size]

    def normalize_location_name(self, value: str) -> str:
        if value.startswith("accounts/"):
            return value
        return f"accounts/999/{value}"


class FakeEvidenceService:
    def __init__(self):
        self.calls = 0

    def capture_image(self, *, case_id: str, artifact_id: str, source_url: str | None):
        self.calls += 1
        return type(
            "Captured",
            (),
            {
                "internal_url": "/api/evidence/image?path=file%3A%2F%2F%2Ftmp%2Fvigilante-evidence%2Ffake.jpg",
                "storage_path": "file:///tmp/vigilante-evidence/fake.jpg",
                "checksum": "abc123",
                "content_type": "image/jpeg",
                "size_bytes": 12,
                "download_status": "captured",
                "bytes_payload": b"fake-image",
            },
        )()


def _build_service(repo: InMemoryRepository) -> GbpCustomerMediaIngestService:
    items = [
        CustomerMediaItem(
            name="accounts/999/locations/1001/media/customers/1",
            location_name="accounts/999/locations/1001",
            image_url="https://example.com/fake.jpg",
            thumbnail_url="https://example.com/fake-thumb.jpg",
            source_page_url="https://maps.google.com/?cid=123",
            description="Nuevo numero del concesionario",
            create_time="2026-03-19T18:30:00Z",
            raw_payload={"uploader": "local-guide-12", "ocr_text": "Yamaha Bello 301 999 8888"},
        )
    ]
    return GbpCustomerMediaIngestService(
        repository=repo,
        scout_agent=ScoutAgent(repo, ForensicAgent()),
        media_client=FakeMediaClient(items),
        evidence_service=FakeEvidenceService(),
    )


def test_customer_media_sync_creates_case_and_visual_evidence():
    repo = InMemoryRepository()
    repo.seed()

    result = _build_service(repo).sync_profile("profile-bello", limit=5)

    assert result["processed"] == 1
    assert result["cases_created"] == 1
    case = repo.list_cases()[0]
    evidence = repo.list_evidence_for_case(case.id)
    assert case.source_reference_id == "accounts/999/locations/1001/media/customers/1"
    assert len(evidence) == 1
    assert evidence[0].content["internal_image_url"].startswith("/api/evidence/image?")
    assert evidence[0].content["detected_phone_numbers"] == ["3019998888"]
    assert evidence[0].content["media_origin"] == "gbp_customer_media"
    assert case.risk_score >= 70


def test_customer_media_sync_dedupes_same_photo():
    repo = InMemoryRepository()
    repo.seed()
    service = _build_service(repo)

    service.sync_profile("profile-bello", limit=5)
    service.sync_profile("profile-bello", limit=5)

    cases = repo.list_cases()
    assert len(cases) == 1
    assert len(repo.list_evidence_for_case(cases[0].id)) == 1


def test_customer_media_service_builds_client_from_org_connection():
    repo = InMemoryRepository()
    repo.seed()
    connection = GbpConnection(
        id="gbp-1",
        organization_id="org-dealer-bello",
        provider_account_id="google-subject-1",
        provider_email="dealer@example.com",
        encrypted_refresh_token=encrypt_secret("refresh-token"),
        selected_profile_ids=["profile-bello"],
        status=ConnectionStatus.CONNECTED,
    )
    repo.save_gbp_connection(connection)

    class FakeResolver(GbpOrganizationConnectionResolver):
        def credentials_for_profile(self, profile):
            assert profile.id == "profile-bello"
            return GbpResolvedCredentials(
                access_token="org-access-token",
                account_names=["accounts/777"],
                connection=connection,
            )

    service = GbpCustomerMediaIngestService(
        repository=repo,
        scout_agent=ScoutAgent(repo, ForensicAgent()),
        media_client=None,
        evidence_service=FakeEvidenceService(),
        credentials_resolver=FakeResolver(repo),
    )

    client = service._client_for_profile(repo.profiles["profile-bello"])

    assert isinstance(client, GbpCustomerMediaClient)
    assert client.access_token == "org-access-token"
    assert client.account_names == ["accounts/777"]


def test_sync_push_payload_matches_profile_by_location_suffix():
    repo = InMemoryRepository()
    repo.seed()
    service = _build_service(repo)
    captured = {}

    def fake_sync_profile(profile_id: str, limit: int = 20, ingestion_mode: str = "push"):
        captured["profile_id"] = profile_id
        captured["limit"] = limit
        captured["ingestion_mode"] = ingestion_mode
        return {"profile_id": profile_id}

    service.sync_profile = fake_sync_profile  # type: ignore[method-assign]

    result = service.sync_push_payload({"location_name": "accounts/555/locations/1001"}, limit=7)

    assert result == {"profile_id": "profile-bello"}
    assert captured == {"profile_id": "profile-bello", "limit": 7, "ingestion_mode": "push"}


def test_discover_locations_updates_connection_cache():
    repo = InMemoryRepository()
    repo.seed()
    connection = GbpConnection(
        id="gbp-1",
        organization_id="org-dealer-bello",
        provider_account_id="google-subject-1",
        provider_email="dealer@example.com",
        encrypted_refresh_token=encrypt_secret("refresh-token"),
        selected_profile_ids=["profile-bello"],
        status=ConnectionStatus.CONNECTED,
    )
    repo.save_gbp_connection(connection)

    class FakeResolver(GbpOrganizationConnectionResolver):
        def _refresh_access_token(self, refresh_token: str) -> str:
            assert refresh_token == "refresh-token"
            return "org-access-token"

        def _list_account_names(self, access_token: str) -> list[str]:
            assert access_token == "org-access-token"
            return ["accounts/777"]

        def _list_locations_for_account(self, access_token: str, account_name: str) -> list[dict[str, str]]:
            assert account_name == "accounts/777"
            return [
                {
                    "name": "locations/555",
                    "title": "Motoblu Bello",
                    "account_name": account_name,
                    "place_id": "place-1",
                    "store_code": "",
                }
            ]

    resolver = FakeResolver(repo)
    locations = resolver.discover_locations(organization_id="org-dealer-bello", connection_id="gbp-1")

    assert locations[0]["name"] == "locations/555"
    updated = repo.get_gbp_connection("gbp-1")
    assert updated is not None
    assert updated.gbp_account_name == "accounts/777"
    assert updated.available_locations[0]["title"] == "Motoblu Bello"
    assert updated.last_locations_sync_at is not None


def test_backfill_customer_media_returns_clear_403_when_google_forbids_access():
    class ForbiddenService:
        def sync_profiles(self, profile_ids=None, limit=20):
            raise HTTPError(
                url="https://mybusiness.googleapis.com/v4/accounts/me/locations/123/media/customers",
                code=403,
                msg="Forbidden",
                hdrs=None,
                fp=None,
            )

    from app import main as main_module

    original_factory = main_module.customer_media_ingest_service
    main_module.customer_media_ingest_service = lambda: ForbiddenService()
    try:
        client = TestClient(app)
        app_repository.seed()
        client.post(
            "/auth/login",
            data={"email": "operator@vigilante.local", "password": "change-me"},
        )
        response = client.post(
            "/api/gbp/customer-media/backfill",
            json={"profile_ids": ["profile-bello"], "limit": 5},
        )
    finally:
        main_module.customer_media_ingest_service = original_factory

    assert response.status_code == 403
    assert "todavía no autoriza" in response.json()["detail"].lower()


def test_evidence_image_route_serves_file(tmp_path: Path):
    image_path = tmp_path / "evidence.jpg"
    image_path.write_bytes(b"hello-image")

    app_repository.seed()
    if not app_repository.list_cases():
        case = ScoutAgent(app_repository, ForensicAgent()).process_gbp_event(suspicious_assets()[0])
    else:
        case = app_repository.list_cases()[0]

    artifact = EvidenceArtifact(
        id="evidence-image-test",
        case_id=case.id,
        artifact_type="observed_asset",
        label="Foto copiada",
        content={"evidence_image_path": f"file://{image_path}"},
    )
    app_repository.save_evidence(artifact)

    client = TestClient(app)
    client.post(
        "/auth/login",
        data={"email": "operator@vigilante.local", "password": "change-me"},
    )
    response = client.get("/api/evidence/evidence-image-test/image")

    assert response.status_code == 200
    assert response.content == b"hello-image"
