from types import SimpleNamespace
from urllib.parse import parse_qs, urlparse

from fastapi.testclient import TestClient

from app.config import settings
from app.main import app, _clone_profile_template_to_organization, _suggest_profile_templates_for_organization
from app.models import Organization, OrganizationType
from app.services.auth import AuthService, verify_password
from app.store import InMemoryRepository, repository as app_repository


def _login(client: TestClient, email: str, password: str):
    response = client.post(
        "/auth/login",
        data={"email": email, "password": password},
        follow_redirects=False,
    )
    assert response.status_code == 303


def test_google_oauth_uses_separate_scopes_for_signin_and_gbp():
    repo = InMemoryRepository()
    service = AuthService(repo)
    request = SimpleNamespace(session={})
    original_client_id = settings.google_oauth_client_id
    original_redirect_uri = settings.google_oauth_redirect_uri
    settings.google_oauth_client_id = "client-id"
    settings.google_oauth_redirect_uri = "https://example.com/callback"

    try:
        signin_url = service.google_oauth_authorize_url(request, purpose="signin")
        signin_params = parse_qs(urlparse(signin_url).query)
        assert "https://www.googleapis.com/auth/business.manage" not in signin_params["scope"][0]
        assert signin_params["prompt"][0] == "select_account"

        connect_url = service.google_oauth_authorize_url(
            request,
            organization_id="org-dealer-bello",
            purpose="gbp_connect",
        )
        connect_params = parse_qs(urlparse(connect_url).query)
        assert "https://www.googleapis.com/auth/business.manage" in connect_params["scope"][0]
        assert connect_params["access_type"][0] == "offline"
        assert "org-dealer-bello" in connect_params["state"][0]
        assert "gbp_connect" in connect_params["state"][0]
    finally:
        settings.google_oauth_client_id = original_client_id
        settings.google_oauth_redirect_uri = original_redirect_uri


def test_save_gbp_connection_updates_existing_and_disconnects():
    repo = InMemoryRepository()
    repo.seed()
    service = AuthService(repo)

    first = service.save_gbp_connection(
        organization_id="org-dealer-bello",
        provider_account_id="google-account-1",
        provider_email="dealer@example.com",
        refresh_token="refresh-token-1",
        scopes=["openid", "email", "profile", "https://www.googleapis.com/auth/business.manage"],
    )
    first.selected_profile_ids = ["profile-bello"]
    repo.save_gbp_connection(first)

    second = service.save_gbp_connection(
        organization_id="org-dealer-bello",
        provider_account_id="google-account-1",
        provider_email="dealer-updated@example.com",
        refresh_token="refresh-token-2",
        scopes=["openid", "email", "profile", "https://www.googleapis.com/auth/business.manage"],
    )

    assert first.id == second.id
    assert len(repo.list_gbp_connections("org-dealer-bello")) == 1
    assert second.provider_email == "dealer-updated@example.com"
    assert second.status.value == "connected"

    disconnected = service.disconnect_gbp_connection(
        organization_id="org-dealer-bello",
        connection_id=second.id,
    )
    assert disconnected.status.value == "disconnected"
    assert disconnected.selected_profile_ids == []
    assert disconnected.encrypted_refresh_token is None


def test_only_dealer_admin_or_super_admin_can_start_gbp_onboarding():
    app_repository.seed()
    client = TestClient(app)

    _login(client, "yamaha@vigilante.local", "yamaha-demo")
    yamaha_response = client.get("/api/organizations/org-dealer-bello/gbp/start", follow_redirects=False)
    assert yamaha_response.status_code == 403

    _login(client, "asesor.bello@motoblu.local", "dealer-demo")
    member_response = client.get("/api/organizations/org-dealer-bello/gbp/start", follow_redirects=False)
    assert member_response.status_code == 403


def test_inviting_existing_user_rotates_temporary_password():
    repo = InMemoryRepository()
    repo.seed()
    service = AuthService(repo)

    existing = repo.find_user_by_email("asesor.bello@motoblu.local")
    assert existing is not None
    previous_hash = existing.password_hash

    invited = service.invite_user(
        organization_id="org-dealer-bello",
        email="asesor.bello@motoblu.local",
        full_name="Asesor Motoblu Bello",
        role=existing and repo.list_memberships_for_user(existing.id)[0].role,
    )

    assert invited.password_hash != previous_hash
    assert verify_password(getattr(invited, "_temporary_password"), invited.password_hash)


def test_suggested_profiles_match_motoblu_group():
    repo = InMemoryRepository()
    repo.seed()
    organization = Organization(id="org-motoblu", name="Motoblu", organization_type=OrganizationType.DEALER)
    repo.save_organization(organization)

    from app import main as main_module

    original_repository = main_module.repository
    main_module.repository = repo
    try:
      suggestions = _suggest_profile_templates_for_organization(organization)
    finally:
      main_module.repository = original_repository

    names = {profile.name for profile in suggestions}
    assert "Motoblu Bello" in names
    assert "Motoblu Itagui" in names


def test_clone_profile_template_to_new_organization_creates_internal_profile():
    repo = InMemoryRepository()
    repo.seed()
    organization = Organization(id="org-motoblu", name="Motoblu", organization_type=OrganizationType.DEALER)
    repo.save_organization(organization)

    from app import main as main_module

    original_repository = main_module.repository
    main_module.repository = repo
    try:
      cloned = _clone_profile_template_to_organization("profile-bello", "org-motoblu")
    finally:
      main_module.repository = original_repository

    assert cloned is not None
    assert cloned.organization_id == "org-motoblu"
    assert cloned.name == "Motoblu Bello"
    assert cloned.id != "profile-bello"


def test_binding_real_google_locations_updates_selected_profiles():
    repo = InMemoryRepository()
    repo.seed()

    from app import main as main_module

    original_repository = main_module.repository
    main_module.repository = repo
    try:
        motoblu = Organization(id="org-motoblu", name="Motoblu", organization_type=OrganizationType.DEALER)
        repo.save_organization(motoblu)
        bello = _clone_profile_template_to_organization("profile-bello", "org-motoblu")
        itagui = _clone_profile_template_to_organization("profile-itagui", "org-motoblu")
        assert bello is not None and itagui is not None

        connection = repo.save_gbp_connection(
            main_module.auth_service().save_gbp_connection(
                organization_id="org-motoblu",
                provider_account_id="google-account-1",
                provider_email="dealer@example.com",
                refresh_token="refresh-token-1",
                scopes=["openid", "email", "profile", "https://www.googleapis.com/auth/business.manage"],
            )
        )
        connection.selected_profile_ids = [bello.id, itagui.id]
        connection.available_locations = [
            {"name": "locations/555", "title": "Motoblu Bello", "place_id": "demo-place-bello", "account_name": "accounts/777", "store_code": ""},
            {"name": "locations/556", "title": "Motoblu Itagui", "place_id": "demo-place-itagui", "account_name": "accounts/777", "store_code": ""},
        ]
        repo.save_gbp_connection(connection)

        client = TestClient(app)
        _login(client, "operator@vigilante.local", "change-me")
        response = client.post(
            f"/settings/organizations/org-motoblu/gbp/connections/{connection.id}/locations/bind",
            data={
                f"binding__{bello.id}": "locations/555",
                f"binding__{itagui.id}": "locations/556",
            },
            follow_redirects=False,
        )
    finally:
        main_module.repository = original_repository

    assert response.status_code == 303
    assert repo.profiles[bello.id].gbp_location_id == "locations/555"
    assert repo.profiles[itagui.id].gbp_location_id == "locations/556"


def test_binding_manual_google_location_normalizes_full_account_path():
    repo = InMemoryRepository()
    repo.seed()

    from app import main as main_module

    original_repository = main_module.repository
    main_module.repository = repo
    try:
        motoblu = Organization(id="org-motoblu", name="Motoblu", organization_type=OrganizationType.DEALER)
        repo.save_organization(motoblu)
        bello = _clone_profile_template_to_organization("profile-bello", "org-motoblu")
        assert bello is not None

        connection = repo.save_gbp_connection(
            main_module.auth_service().save_gbp_connection(
                organization_id="org-motoblu",
                provider_account_id="google-account-1",
                provider_email="dealer@example.com",
                refresh_token="refresh-token-1",
                scopes=["openid", "email", "profile", "https://www.googleapis.com/auth/business.manage"],
            )
        )
        connection.selected_profile_ids = [bello.id]
        repo.save_gbp_connection(connection)

        client = TestClient(app)
        _login(client, "operator@vigilante.local", "change-me")
        response = client.post(
            f"/settings/organizations/org-motoblu/gbp/connections/{connection.id}/locations/bind",
            data={
                f"binding__{bello.id}": "accounts/123456789/locations/987654321",
            },
            follow_redirects=False,
        )
    finally:
        main_module.repository = original_repository

    assert response.status_code == 303
    assert repo.profiles[bello.id].gbp_location_id == "locations/987654321"


def test_binding_manual_google_location_normalizes_business_profile_id_with_hyphens():
    repo = InMemoryRepository()
    repo.seed()

    from app import main as main_module

    original_repository = main_module.repository
    main_module.repository = repo
    try:
        motoblu = Organization(id="org-motoblu", name="Motoblu", organization_type=OrganizationType.DEALER)
        repo.save_organization(motoblu)
        bello = _clone_profile_template_to_organization("profile-bello", "org-motoblu")
        assert bello is not None

        connection = repo.save_gbp_connection(
            main_module.auth_service().save_gbp_connection(
                organization_id="org-motoblu",
                provider_account_id="google-account-1",
                provider_email="dealer@example.com",
                refresh_token="refresh-token-1",
                scopes=["openid", "email", "profile", "https://www.googleapis.com/auth/business.manage"],
            )
        )
        connection.selected_profile_ids = [bello.id]
        repo.save_gbp_connection(connection)

        client = TestClient(app)
        _login(client, "operator@vigilante.local", "change-me")
        response = client.post(
            f"/settings/organizations/org-motoblu/gbp/connections/{connection.id}/locations/bind",
            data={
                f"binding__{bello.id}": "2077-4711-1725-0315-453",
            },
            follow_redirects=False,
        )
    finally:
        main_module.repository = original_repository

    assert response.status_code == 303
    assert repo.profiles[bello.id].gbp_location_id == "locations/2077471117250315453"


def test_support_case_tracking_updates_gbp_connection():
    repo = InMemoryRepository()
    repo.seed()

    from app import main as main_module

    original_repository = main_module.repository
    main_module.repository = repo
    try:
        connection = repo.save_gbp_connection(
            main_module.auth_service().save_gbp_connection(
                organization_id="org-dealer-bello",
                provider_account_id="google-account-1",
                provider_email="dealer@example.com",
                refresh_token="refresh-token-1",
                scopes=["openid", "email", "profile", "https://www.googleapis.com/auth/business.manage"],
            )
        )

        client = TestClient(app)
        _login(client, "operator@vigilante.local", "change-me")
        response = client.post(
            f"/settings/organizations/org-dealer-bello/gbp/connections/{connection.id}/api-access",
            data={"case_id": "2-9803000040915", "access_status": "pending_google"},
            follow_redirects=False,
        )
    finally:
        main_module.repository = original_repository

    assert response.status_code == 303
    stored = repo.get_gbp_connection(connection.id)
    assert stored is not None
    assert stored.api_access_case_id == "2-9803000040915"
    assert stored.api_access_status == "pending_google"
