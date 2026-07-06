from datetime import datetime, timezone
from pathlib import Path

from fastapi.testclient import TestClient

from app.models import EvidenceArtifact, MonitoringMode, Organization, OrganizationType, SourceType, ThreatCase
from app.agents.forensic import ForensicAgent
from app.agents.reporter import ReporterAgent
from app.agents.scout import ScoutAgent
from app.main import app
from app.services.auth import AuthService
from app.services.dashboard import DashboardService
import app.services.dashboard as dashboard_module
from app.services.demo_data import suspicious_assets, suspicious_places
from app.store import InMemoryRepository, repository as app_repository


def _login(client: TestClient, email: str = "operator@vigilante.local", password: str = "change-me"):
    response = client.post(
        "/auth/login",
        data={"email": email, "password": password},
        follow_redirects=False,
    )
    assert response.status_code == 303


def test_login_atlas_asset_is_served_as_webp():
    with TestClient(app) as client:
        response = client.get("/static/medellin-atlas-login.webp")

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/webp"


def test_dashboard_sections_have_expected_shape():
    repo = InMemoryRepository()
    repo.seed()
    scout = ScoutAgent(repo, ForensicAgent())
    scout.run_public_scan("yamaha medellin", suspicious_places())
    scout.process_gbp_event(suspicious_assets()[0])
    sections = DashboardService(repo).all_sections()
    assert "executive" in sections
    assert "operations" in sections
    assert "territory" in sections
    assert "threats" in sections
    assert "trust" in sections
    assert sections["executive"]["highlights"][0]["label"] == "Amenazas activas"
    assert sections["territory"]["headline"] == "Cómo se distribuye el riesgo en el Valle de Aburrá"
    assert len(sections["territory"]["clusters"]) >= 1
    assert len(sections["executive"]["alert_feed"]) >= 1
    assert sections["threats"]["cards"][0]["dealer_maps_link"].startswith("https://www.google.com/maps")
    assert sections["threats"]["cards"][0]["identified_at"].endswith("COT")
    assert sections["threats"]["cards"][0]["observed_name"]
    assert len(sections["threats"]["filters"]["cities"]) >= 1


def test_command_alerts_are_sorted_by_risk():
    repo = InMemoryRepository()
    repo.seed()
    scout = ScoutAgent(repo, ForensicAgent())
    scout.run_public_scan("yamaha medellin", suspicious_places())
    scout.process_gbp_event(suspicious_assets()[0])

    cards = DashboardService(repo).threat_summary()["cards"]
    scores = [card["case"].risk_score for card in cards]

    assert scores == sorted(scores, reverse=True)


def test_public_scan_endpoint_accepts_trusted_cloud_scheduler_headers():
    repo = app_repository
    repo.seed()
    client = TestClient(app)

    response = client.post(
        "/api/scans/run",
        json={"query": "yamaha medellin"},
        headers={
            "User-Agent": "Google-Cloud-Scheduler",
            "X-CloudScheduler": "true",
            "X-CloudScheduler-JobName": "vigilante-public-scan-hourly",
            "X-CloudScheduler-ScheduleTime": "2026-03-24T22:00:00Z",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["scan"]["query"] == "yamaha medellin"


def test_public_scan_endpoint_still_requires_auth_without_scheduler_headers():
    client = TestClient(app)

    response = client.post("/api/scans/run", json={"query": "yamaha medellin"})

    assert response.status_code == 401


def test_format_when_uses_colombia_timezone():
    value = datetime(2026, 3, 19, 18, 30, tzinfo=timezone.utc)
    assert DashboardService._format_when(value) == "2026-03-19 13:30 COT"


def test_case_detail_builds_rich_context():
    repo = InMemoryRepository()
    repo.seed()
    scout = ScoutAgent(repo, ForensicAgent())
    scout.run_public_scan("yamaha medellin", suspicious_places())
    case = scout.process_gbp_event(suspicious_assets()[0])
    assert case is not None
    ReporterAgent(repo).generate_report(case)

    detail = DashboardService(repo).case_detail(case.id)
    assert detail is not None
    assert detail["case"].id == case.id
    assert detail["overview"][0]["label"] == "Identificado"
    assert detail["identified_at"].endswith("COT")
    assert detail["decision_summary"][0]["label"] == "Qué pasó"
    assert detail["command_center"]["headline"] == "Siguiente mejor acción"
    assert detail["report_brief"]["title"] == "Suplantación visual del perfil oficial de Motoblu Bello"
    assert detail["report_brief"]["official_phone"] == "6044440101"
    assert "Solicito revisión del perfil oficial" in detail["report_brief"]["copy_ready_text"]
    assert detail["workflow"][0]["label"] == "1. Revisar evidencia"
    assert len(detail["timeline"]) >= 4
    assert len(detail["evidence_cards"]) >= 2
    assert detail["browser_panel"]["show_submit_action"] is False
    assert isinstance(detail["browser_panel"]["blockers"], list)
    assert detail["primary_evidence"] is not None


def test_place_clone_case_detail_builds_comparison_panel():
    repo = InMemoryRepository()
    repo.seed()
    clone_case = ThreatCase(
        id="case-clone-ui-1",
        title="Posible clon de Motoblu Bello",
        dealer_id="dealer-bello",
        organization_id="org-dealer-bello",
        dealer_name="Motoblu Bello",
        city="Bello",
        monitoring_mode=MonitoringMode.PUBLIC_SCAN,
        source_type=SourceType.PLACE_CLONE,
        risk_score=88,
        risk_reasons=["Usa el nombre Yamaha Bello Principal y un teléfono no oficial."],
        summary="Punto sospechoso detectado muy cerca de la sede oficial.",
        location_label="Diagonal 50 45-12, Bello",
        source_reference_id="clone-bello-ui",
    )
    repo.save_case(clone_case)
    repo.save_evidence(
        EvidenceArtifact(
            id="evidence-clone-ui-1",
            case_id=clone_case.id,
            artifact_type="observed_place",
            label="Yamaha Bello Principal",
            content={
                "name": "Yamaha Bello Principal",
                "address": "Diagonal 50 45-12, Bello",
                "phone_number": "3019998888",
                "category": "motorcycle_dealer",
                "latitude": 6.3371,
                "longitude": -75.5549,
                "place_id": "clone-bello-ui",
                "google_maps_uri": "https://www.google.com/maps/@6.3371,-75.5549,17z",
                "source_query": "yamaha principal bello",
                "query_hits": ["yamaha bello", "yamaha principal bello"],
                "rating": 4.1,
                "user_rating_count": 12,
            },
        )
    )

    detail = DashboardService(repo).case_detail(clone_case.id)

    assert detail is not None
    assert detail["clone_comparison"] is not None
    assert detail["clone_comparison"]["clone_name"]
    assert detail["clone_comparison"]["official_name"] == clone_case.dealer_name
    assert detail["clone_comparison"]["clone_maps_link"].startswith("https://www.google.com/maps")
    assert detail["clone_comparison"]["clone_maps_link"] == "https://www.google.com/maps/search/?api=1&query=6.3371%2C-75.5549"
    assert "query_place_id=place-official-bello" in detail["clone_comparison"]["official_maps_link"]


def test_maps_link_prefers_place_identity_over_generic_map_view():
    link = DashboardService._maps_link(
        {
            "name": "Yamaha Bello Principal",
            "address": "Diagonal 50 45-12, Bello",
            "place_id": "clone-place-123",
            "google_maps_uri": "https://www.google.com/maps/@6.3371,-75.5549,17z",
        }
    )

    assert link == (
        "https://www.google.com/maps/search/?api=1&query=Yamaha%20Bello%20Principal%20"
        "Diagonal%2050%2045-12%2C%20Bello&query_place_id=clone-place-123"
    )


def test_maps_link_prefers_precise_google_cid_over_place_id():
    link = DashboardService._maps_link(
        {
            "raw_payload": {
                "googleMapsUri": "https://maps.google.com/?cid=5737355300905269745",
                "id": "ChIJ6yqsYgApRI4R8bmplD8un08",
            },
            "name": "Yamaha Principal Medellín",
            "address": "Cra. 48 #055422, Cl. 32B Sur #29, Envigado",
            "place_id": "ChIJ6yqsYgApRI4R8bmplD8un08",
        }
    )

    assert link == "https://maps.google.com/?cid=5737355300905269745"


def test_maps_link_prefers_coordinates_for_observed_places_with_unreliable_cid():
    link = DashboardService._maps_link(
        {
            "raw_payload": {
                "googleMapsUri": "https://maps.google.com/?cid=5737355300905269745",
                "id": "ChIJ6yqsYgApRI4R8bmplD8un08",
                "location": {"latitude": 6.177696, "longitude": -75.58995709999999},
            },
            "name": "Yamaha Principal Medellín",
            "address": "Cra. 48 #055422, Cl. 32B Sur #29, Envigado",
            "place_id": "ChIJ6yqsYgApRI4R8bmplD8un08",
            "latitude": 6.177696,
            "longitude": -75.58995709999999,
        }
    )

    assert link == "https://www.google.com/maps/search/?api=1&query=6.177696%2C-75.58995709999999"


def test_maps_link_recovers_query_place_id_from_google_maps_url():
    link = DashboardService._maps_link(
        {
            "name": "Yamaha Sports Calle 33",
            "google_maps_uri": (
                "https://www.google.com/maps/search/?api=1&query=Yamaha%20Sports"
                "&query_place_id=ChIJstable123"
            ),
        }
    )

    assert link == "https://www.google.com/maps/search/?api=1&query=Yamaha%20Sports&query_place_id=ChIJstable123"


def test_review_photo_case_prioritizes_visual_evidence_over_google_report_draft():
    repo = InMemoryRepository()
    repo.seed()
    case = ThreatCase(
        id="case-review-photo-primary",
        title="Foto sospechosa en Motoblu Bello",
        dealer_id="dealer-bello",
        organization_id="org-dealer-bello",
        dealer_name="Motoblu Bello",
        city="Bello",
        monitoring_mode=MonitoringMode.PUBLIC_SCAN,
        source_type=SourceType.REVIEW_PHOTO,
        risk_score=96,
        risk_reasons=["Foto de fachada con telefono no oficial."],
        summary="Una foto manipulada intenta desviar clientes desde el perfil oficial.",
        location_label="Bello",
        source_reference_id="review-photo-primary",
    )
    repo.save_case(case)
    repo.save_evidence(
        EvidenceArtifact(
            id="evidence-report-draft-priority",
            case_id=case.id,
            artifact_type="google_report_draft",
            label="Borrador de reporte Google",
            content={
                "report_url": "https://www.google.com/local/content/rap/report?postId=123",
            },
        )
    )
    repo.save_evidence(
        EvidenceArtifact(
            id="evidence-observed-photo-priority",
            case_id=case.id,
            artifact_type="observed_asset",
            label="Foto sospechosa",
            content={
                "source_page_url": "https://maps.google.com/?q=test",
                "captured_image_url": "https://example.com/photo.jpg",
                "image_url": "https://example.com/photo.jpg",
            },
        )
    )

    detail = DashboardService(repo).case_detail(case.id)

    assert detail is not None
    assert detail["primary_evidence"] is not None
    assert detail["primary_evidence"]["type"] == "observed_asset"
    assert detail["primary_evidence"]["media"] is not None


def test_dealer_maps_link_uses_places_resolution_when_profile_is_missing(monkeypatch):
    repo = InMemoryRepository()
    repo.seed()
    dealer = repo.dealers["dealer-guayabal"].model_copy(update={"id": "dealer-guayabal-no-profile"})
    repo._dealers[dealer.id] = dealer

    class _Place:
        name = "Mundo Yamaha Guayabal"
        address = "Calle 10 55-87, Medellin, Antioquia, Colombia"
        place_id = "ChIJtest123"
        raw_payload = {}

    monkeypatch.setattr(dashboard_module.places_search_service, "is_configured", lambda: True)
    monkeypatch.setattr(dashboard_module.places_search_service, "search_text", lambda query: [_Place()])

    service = DashboardService(repo)
    link = service._dealer_maps_link(dealer, prefer_resolution=True)

    assert "query_place_id=ChIJtest123" in link
    assert "Mundo%20Yamaha%20Guayabal" in link


def test_case_detail_page_renders():
    app_repository.seed()
    scout = ScoutAgent(app_repository, ForensicAgent())
    case = scout.process_gbp_event(suspicious_assets()[0])
    if case is None:
        scout.run_public_scan("yamaha medellin", suspicious_places())
        case = app_repository.list_cases()[0]
    ReporterAgent(app_repository).generate_report(case)
    client = TestClient(app)
    _login(client)
    response = client.get(f"/cases/{case.id}")

    assert response.status_code == 200
    assert "Siguiente mejor acción" in response.text
    assert "Prueba principal" in response.text
    assert "Contraste rápido" in response.text
    assert "Siguiente paso" in response.text
    assert "Prueba principal" in response.text
    assert "Borrador asistido para Google" in response.text
    assert "Texto listo para copiar en Google" in response.text


def test_place_clone_case_detail_opens_timeline_and_related_by_default():
    repo = app_repository
    repo.seed()
    clone_case = ThreatCase(
        id="case-clone-open-sections",
        title="Posible clon de Motoblu Bello",
        dealer_id="dealer-bello",
        organization_id="org-dealer-bello",
        dealer_name="Motoblu Bello",
        city="Bello",
        monitoring_mode=MonitoringMode.PUBLIC_SCAN,
        source_type=SourceType.PLACE_CLONE,
        risk_score=88,
        risk_reasons=["Usa el nombre Yamaha Bello Principal y un teléfono no oficial."],
        summary="Punto sospechoso detectado muy cerca de la sede oficial.",
        location_label="Diagonal 50 45-12, Bello",
        source_reference_id="clone-bello-open-sections",
    )
    repo.save_case(clone_case)
    repo.save_evidence(
        EvidenceArtifact(
            id="evidence-clone-open-sections",
            case_id=clone_case.id,
            artifact_type="observed_place",
            label="Yamaha Bello Principal",
            content={
                "name": "Yamaha Bello Principal",
                "address": "Diagonal 50 45-12, Bello",
                "phone_number": "3019998888",
                "category": "motorcycle_dealer",
                "latitude": 6.3371,
                "longitude": -75.5549,
                "place_id": "clone-bello-open-sections",
                "source_query": "yamaha principal bello",
                "query_hits": ["yamaha bello", "yamaha principal bello"],
            },
        )
    )

    client = TestClient(app)
    _login(client)
    response = client.get(f"/cases/{clone_case.id}")

    assert response.status_code == 200
    assert 'href="https://www.google.com/maps/search/?api=1&amp;query=6.3371%2C-75.5549" target="_blank" rel="noopener noreferrer"' in response.text
    assert '<summary>Ver línea de tiempo del caso</summary>' in response.text
    assert '<details class="follow-up-details" open>' in response.text
    assert "Ver otros casos de esta sede" in response.text


def test_archived_case_keeps_dismissed_status_suggestion_and_shows_in_archived_cards():
    repo = InMemoryRepository()
    repo.seed()
    case = ThreatCase(
        id="case-archived-1",
        title="Posible clon descartado de Motoblu Bello",
        dealer_id="dealer-bello",
        organization_id="org-dealer-bello",
        dealer_name="Motoblu Bello",
        city="Bello",
        monitoring_mode=MonitoringMode.PUBLIC_SCAN,
        source_type=SourceType.PLACE_CLONE,
        risk_score=77,
        status="dismissed",
        risk_reasons=["Falso positivo tras validación humana."],
        summary="Se descartó después de revisar el punto y contrastarlo con la sede oficial.",
        location_label="Bello",
        source_reference_id="archived-case-1",
    )
    repo.save_case(case)

    detail = DashboardService(repo).case_detail(case.id)
    sections = DashboardService(repo).all_sections()

    assert detail["command_center"]["status_suggestion"] == "dismissed"
    assert sections["threats"]["archived_count"] >= 1
    assert any(item["id"] == case.id for item in sections["threats"]["archived_cards"])


def test_dashboard_page_renders_territory_story():
    with TestClient(app) as client:
        _login(client)
        response = client.get("/")

    assert response.status_code == 200
    assert '/static/styles.css?v=' in response.text
    assert "Territorio" in response.text
    assert "Valle de Aburrá" in response.text
    assert "Abrir expediente" in response.text
    assert "Barrido público" in response.text
    assert "Estado actual de alertas" in response.text
    assert "Caso seleccionado" in response.text
    assert "Alertas activas" in response.text
    assert "Confianza del sistema" in response.text
    assert "Filtrar" in response.text
    assert 'data-command-pagination' in response.text
    assert 'data-command-page-next' in response.text
    assert "const commandPageSize = 6;" in response.text
    assert "Contrastar con sedes oficiales" in response.text
    assert "Punto en foco" in response.text


def test_paginated_command_alerts_respect_hidden_attribute():
    styles = (Path(__file__).parents[1] / "app" / "static" / "styles.css").read_text()
    template = (Path(__file__).parents[1] / "app" / "templates" / "dashboard.html").read_text()

    assert ".command-alert-row[hidden]" in styles
    assert "display: none;" in styles.split(".command-alert-row[hidden]", 1)[1].split("}", 1)[0]
    assert ".command-map-marker[hidden]" in styles
    assert "marker.hidden = visibleIndex === -1;" in template
    assert "positionCommandMarker(marker, row, visibleIndex);" in template


def test_api_me_and_dealer_scope():
    repo = app_repository
    repo.seed()
    scout = ScoutAgent(repo, ForensicAgent())
    if not repo.list_cases():
        scout.run_public_scan("yamaha medellin", suspicious_places())
    case = scout.process_gbp_event(suspicious_assets()[0])
    assert case is not None

    client = TestClient(app)
    _login(client, "bello@motoblu.local", "dealer-demo")

    me = client.get("/api/me")
    assert me.status_code == 200
    assert me.json()["user"]["email"] == "bello@motoblu.local"

    cases = client.get("/api/cases")
    assert cases.status_code == 200
    returned = cases.json()["items"]
    assert all(item["dealer_id"] == "dealer-bello" for item in returned)


def test_settings_view_switcher_allows_returning_to_network_view():
    app_repository.seed()
    client = TestClient(app)
    _login(client)

    select_org = client.post(
        "/settings/organization-selection",
        data={"organization_id": "org-dealer-bello"},
        follow_redirects=False,
    )
    assert select_org.status_code == 303

    network_view = client.post(
        "/settings/organization-selection",
        data={"organization_id": "__network__"},
        follow_redirects=False,
    )
    assert network_view.status_code == 303
    assert network_view.headers["location"] == "/settings"

    me = client.get("/api/me")
    assert me.status_code == 200
    assert me.json()["active_organization_id"] is None

    settings_page = client.get("/settings")
    assert settings_page.status_code == 200
    assert 'option value="__network__" selected' in settings_page.text


def test_settings_view_switcher_keeps_all_org_options_for_network_users():
    app_repository.seed()
    client = TestClient(app)
    _login(client)

    select_platform = client.post(
        "/settings/organization-selection",
        data={"organization_id": "org-platform"},
        follow_redirects=False,
    )
    assert select_platform.status_code == 303

    settings_page = client.get("/settings")
    assert settings_page.status_code == 200
    assert 'option value="org-platform" selected' in settings_page.text
    assert "Motoblu Bello" in settings_page.text


def test_select_organization_page_shows_full_network_options_for_network_users():
    app_repository.seed()
    app_repository.save_organization(Organization(id="org-gp-bikes", name="GP Bikes", organization_type=OrganizationType.DEALER))
    app_repository.save_organization(
        Organization(id="org-yamaha-sports", name="Yamaha Sports", organization_type=OrganizationType.DEALER)
    )
    client = TestClient(app)
    _login(client)

    page = client.get("/select-organization")
    assert page.status_code == 200
    assert "Vista global de redes" in page.text
    assert "Vigilante Platform" in page.text
    assert "Yamaha Red Oficial" in page.text
    assert "GP Bikes" in page.text
    assert "Yamaha Sports" in page.text


def test_settings_view_switcher_uses_curated_order():
    app_repository.seed()
    app_repository.save_organization(Organization(id="org-gp-bikes", name="GP Bikes", organization_type=OrganizationType.DEALER))
    app_repository.save_organization(
        Organization(id="org-yamaha-network", name="Yamaha Red Oficial", organization_type=OrganizationType.NETWORK)
    )
    app_repository.save_organization(
        Organization(id="org-yamaha-sports", name="Yamaha Sports", organization_type=OrganizationType.DEALER)
    )
    app_repository.save_organization(
        Organization(id="org-mundo-yamaha", name="Mundo Yamaha", organization_type=OrganizationType.DEALER)
    )
    client = TestClient(app)
    _login(client)

    settings_page = client.get("/settings")
    assert settings_page.status_code == 200

    text = settings_page.text
    start = text.index('<select name="organization_id" data-settings-view-select>')
    end = text.index("</select>", start)
    select_html = text[start:end]

    platform_pos = select_html.index('option value="org-platform"')
    global_pos = select_html.index('option value="__network__"')
    yamaha_network_pos = select_html.index('option value="org-yamaha-network"')
    gp_bikes_pos = select_html.index('option value="org-gp-bikes"')
    motoblu_pos = select_html.index('option value="org-dealer-bello"')
    mundo_yamaha_pos = select_html.index('option value="org-mundo-yamaha"')
    yamaha_sports_pos = select_html.index('option value="org-yamaha-sports"')

    assert platform_pos < global_pos < yamaha_network_pos < gp_bikes_pos < motoblu_pos < mundo_yamaha_pos < yamaha_sports_pos


def test_network_settings_view_uses_dealer_and_branch_language():
    app_repository.seed()
    client = TestClient(app)
    _login(client)

    select_network = client.post(
        "/settings/organization-selection",
        data={"organization_id": "org-yamaha-network"},
        follow_redirects=False,
    )
    assert select_network.status_code == 303

    settings_page = client.get("/settings")
    assert settings_page.status_code == 200
    assert "sedes monitoreadas" in settings_page.text
    assert "Red oficial Yamaha" in settings_page.text
    assert "Concesionario" in settings_page.text
    assert "Sedes" in settings_page.text
    assert "GBP" in settings_page.text


def test_dashboard_counts_profiles_when_network_view_is_active():
    repo = InMemoryRepository()
    repo.seed()
    actor = AuthService(repo)._actor_for_user("user-yamaha-admin", active_organization_id="org-yamaha-network")

    summary = DashboardService(repo, actor).executive_summary()

    assert summary["headline"]["coverage"] == "3 perfiles protegidos"


def test_google_super_admin_bootstrap():
    repo = InMemoryRepository()
    repo.seed()
    actor = AuthService(repo).login_google_user(
        email="joework.co@gmail.com",
        full_name="Joe Work",
        google_subject="google-super-admin-subject",
    )

    assert actor.is_super_admin
    assert actor.active_organization_id is None
    assert actor.user.email == "joework.co@gmail.com"


def test_super_admin_email_self_heals_membership_for_existing_user():
    repo = InMemoryRepository()
    repo.seed()
    user = repo.find_user_by_email("joework.co@gmail.com")
    assert user is None

    created = AuthService(repo).login_google_user(
        email="joework.co@gmail.com",
        full_name="Joe Work",
        google_subject="bootstrap-subject",
    )
    assert created.is_super_admin

    repo._memberships = {
        key: membership
        for key, membership in repo._memberships.items()
        if membership.user_id != created.user.id
    }

    actor = AuthService(repo).current_actor(
        type(
            "Req",
            (),
            {"session": {"user_id": created.user.id, "active_organization_id": None}},
        )()
    )

    assert actor is not None
    assert actor.is_super_admin
    assert any(item.role.value == "super_admin" for item in actor.memberships)
