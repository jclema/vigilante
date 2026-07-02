from fastapi.testclient import TestClient

import app.main as main_module
from app.main import app
from app.models import (
    BrowserExecutionMode,
    BrowserFlowType,
    BrowserRunStatus,
    BrowserSessionStatus,
    CaseStatus,
    EvidenceArtifact,
    MonitoringMode,
    SourceType,
    ThreatCase,
)
from app.services.browser_ops import BrowserEnforcementService, BrowserExecutionResult
from app.store import InMemoryRepository, repository as app_repository


class FakeBrowserExecutor:
    def submit(self, *, run, case, target, session):
        return BrowserExecutionResult(
            status=BrowserRunStatus.SUBMITTED,
            screenshots=["gs://bucket/browser-run-1/final.png"],
            dom_hints={"flow": target.flow_type.value, "auth_user": session.auth_user_email},
            audit_log=[{"step": "submitted", "status": "ok"}],
        )


def _seed_visual_case(repo: InMemoryRepository) -> ThreatCase:
    repo.seed()
    case = ThreatCase(
        id="case-browser-1",
        title="Foto crítica de Motoblu Bello",
        dealer_id="dealer-bello",
        organization_id="org-dealer-bello",
        dealer_name="Motoblu Bello",
        city="Bello",
        monitoring_mode=MonitoringMode.PUBLIC_SCAN,
        source_type=SourceType.REVIEW_PHOTO,
        risk_score=92,
        risk_reasons=["Se detectó un teléfono distinto al whitelist."],
        summary="La foto muestra la marca Yamaha y un teléfono distinto al oficial.",
        location_label="Bello",
    )
    repo.save_case(case)
    repo.save_evidence(
        EvidenceArtifact(
            id="evidence-browser-1",
            case_id=case.id,
            artifact_type="observed_asset",
            label="Fachada Motoblu Bello",
            content={
                "source_page_url": "https://www.google.com/local/content/rap/report?postId=abc&t=3&wv=1",
                "google_maps_uri": "https://www.google.com/local/content/rap/report?postId=abc&t=3&wv=1",
                "detected_phone_numbers": ["3019998888"],
                "ocr_text": "Yamaha Bello 301 999 8888",
                "raw_payload": {
                    "detected_phone_numbers": ["3019998888"],
                    "contributor_profile_url": "https://www.google.com/maps/contrib/1234567890",
                },
            },
        )
    )
    return case


def _login(client: TestClient, email: str = "operator@vigilante.local", password: str = "change-me"):
    response = client.post("/auth/login", data={"email": email, "password": password}, follow_redirects=False)
    assert response.status_code == 303


def test_browser_enforcement_marks_high_certainty_visual_case_as_auto_eligible():
    repo = InMemoryRepository()
    case = _seed_visual_case(repo)

    eligibility = BrowserEnforcementService(repo).evaluate_case(case)

    assert eligibility.eligible is True
    assert eligibility.target is not None
    assert eligibility.target.flow_type == BrowserFlowType.REPORT_PHOTO_MOBILE
    assert eligibility.target.contributor_profile_url == "https://www.google.com/maps/contrib/1234567890"


def test_browser_enforcement_resolves_pilot_target_from_capture_url():
    repo = InMemoryRepository()
    repo.seed()
    case = ThreatCase(
        id="case-browser-2",
        title="Foto crítica de Mundo Yamaha Guayabal",
        dealer_id="dealer-guayabal",
        organization_id="org-dealer-guayabal",
        dealer_name="Mundo Yamaha Guayabal",
        city="Medellin",
        monitoring_mode=MonitoringMode.PUBLIC_SCAN,
        source_type=SourceType.REVIEW_PHOTO,
        risk_score=88,
        risk_reasons=["La foto muestra teléfono distinto al oficial."],
        summary="La foto muestra marca Yamaha y contacto sospechoso.",
        location_label="Guayabal",
    )
    repo.save_case(case)
    repo.save_evidence(
        EvidenceArtifact(
            id="evidence-browser-2",
            case_id=case.id,
            artifact_type="observed_asset",
            label="Fachada Guayabal",
            content={
                "source_url": "https://lh3.googleusercontent.com/fake-capture.jpg",
                "detected_phone_numbers": ["3019997777"],
                "ocr_text": "Yamaha Guayabal 301 999 7777",
            },
        )
    )

    eligibility = BrowserEnforcementService(repo).evaluate_case(case)

    assert eligibility.target is not None
    assert eligibility.target.target_url == "https://lh3.googleusercontent.com/fake-capture.jpg"
    assert eligibility.eligible is True


def test_browser_enforcement_submit_updates_case_and_run():
    repo = InMemoryRepository()
    case = _seed_visual_case(repo)
    service = BrowserEnforcementService(repo, executor=FakeBrowserExecutor())
    service.refresh_session(
        organization_id="org-dealer-bello",
        auth_user_email="bello@motoblu.local",
        session_state="session-ok",
    )

    run = service.run_auto(case.id)
    updated = repo.get_case(case.id)

    assert run.status == BrowserRunStatus.SUBMITTED
    assert updated is not None
    assert updated.browser_status == BrowserRunStatus.SUBMITTED
    assert updated.browser_execution_mode == BrowserExecutionMode.AUTO_SUBMIT
    assert updated.browser_last_submitted_at is not None
    evidence = repo.list_evidence_for_case(case.id)
    assert any(item.artifact_type == "browser_enforcement_run" for item in evidence)


def test_browser_endpoints_prepare_and_refresh_session():
    app_repository.seed()
    case = _seed_visual_case(app_repository)
    client = TestClient(app)
    _login(client)

    refreshed = client.post(
        "/api/browser-sessions/org-dealer-bello/refresh",
        json={"auth_user_email": "dealer@example.com", "session_state": "session-1"},
    )
    assert refreshed.status_code == 200
    assert refreshed.json()["session"]["status"] == BrowserSessionStatus.ACTIVE.value

    prepared = client.post(f"/api/cases/{case.id}/browser-enforcement/prepare")
    assert prepared.status_code == 200
    assert prepared.json()["run"]["status"] == BrowserRunStatus.PREPARED.value

    state = client.get(f"/api/cases/{case.id}/browser-enforcement")
    assert state.status_code == 200
    payload = state.json()
    assert payload["eligibility"]["eligible"] is True
    assert payload["runs"][0]["execution_mode"] == BrowserExecutionMode.MANUAL_PREPARE.value


def test_confirming_case_only_prepares_browser_follow_up(monkeypatch):
    repo = InMemoryRepository()
    repo.seed()
    case = _seed_visual_case(repo)
    monkeypatch.setattr(main_module, "repository", repo)
    client = TestClient(app)
    _login(client)

    response = client.post(f"/api/cases/{case.id}/status", json={"status": "confirmed"})

    assert response.status_code == 200
    updated = repo.get_case(case.id)
    assert updated is not None
    assert updated.status == CaseStatus.CONFIRMED
    assert updated.browser_status == BrowserRunStatus.PREPARED
    assert updated.browser_execution_mode == BrowserExecutionMode.MANUAL_PREPARE
