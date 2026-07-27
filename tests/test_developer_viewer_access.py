from fastapi.testclient import TestClient

from app.main import app
from app.models import UserRole
from app.services.auth import AuthService, hash_password
from app.store import repository


def _login_developer_viewer(client: TestClient):
    repository.seed()
    user, membership, _ = AuthService(repository).provision_developer_viewer(
        email="developer.viewer@example.com",
        full_name="Developer Viewer",
    )
    user.password_hash = hash_password("viewer-test-password")
    repository.save_user(user)
    response = client.post(
        "/auth/login",
        data={"email": user.email, "password": "viewer-test-password"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert membership.role == UserRole.DEVELOPER_VIEWER
    return user


def test_developer_viewer_has_network_read_access_without_settings():
    with TestClient(app) as client:
        _login_developer_viewer(client)

        dashboard = client.get("/")
        settings = client.get("/settings")
        cases = client.get("/api/cases")

    assert dashboard.status_code == 200
    assert cases.status_code == 200
    assert settings.status_code == 403
    assert 'href="/settings"' not in dashboard.text


def test_developer_viewer_cannot_change_case_status():
    with TestClient(app) as client:
        _login_developer_viewer(client)
        case = repository.list_cases()[0]
        previous_status = case.status

        response = client.post(
            f"/api/cases/{case.id}/status",
            json={"status": "confirmed"},
        )

    assert response.status_code == 403
    assert repository.get_case(case.id).status == previous_status


def test_developer_viewer_cannot_run_scan_or_generate_report():
    with TestClient(app) as client:
        _login_developer_viewer(client)
        case = repository.list_cases()[0]

        scan = client.post("/api/scans/run", json={"query": "yamaha bogota"})
        report = client.post(f"/api/cases/{case.id}/generate-report")

    assert scan.status_code == 403
    assert report.status_code == 403


def test_developer_viewer_provisioning_is_idempotent():
    repository.seed()
    service = AuthService(repository)

    first_user, first_membership, first_created = service.provision_developer_viewer(
        email="  trystan.jaquet@gmail.com ",
        full_name="Trystan Jaquet",
    )
    second_user, second_membership, second_created = service.provision_developer_viewer(
        email="trystan.jaquet@gmail.com",
        full_name="Trystan Jaquet",
    )

    assert first_created is True
    assert second_created is False
    assert first_user.id == second_user.id
    assert first_membership.id == second_membership.id
    assert first_membership.role == UserRole.DEVELOPER_VIEWER
