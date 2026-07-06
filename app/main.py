from __future__ import annotations

from contextlib import asynccontextmanager
import hashlib
import mimetypes
from pathlib import Path
from time import monotonic
from urllib.parse import quote, urlencode, urlsplit
import re
from urllib.error import HTTPError
from datetime import datetime, UTC

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.agents.forensic import ForensicAgent
from app.agents.reporter import ReporterAgent
from app.agents.scout import ScoutAgent
from app.config import settings
from app.models import (
    AuthorizedDealer,
    BrowserExecutionMode,
    BrowserRunStatus,
    CaseStatus,
    ConnectionStatus,
    DealerProfile,
    GoogleReportStatus,
    MonitoringMode,
    NotificationChannel,
    NotificationDestination,
    NotificationEventType,
    ObservedAsset,
    Organization,
    OrganizationType,
    SourceType,
    UserRole,
)
from app.services.auth import AuthService
from app.services.browser_ops import BrowserEnforcementService
from app.services.dashboard import DashboardService
from app.services.demo_data import suspicious_assets
from app.services.evidence_media import EvidenceMediaService
from app.services.gbp_media import GbpCustomerMediaClient, GbpCustomerMediaIngestService, GbpOrganizationConnectionResolver
from app.services.multi_source_ingest import EvidenceIngestionRequest, MultiSourceEvidenceIngestService
from app.services.notifications import NotificationService
from app.services.places import places_search_service
from app.store import repository


BASE_DIR = Path(__file__).resolve().parent
ASSET_VERSION = hashlib.sha256((BASE_DIR / "static" / "styles.css").read_bytes()).hexdigest()[:12]
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
login_attempts: dict[str, list[float]] = {}


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings.validate_for_startup()
    if settings.seed_demo_data and not repository.dealers:
        repository.seed()
        scout = ScoutAgent(repository, ForensicAgent())
        scout.run_public_scan("yamaha medellin", places_search_service.search_clone_candidates("yamaha medellin"))
        for asset in suspicious_assets():
            scout.process_gbp_event(asset)
        reporter = ReporterAgent(repository, NotificationService(repository))
        for case in repository.list_cases()[:2]:
            if case.risk_score >= 70:
                reporter.create_alert(case)
                report = reporter.generate_report(case)
                case.google_report_status = GoogleReportStatus.DRAFTED
                case.google_report_response = report.response_summary
                if case.risk_score >= 80:
                    case.status = CaseStatus.CONFIRMED
                repository.save_case(case)
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.session_secret,
    same_site="lax",
    https_only=settings.is_production,
    max_age=28800,
)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_host_list)
mimetypes.add_type("image/webp", ".webp")
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    unsafe_method = request.method in {"POST", "PUT", "PATCH", "DELETE"}
    machine_endpoint = request.url.path == "/api/scans/run" or request.url.path.startswith("/api/webhooks/")
    if settings.is_production and unsafe_method and not machine_endpoint:
        source = request.headers.get("origin") or request.headers.get("referer")
        parsed_source = urlsplit(source) if source else None
        trusted_source = bool(
            parsed_source
            and parsed_source.scheme == "https"
            and parsed_source.hostname == request.url.hostname
        )
        if not trusted_source:
            response = JSONResponse({"detail": "Invalid request origin"}, status_code=403)
        else:
            response = await call_next(request)
    else:
        response = await call_next(request)
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "base-uri 'self'; "
        "connect-src 'self' https://accounts.google.com; "
        "font-src 'self' data:; "
        "form-action 'self'; "
        "frame-ancestors 'none'; "
        "img-src 'self' data: https:; "
        "object-src 'none'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline'"
    )
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    if settings.is_production:
        response.headers["Strict-Transport-Security"] = "max-age=86400"
    return response


@app.get("/healthz", include_in_schema=False)
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/readyz", include_in_schema=False)
async def readyz() -> dict[str, str]:
    return {"status": "ready", "storage_backend": settings.storage_backend}


def auth_service() -> AuthService:
    return AuthService(repository)


def dashboard_service(request: Request | None = None) -> DashboardService:
    actor = auth_service().current_actor(request) if request else None
    return DashboardService(repository, actor)


def _settings_redirect(notice: str, **params: str | int) -> RedirectResponse:
    query = urlencode(
        {"notice": notice, **{key: value for key, value in params.items() if value not in (None, "")}}
    )
    return RedirectResponse(url=f"/settings?{query}", status_code=303)


def _customer_media_summary_for_organization(organization_id: str | None) -> dict[str, object]:
    if not organization_id:
        return {
            "eligible_profiles": [],
            "eligible_profile_ids": [],
            "case_count": 0,
            "evidence_count": 0,
            "recent_jobs": [],
            "latest_job": None,
        }
    eligible_profiles = [
        profile
        for profile in repository.profiles.values()
        if profile.organization_id == organization_id
        and profile.enabled
        and profile.monitoring_mode == MonitoringMode.GBP_PUSH
        and profile.gbp_location_id
    ]
    case_ids: set[str] = set()
    evidence_count = 0
    for case in repository.list_cases():
        case_org_id = case.organization_id
        if not case_org_id and case.dealer_id:
            dealer = repository.dealers.get(case.dealer_id)
            case_org_id = dealer.organization_id if dealer else None
        if case_org_id != organization_id:
            continue
        media_evidence = [
            artifact
            for artifact in repository.list_evidence_for_case(case.id)
            if (artifact.content or {}).get("media_origin") == "gbp_customer_media"
        ]
        if media_evidence:
            case_ids.add(case.id)
            evidence_count += len(media_evidence)
    recent_jobs = [
        job
        for job in repository.list_jobs()
        if job.organization_id == organization_id
        and job.job_type in {"gbp_customer_media_backfill", "gbp_customer_media_reconcile"}
    ]
    recent_jobs.sort(key=lambda item: item.started_at, reverse=True)
    return {
        "eligible_profiles": eligible_profiles,
        "eligible_profile_ids": [profile.id for profile in eligible_profiles],
        "case_count": len(case_ids),
        "evidence_count": evidence_count,
        "recent_jobs": recent_jobs[:3],
        "latest_job": recent_jobs[0] if recent_jobs else None,
    }


def _settings_view_options(organizations: list[Organization], *, can_view_network: bool) -> list[dict[str, str]]:
    def preferred_rank(label: str) -> int:
        normalized = label.strip().lower()
        if normalized == "vigilante platform":
            return 0
        if normalized.startswith("yamaha red oficial"):
            return 2
        if normalized.startswith("gp bikes"):
            return 3
        if normalized.startswith("motoblu"):
            return 4
        if normalized.startswith("mundo yamaha"):
            return 5
        if normalized.startswith("yamaha sports"):
            return 6
        return 100

    org_options = [{"id": organization.id, "label": organization.name} for organization in organizations]
    org_options.sort(key=lambda item: (preferred_rank(item["label"]), item["label"].lower()))

    ordered_options: list[dict[str, str]] = []
    platform_option = next((item for item in org_options if item["label"].strip().lower() == "vigilante platform"), None)
    if platform_option:
        ordered_options.append(platform_option)
    if can_view_network:
        ordered_options.append({"id": "__network__", "label": "Vista global de redes"})
    ordered_options.extend(item for item in org_options if item is not platform_option)
    return ordered_options


def scout_agent() -> ScoutAgent:
    return ScoutAgent(repository, ForensicAgent())


def reporter_agent() -> ReporterAgent:
    return ReporterAgent(repository, NotificationService(repository))


def browser_enforcement_service() -> BrowserEnforcementService:
    return BrowserEnforcementService(repository)


def evidence_media_service() -> EvidenceMediaService:
    return EvidenceMediaService()


def customer_media_ingest_service() -> GbpCustomerMediaIngestService:
    return GbpCustomerMediaIngestService(
        repository=repository,
        scout_agent=scout_agent(),
        media_client=None,
        evidence_service=evidence_media_service(),
    )


def gbp_connection_resolver() -> GbpOrganizationConnectionResolver:
    return GbpOrganizationConnectionResolver(repository)


def multi_source_ingest_service() -> MultiSourceEvidenceIngestService:
    return MultiSourceEvidenceIngestService(
        repository=repository,
        scout_agent=scout_agent(),
        evidence_service=evidence_media_service(),
        text_extractor=customer_media_ingest_service().text_extractor,
    )


def _base_context(request: Request) -> dict[str, object]:
    actor = auth_service().current_actor(request)
    active_org = repository.get_organization(actor.active_organization_id) if actor and actor.active_organization_id else None
    return {
        "app_name": settings.app_name,
        "asset_version": ASSET_VERSION,
        "current_actor": actor,
        "active_organization": active_org,
    }


def _require_actor(request: Request):
    actor = auth_service().current_actor(request)
    if not actor:
        raise HTTPException(status_code=401, detail="Autenticación requerida")
    return actor


def _is_trusted_scheduler_request(request: Request, *, expected_job_name: str) -> bool:
    job_name = request.headers.get("X-CloudScheduler-JobName", "").strip()
    scheduler_flag = request.headers.get("X-CloudScheduler", "").strip().lower()
    schedule_time = request.headers.get("X-CloudScheduler-ScheduleTime", "").strip()
    user_agent = request.headers.get("User-Agent", "")
    return (
        job_name == expected_job_name
        and scheduler_flag == "true"
        and bool(schedule_time)
        and "Google-Cloud-Scheduler" in user_agent
    )


def _require_actor_or_scheduler(request: Request, *, scheduler_job_name: str):
    actor = auth_service().current_actor(request)
    if actor:
        return actor
    if _is_trusted_scheduler_request(request, expected_job_name=scheduler_job_name):
        return None
    raise HTTPException(status_code=401, detail="Autenticación requerida")


def _require_actor_page(request: Request):
    actor = auth_service().current_actor(request)
    if not actor:
        return None, RedirectResponse(url="/login", status_code=303)
    return actor, None


def _require_org_access(actor, organization_id: str) -> None:
    if actor.can_view_network or actor.can_manage_organization(organization_id):
        return
    raise HTTPException(status_code=403, detail="No tienes permisos sobre esta organización")


def _require_org_management(actor, organization_id: str) -> None:
    if actor.can_manage_platform or actor.can_manage_organization(organization_id):
        return
    raise HTTPException(status_code=403, detail="Solo un admin autorizado puede gestionar esta organización")


def _normalized_terms(value: str) -> list[str]:
    return [term for term in re.split(r"[^a-z0-9]+", value.lower()) if len(term) >= 4]


def _normalize_gbp_location_binding(raw_value: str) -> str:
    value = raw_value.strip()
    if not value:
        return ""
    if value.startswith("accounts/") and "/locations/" in value:
        return GbpCustomerMediaClient.location_suffix(value)
    if value.startswith("locations/"):
        return value
    compact_digits = re.sub(r"[^0-9]", "", value)
    if compact_digits and len(compact_digits) >= 10:
        return f"locations/{compact_digits}"
    raise ValueError("El identificador debe verse como locations/1234567890 o accounts/.../locations/1234567890")


def _build_connection_location_options(connection, profiles: list[DealerProfile]) -> dict[str, object]:
    selected_profiles = [profile for profile in profiles if profile.id in connection.selected_profile_ids]
    available_locations = connection.available_locations or []
    location_lookup = {item.get("name", ""): item for item in available_locations}
    bindings = []
    for profile in selected_profiles:
        suggested_location_name = profile.gbp_location_id if profile.gbp_location_id in location_lookup else None
        if not suggested_location_name:
            by_place = next(
                (
                    item
                    for item in available_locations
                    if profile.google_place_id
                    and item.get("place_id")
                    and item.get("place_id") == profile.google_place_id
                ),
                None,
            )
            if by_place:
                suggested_location_name = by_place.get("name")
        if not suggested_location_name:
            profile_terms = set(_normalized_terms(profile.name))
            by_name = next(
                (
                    item
                    for item in available_locations
                    if profile_terms
                    and len(profile_terms.intersection(_normalized_terms(item.get("title", "")))) >= min(2, len(profile_terms))
                ),
                None,
            )
            if by_name:
                suggested_location_name = by_name.get("name")
        bindings.append(
            {
                "profile": profile,
                "selected_location_name": suggested_location_name or "",
                "selected_location_value": suggested_location_name or profile.gbp_location_id or "",
            }
        )
    return {
        "connection": connection,
        "selected_profiles": selected_profiles,
        "available_locations": available_locations,
        "bindings": bindings,
    }


def _suggest_profile_templates_for_organization(organization: Organization) -> list[DealerProfile]:
    org_terms = _normalized_terms(organization.name)
    if not org_terms:
        return []
    existing_names = {
        profile.name.lower()
        for profile in repository.profiles.values()
        if profile.organization_id == organization.id
    }
    suggestions = []
    for profile in repository.profiles.values():
        if profile.organization_id == organization.id:
            continue
        haystack = f"{profile.name} {repository.dealers.get(profile.dealer_id).name if repository.dealers.get(profile.dealer_id) else ''}".lower()
        if profile.name.lower() in existing_names:
            continue
        if all(term in haystack for term in org_terms):
            suggestions.append(profile)
    return sorted(suggestions, key=lambda item: item.name)


def _clone_profile_template_to_organization(profile_id: str, organization_id: str) -> DealerProfile | None:
    source_profile = repository.profiles.get(profile_id)
    if not source_profile:
        return None
    source_dealer = repository.dealers.get(source_profile.dealer_id)
    if not source_dealer:
        return None
    already_exists = next(
        (
            profile
            for profile in repository.profiles.values()
            if profile.organization_id == organization_id
            and (
                (source_profile.google_place_id and profile.google_place_id == source_profile.google_place_id)
                or profile.name.strip().lower() == source_profile.name.strip().lower()
            )
        ),
        None,
    )
    if already_exists:
        return already_exists
    cloned_dealer = AuthorizedDealer(
        id=repository.next_id("dealer"),
        organization_id=organization_id,
        name=source_dealer.name,
        city=source_dealer.city,
        address=source_dealer.address,
        phone_numbers=list(source_dealer.phone_numbers),
        latitude=source_dealer.latitude,
        longitude=source_dealer.longitude,
        influence_label=source_dealer.influence_label,
        influence_radius_km=source_dealer.influence_radius_km,
    )
    cloned_profile = DealerProfile(
        id=repository.next_id("profile"),
        dealer_id=cloned_dealer.id,
        organization_id=organization_id,
        name=source_profile.name,
        google_place_id=source_profile.google_place_id,
        gbp_location_id=source_profile.gbp_location_id,
        monitoring_mode=source_profile.monitoring_mode,
        enabled=source_profile.enabled,
    )
    repository.import_whitelist([cloned_dealer])
    repository.import_profiles([cloned_profile])
    return cloned_profile


class DealerImportRequest(BaseModel):
    dealers: list[AuthorizedDealer]


class ProfileImportRequest(BaseModel):
    profiles: list[DealerProfile]


class ScanRequest(BaseModel):
    query: str = "yamaha medellin"


class StatusUpdateRequest(BaseModel):
    status: CaseStatus


class GbpWebhookPayload(BaseModel):
    profile_id: str
    source_type: str
    image_url: str | None = None
    external_media_id: str | None = None
    gbp_location_id: str | None = None
    source_page_url: str | None = None
    google_maps_uri: str | None = None
    thumbnail_url: str | None = None
    source_url: str | None = None
    review_id: str | None = None
    ingestion_mode: str | None = None
    review_text: str | None = None
    extracted_text: str | None = None
    raw_payload: dict[str, object] = Field(default_factory=dict)


class CustomerMediaBackfillRequest(BaseModel):
    profile_ids: list[str] | None = None
    limit: int = 20


class EvidenceIngestPayload(BaseModel):
    profile_id: str
    organization_id: str | None = None
    source_type: str
    source_url: str | None = None
    image_url: str | None = None
    source_page_url: str | None = None
    google_maps_uri: str | None = None
    thumbnail_url: str | None = None
    external_media_id: str | None = None
    gbp_location_id: str | None = None
    review_id: str | None = None
    ingestion_mode: str | None = None
    media_origin: str | None = None
    review_text: str | None = None
    extracted_text: str | None = None
    raw_payload: dict[str, object] = Field(default_factory=dict)


class OrganizationCreatePayload(BaseModel):
    name: str
    organization_type: OrganizationType = OrganizationType.DEALER


class BrowserSessionRefreshRequest(BaseModel):
    auth_user_email: str | None = None
    session_state: str | None = None


def _maybe_trigger_browser_follow_up(case) -> None:
    service = browser_enforcement_service()
    try:
        eligibility = service.evaluate_case(case)
        case.eligible_for_auto_submit = eligibility.eligible
        repository.save_case(case)
        if not eligibility.target:
            return
        service.prepare_case(case.id)
    except ValueError as exc:
        case.browser_last_error = str(exc)
        repository.save_case(case)


class InviteUserPayload(BaseModel):
    email: str
    full_name: str
    role: UserRole = UserRole.DEALER_MEMBER


class NotificationDestinationPayload(BaseModel):
    target: str
    subscribed_events: list[NotificationEventType] = Field(default_factory=list)


class GbpConnectionProfileSelectionPayload(BaseModel):
    profile_ids: list[str] = Field(default_factory=list)


@app.get("/", response_class=HTMLResponse)
async def home(request: Request) -> HTMLResponse:
    _, redirect = _require_actor_page(request)
    if redirect:
        return redirect
    scoped = dashboard_service(request)
    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            **_base_context(request),
            "sections": scoped.all_sections(),
            "cases": scoped.repository.list_cases(),
            "evidence_index": scoped.repository.evidence,
        },
    )


@app.get("/cases/{case_id}", response_class=HTMLResponse)
async def case_detail_page(request: Request, case_id: str) -> HTMLResponse:
    _, redirect = _require_actor_page(request)
    if redirect:
        return redirect
    scoped = dashboard_service(request)
    detail = scoped.case_detail(case_id)
    if not detail:
        raise HTTPException(status_code=404, detail="Caso no encontrado")
    return templates.TemplateResponse(
        request,
        "case_detail.html",
        {
            **_base_context(request),
            "sections": scoped.all_sections(),
            "detail": detail,
            "cases": scoped.repository.list_cases(),
            "case_notice": request.query_params.get("notice"),
            "case_notice_detail": request.query_params.get("detail"),
            "case_notice_tone": request.query_params.get("tone", "neutral"),
        },
    )


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "login.html", {**_base_context(request)})


@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "register.html", {**_base_context(request)})


@app.get("/select-organization", response_class=HTMLResponse)
async def select_organization_page(request: Request) -> HTMLResponse:
    actor, redirect = _require_actor_page(request)
    if redirect:
        return redirect
    organizations = repository.list_organizations()
    visible_org_ids = None if actor.can_view_network else actor.visible_organization_ids()
    if visible_org_ids is not None:
        organizations = [organization for organization in organizations if organization.id in visible_org_ids]
    settings_view_options = _settings_view_options(organizations, can_view_network=actor.can_view_network)
    return templates.TemplateResponse(
        request,
        "select_organization.html",
        {**_base_context(request), "organizations": organizations, "settings_view_options": settings_view_options},
    )


@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request) -> HTMLResponse:
    actor, redirect = _require_actor_page(request)
    if redirect:
        return redirect

    organizations = repository.list_organizations()
    visible_org_ids = None if actor.can_view_network else actor.visible_organization_ids()
    if visible_org_ids is not None:
        organizations = [organization for organization in organizations if organization.id in visible_org_ids]

    if actor.can_view_network and actor.active_organization_id is None:
        selected_org_id = None
    else:
        selected_org_id = actor.active_organization_id or (organizations[0].id if organizations else None)
    settings_view_options = _settings_view_options(organizations, can_view_network=actor.can_view_network)
    selected_org = next((organization for organization in organizations if organization.id == selected_org_id), None)
    memberships = {
        organization.id: [
            {"membership": membership, "user": repository.get_user(membership.user_id)}
            for membership in repository.list_memberships_for_organization(organization.id)
        ]
        for organization in organizations
    }
    notice_key = request.query_params.get("notice")
    notice_detail = request.query_params.get("detail")
    count_detail = request.query_params.get("count")
    type_detail = request.query_params.get("type")
    notice_by_key = {
        "organization_created": {
            "tone": "success",
            "title": "Organización creada",
            "message": (
                f"{notice_detail} ya quedó creada como {type_detail}."
                if notice_detail and type_detail
                else "La nueva organización ya quedó lista para empezar su configuración."
            ),
        },
        "user_invited": {
            "tone": "success",
            "title": "Invitación enviada",
            "message": (
                f"{notice_detail} ya quedó agregado a la organización activa."
                if notice_detail
                else "El usuario ya quedó agregado a la organización activa."
            ),
        },
        "notification_added": {
            "tone": "success",
            "title": "Destino agregado",
            "message": (
                f"{notice_detail} ya está suscrito para recibir alertas."
                if notice_detail
                else "Las alertas ya tienen un nuevo correo receptor activo."
            ),
        },
        "profiles_saved": {
            "tone": "success",
            "title": "Perfiles guardados",
            "message": (
                f"Quedaron asociados {count_detail} perfiles a esta conexión GBP."
                if count_detail is not None
                else "La selección de perfiles GBP quedó actualizada para esta organización."
            ),
        },
        "gbp_connected": {
            "tone": "success",
            "title": "Cuenta GBP conectada",
            "message": (
                f"{notice_detail} quedó conectada. Solo falta revisar perfiles y cobertura."
                if notice_detail
                else "La conexión oficial quedó registrada. Solo falta revisar perfiles y cobertura."
            ),
        },
        "gbp_disconnected": {
            "tone": "success",
            "title": "Cuenta GBP desconectada",
            "message": "La conexión oficial se retiró de Vigilante y los perfiles asociados quedaron desvinculados.",
        },
        "locations_refreshed": {
            "tone": "success",
            "title": "Locations sincronizadas",
            "message": (
                f"Se encontraron {count_detail} sedes reales desde Google y ya están listas para vincular."
                if count_detail is not None
                else "Las locations reales de Google ya están listas para vincular."
            ),
        },
        "locations_bound": {
            "tone": "success",
            "title": "Vinculación completada",
            "message": (
                f"Quedaron vinculados {count_detail} perfiles internos con sus locations reales de Google."
                if count_detail is not None
                else "Los perfiles internos ya quedaron vinculados con sus locations reales."
            ),
        },
        "gbp_rate_limited": {
            "tone": "warning",
            "title": "Google limitó temporalmente la consulta",
            "message": "La cuenta sí sigue conectada, pero Google devolvió un límite temporal al intentar descubrir sedes oficiales. Reintenta en unos minutos.",
        },
        "gbp_discovery_failed": {
            "tone": "warning",
            "title": "No fue posible descubrir las sedes oficiales",
            "message": "La conexión está guardada, pero Google no devolvió una respuesta usable para listar las sedes. Reintenta más tarde o revisa permisos de la cuenta.",
        },
        "api_access_logged": {
            "tone": "success",
            "title": "Seguimiento de Google registrado",
            "message": (
                f"Quedó guardado el caso de soporte {notice_detail} para esta conexión."
                if notice_detail
                else "Quedó guardado el seguimiento del acceso oficial con Google."
            ),
        },
        "profiles_imported": {
            "tone": "success",
            "title": "Perfiles listos",
            "message": (
                f"Se agregaron {count_detail} perfiles oficiales a esta organización."
                if count_detail is not None
                else "Los perfiles oficiales ya quedaron disponibles para esta organización."
            ),
        },
        "customer_media_backfill_done": {
            "tone": "success",
            "title": "Fotos oficiales sincronizadas",
            "message": (
                f"{count_detail} fotos revisadas desde Google. {notice_detail}"
                if count_detail is not None and notice_detail
                else "La sincronización oficial de fotos ya terminó para las sedes conectadas."
            ),
        },
        "customer_media_backfill_blocked": {
            "tone": "warning",
            "title": "Integración lista, acceso pendiente por Google",
            "message": notice_detail or "La cuenta y las sedes ya quedaron listas en Vigilante, pero Google todavía no habilita customer media oficial para este proyecto.",
        },
        "customer_media_backfill_failed": {
            "tone": "warning",
            "title": "La sincronización oficial no pudo completarse",
            "message": notice_detail or "Hubo un error al intentar leer customer media oficial para esta organización.",
        },
    }
    organization_health = {}
    for organization in organizations:
        org_memberships = memberships.get(organization.id, [])
        org_connections = repository.list_gbp_connections(organization.id)
        org_notifications = repository.list_notification_destinations(organization.id)
        has_connected = any(connection.status.value == "connected" for connection in org_connections)
        has_error = any(connection.status.value == "error" for connection in org_connections)
        if has_error:
            health = {
                "label": "Revisar",
                "tone": "critical",
                "summary": "Hay una conexión GBP con error que necesita atención.",
            }
        elif not org_connections:
            health = {
                "label": "Sin GBP",
                "tone": "warning",
                "summary": "Todavía no tiene una cuenta oficial conectada.",
            }
        elif not has_connected:
            health = {
                "label": "Pendiente",
                "tone": "warning",
                "summary": "La conexión existe, pero aún no quedó activa.",
            }
        elif any((connection.api_access_status or "") == "pending_google" for connection in org_connections):
            health = {
                "label": "Esperando Google",
                "tone": "watch",
                "summary": "La conexión oficial está lista, pero Google todavía no habilita customer media para el proyecto.",
            }
        elif not org_notifications:
            health = {
                "label": "Sin alertas",
                "tone": "warning",
                "summary": "La fuente oficial está conectada, pero no hay destinos de alerta.",
            }
        elif len(org_memberships) < 2:
            health = {
                "label": "Cobertura mínima",
                "tone": "watch",
                "summary": "La operación depende de muy pocas personas.",
            }
        else:
            health = {
                "label": "Lista",
                "tone": "healthy",
                "summary": "La base operativa está conectada y lista para operar.",
            }
        organization_health[organization.id] = {
            **health,
            "memberships": len(org_memberships),
            "connections": len(org_connections),
            "notifications": len(org_notifications),
        }

    network_dealer_organizations = [organization for organization in organizations if organization.organization_type == OrganizationType.DEALER]
    network_dealer_ids = {organization.id for organization in network_dealer_organizations}
    all_notifications = repository.list_notification_destinations()
    all_connections = repository.list_gbp_connections()
    all_dealers = list(repository.dealers.values())
    all_profiles = list(repository.profiles.values())

    network_rows = []
    for organization in sorted(network_dealer_organizations, key=lambda item: item.name.lower()):
        dealer_branches = [dealer for dealer in all_dealers if dealer.organization_id == organization.id]
        dealer_profiles = [profile for profile in all_profiles if profile.organization_id == organization.id]
        dealer_connections = [connection for connection in all_connections if connection.organization_id == organization.id]
        connected_count = sum(1 for connection in dealer_connections if connection.status == ConnectionStatus.CONNECTED)
        pending_count = sum(1 for connection in dealer_connections if connection.status == ConnectionStatus.PENDING)
        if connected_count:
            gbp_summary = f"{connected_count} activa" if connected_count == 1 else f"{connected_count} activas"
        elif pending_count:
            gbp_summary = "Pendiente"
        else:
            gbp_summary = "Sin GBP"

        network_rows.append(
            {
                "organization": organization,
                "health": organization_health[organization.id],
                "branch_count": len(dealer_branches),
                "branch_names": [dealer.name for dealer in sorted(dealer_branches, key=lambda item: item.name.lower())],
                "profile_count": len(dealer_profiles),
                "member_count": len(memberships.get(organization.id, [])),
                "notification_count": len(
                    [destination for destination in all_notifications if destination.organization_id == organization.id]
                ),
                "gbp_summary": gbp_summary,
            }
        )

    network_summary = {
        "dealers": len(network_dealer_organizations),
        "branches": len([dealer for dealer in all_dealers if dealer.organization_id in network_dealer_ids]),
        "connected_orgs": len(
            {
                connection.organization_id
                for connection in all_connections
                if connection.organization_id in network_dealer_ids and connection.status == ConnectionStatus.CONNECTED
            }
        ),
        "attention_orgs": len(
            [organization for organization in network_dealer_organizations if organization_health[organization.id]["tone"] != "healthy"]
        ),
    }

    profiles_for_selected_org = [
        profile
        for profile in repository.profiles.values()
        if not selected_org_id or profile.organization_id == selected_org_id
    ]
    connections = repository.list_gbp_connections(selected_org_id) if selected_org_id else []
    connection_location_options = [
        _build_connection_location_options(connection, profiles_for_selected_org)
        for connection in connections
        if connection.status.value != "disconnected"
    ]
    selected_dealer_rows = []
    if selected_org_id:
        selected_dealers = sorted(
            [dealer for dealer in repository.dealers.values() if dealer.organization_id == selected_org_id],
            key=lambda item: item.name.lower(),
        )
        profiles_by_dealer = {profile.dealer_id: profile for profile in profiles_for_selected_org}
        for dealer in selected_dealers:
            profile = profiles_by_dealer.get(dealer.id)
            if profile and profile.gbp_location_id:
                coverage = "Vinculada"
            elif profile and profile.monitoring_mode == MonitoringMode.GBP_PUSH:
                coverage = "GBP"
            elif profile:
                coverage = "Barrido publico"
            else:
                coverage = "Sin perfil"
            selected_dealer_rows.append(
                {
                    "dealer": dealer,
                    "profile": profile,
                    "coverage": coverage,
                    "phone_summary": ", ".join(dealer.phone_numbers[:2]) if dealer.phone_numbers else "Sin telefono",
                }
            )
    selected_cases_for_org = []
    customer_media_summary = _customer_media_summary_for_organization(selected_org_id)
    if selected_org_id:
        for case in repository.list_cases():
            case_org_id = case.organization_id
            if not case_org_id and case.dealer_id:
                dealer = repository.dealers.get(case.dealer_id)
                case_org_id = dealer.organization_id if dealer else None
            if case_org_id == selected_org_id:
                selected_cases_for_org.append(case)
        selected_cases_for_org.sort(key=lambda item: (item.status.value, -item.risk_score))

    return templates.TemplateResponse(
        request,
        "settings.html",
        {
            **_base_context(request),
            "organizations": organizations,
            "settings_view_options": settings_view_options,
            "selected_organization_id": selected_org_id,
            "memberships": memberships,
            "connections": connections,
            "connection_location_options": connection_location_options,
            "notifications": repository.list_notification_destinations(selected_org_id) if selected_org_id else [],
            "profiles": profiles_for_selected_org,
            "selected_dealer_rows": selected_dealer_rows,
            "selected_cases_for_org": selected_cases_for_org,
            "customer_media_summary": customer_media_summary,
            "suggested_profiles": _suggest_profile_templates_for_organization(selected_org) if selected_org else [],
            "organization_health": organization_health,
            "network_rows": network_rows,
            "network_summary": network_summary,
            "settings_notice": notice_by_key.get(notice_key),
            "settings_notice_detail": notice_detail,
            "settings_notice_password": request.query_params.get("password"),
        },
    )


@app.post("/auth/login")
async def login(request: Request, email: str = Form(...), password: str = Form(...)):
    normalized_email = email.strip().lower()
    client_ip = request.headers.get("cf-connecting-ip") or (request.client.host if request.client else "unknown")
    attempt_key = f"{client_ip}:{normalized_email}"
    if settings.is_production:
        now = monotonic()
        cutoff = now - settings.login_rate_limit_window_seconds
        recent_attempts = [attempt for attempt in login_attempts.get(attempt_key, []) if attempt >= cutoff]
        login_attempts[attempt_key] = recent_attempts
        if len(recent_attempts) >= settings.login_rate_limit_attempts:
            return JSONResponse(
                {"detail": "Too many login attempts"},
                status_code=429,
                headers={"Retry-After": str(settings.login_rate_limit_window_seconds)},
            )
    try:
        actor = auth_service().login(email=normalized_email, password=password)
    except ValueError as exc:
        if settings.is_production:
            login_attempts.setdefault(attempt_key, []).append(monotonic())
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    login_attempts.pop(attempt_key, None)
    auth_service().persist_session(request, actor)
    target = "/" if actor.active_organization_id or actor.can_view_network else "/select-organization"
    return RedirectResponse(url=target, status_code=303)


@app.post("/auth/register")
async def register(
    request: Request,
    full_name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    organization_name: str = Form(...),
):
    try:
        actor = auth_service().register_user(
            email=email,
            full_name=full_name,
            password=password,
            organization_name=organization_name,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    auth_service().persist_session(request, actor)
    return RedirectResponse(url="/settings", status_code=303)


@app.post("/auth/logout")
async def logout(request: Request):
    auth_service().clear_session(request)
    return RedirectResponse(url="/login", status_code=303)


@app.post("/auth/select-organization")
async def select_organization(request: Request, organization_id: str = Form(default="")):
    try:
        auth_service().switch_organization(request, organization_id or None)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return RedirectResponse(url="/", status_code=303)


@app.get("/auth/google/start")
async def google_auth_start(request: Request):
    try:
        url = auth_service().google_oauth_authorize_url(request, purpose="signin")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return RedirectResponse(url=url, status_code=303)


@app.get("/auth/google/callback")
async def google_auth_callback(request: Request, code: str, state: str):
    try:
        token_data = auth_service().exchange_google_callback(request, code=code, state=state)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    userinfo = token_data["userinfo"]
    state_payload = request.session.get("google_oauth_state") or {}
    organization_id = state_payload.get("organization_id")

    if organization_id:
        actor = auth_service().current_actor(request)
        if not actor:
            raise HTTPException(status_code=401, detail="Debes iniciar sesión en Vigilante antes de conectar GBP")
        _require_org_management(actor, organization_id)
        auth_service().save_gbp_connection(
            organization_id=organization_id,
            provider_account_id=userinfo["sub"],
            provider_email=userinfo.get("email"),
            refresh_token=token_data.get("refresh_token"),
            scopes=(token_data.get("scope") or "").split(),
        )
        return _settings_redirect("gbp_connected", detail=userinfo.get("email") or userinfo["sub"])

    actor = auth_service().login_google_user(
        email=userinfo["email"],
        full_name=userinfo.get("name") or userinfo["email"],
        google_subject=userinfo["sub"],
    )
    auth_service().persist_session(request, actor)
    target = "/" if actor.active_organization_id or actor.can_view_network else "/select-organization"
    return RedirectResponse(url=target, status_code=303)


@app.get("/api/me")
async def api_me(request: Request):
    actor = _require_actor(request)
    return {
        "user": actor.user,
        "memberships": actor.memberships,
        "active_organization_id": actor.active_organization_id,
    }


@app.post("/api/organizations")
async def create_organization(request: Request, payload: OrganizationCreatePayload):
    actor = _require_actor(request)
    if not actor.can_manage_platform:
        raise HTTPException(status_code=403, detail="Solo super admin puede crear organizaciones por API")
    organization = repository.save_organization(
        Organization(
            id=repository.next_id("org"),
            name=payload.name,
            organization_type=payload.organization_type,
        )
    )
    return {"organization": organization}


@app.post("/api/organizations/{organization_id}/invite")
async def invite_user(request: Request, organization_id: str, payload: InviteUserPayload):
    actor = _require_actor(request)
    _require_org_management(actor, organization_id)
    user = auth_service().invite_user(
        organization_id=organization_id,
        email=payload.email,
        full_name=payload.full_name,
        role=payload.role,
    )
    return {"user": user, "temporary_password": getattr(user, "_temporary_password", None)}


@app.get("/api/organizations/{organization_id}/gbp/start")
async def gbp_start(request: Request, organization_id: str):
    actor = _require_actor(request)
    _require_org_management(actor, organization_id)
    try:
        url = auth_service().google_oauth_authorize_url(request, organization_id=organization_id, purpose="gbp_connect")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return RedirectResponse(url=url, status_code=303)


@app.get("/api/organizations/{organization_id}/gbp/callback")
async def gbp_callback(request: Request, organization_id: str, code: str, state: str):
    actor = _require_actor(request)
    _require_org_management(actor, organization_id)
    try:
        token_data = auth_service().exchange_google_callback(request, code=code, state=state)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    userinfo = token_data["userinfo"]
    connection = auth_service().save_gbp_connection(
        organization_id=organization_id,
        provider_account_id=userinfo["sub"],
        provider_email=userinfo.get("email"),
        refresh_token=token_data.get("refresh_token"),
        scopes=(token_data.get("scope") or "").split(),
    )
    return {"connection": connection}


@app.post("/api/organizations/{organization_id}/gbp/connections/{connection_id}/profiles")
async def select_connection_profiles(
    request: Request,
    organization_id: str,
    connection_id: str,
    payload: GbpConnectionProfileSelectionPayload,
):
    actor = _require_actor(request)
    _require_org_management(actor, organization_id)
    connection = repository.get_gbp_connection(connection_id)
    if not connection or connection.organization_id != organization_id:
        raise HTTPException(status_code=404, detail="Conexión GBP no encontrada")
    connection.selected_profile_ids = payload.profile_ids
    connection.status = ConnectionStatus.CONNECTED
    repository.save_gbp_connection(connection)
    return {"connection": connection}


@app.post("/api/organizations/{organization_id}/gbp/connections/{connection_id}/disconnect")
async def disconnect_gbp_connection(request: Request, organization_id: str, connection_id: str):
    actor = _require_actor(request)
    _require_org_management(actor, organization_id)
    connection = auth_service().disconnect_gbp_connection(
        organization_id=organization_id,
        connection_id=connection_id,
    )
    return {"connection": connection}


@app.post("/api/organizations/{organization_id}/gbp/connections/{connection_id}/locations/refresh")
async def refresh_connection_locations(request: Request, organization_id: str, connection_id: str):
    actor = _require_actor(request)
    _require_org_management(actor, organization_id)
    try:
        locations = gbp_connection_resolver().discover_locations(
            organization_id=organization_id,
            connection_id=connection_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except HTTPError as exc:
        if exc.code == 429:
            raise HTTPException(
                status_code=429,
                detail="Google limitó temporalmente la consulta de sedes oficiales. Reintenta en unos minutos.",
            ) from exc
        raise HTTPException(
            status_code=502,
            detail="Google no devolvió una respuesta válida al intentar descubrir las sedes oficiales.",
        ) from exc
    return {"locations": locations, "count": len(locations)}


@app.post("/api/organizations/{organization_id}/gbp/connections/{connection_id}/locations/bind")
async def bind_connection_locations(request: Request, organization_id: str, connection_id: str):
    actor = _require_actor(request)
    _require_org_management(actor, organization_id)
    connection = repository.get_gbp_connection(connection_id)
    if not connection or connection.organization_id != organization_id:
        raise HTTPException(status_code=404, detail="Conexión GBP no encontrada")
    form = await request.form()
    available_locations = {item.get("name", ""): item for item in connection.available_locations}
    updated_profiles: list[DealerProfile] = []
    bound_count = 0
    for profile in repository.profiles.values():
        if profile.organization_id != organization_id or profile.id not in connection.selected_profile_ids:
            continue
        manual_location_name = str(form.get(f"binding__{profile.id}", "") or "")
        selected_location_name = str(form.get(f"binding_select__{profile.id}", "") or "")
        raw_location_name = manual_location_name or selected_location_name
        try:
            location_name = _normalize_gbp_location_binding(raw_location_name)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        if not location_name:
            continue
        if available_locations and location_name not in available_locations:
            matched_location = next(
                (
                    item.get("name", "")
                    for item in connection.available_locations
                    if item.get("name") == location_name or item.get("name") == raw_location_name.strip()
                ),
                "",
            )
            if matched_location:
                location_name = matched_location
        profile.gbp_location_id = location_name
        updated_profiles.append(profile)
        bound_count += 1
    if updated_profiles:
        repository.import_profiles(updated_profiles)
    return {"profiles": updated_profiles, "count": bound_count}


@app.post("/api/organizations/{organization_id}/notifications/email")
async def create_notification_destination(
    request: Request,
    organization_id: str,
    payload: NotificationDestinationPayload,
):
    actor = _require_actor(request)
    _require_org_management(actor, organization_id)
    destination = NotificationDestination(
        id=repository.next_id("notification"),
        organization_id=organization_id,
        channel=NotificationChannel.EMAIL,
        target=payload.target,
        subscribed_events=payload.subscribed_events or [
            NotificationEventType.NEW_ALERT,
            NotificationEventType.CASE_CONFIRMED,
            NotificationEventType.CASE_READY_FOR_GOOGLE,
            NotificationEventType.STATUS_CHANGED,
        ],
    )
    repository.save_notification_destination(destination)
    return {"destination": destination}


@app.post("/settings/organizations")
async def create_organization_form(
    request: Request,
    name: str = Form(...),
    organization_type: OrganizationType = Form(OrganizationType.DEALER),
):
    await create_organization(request, OrganizationCreatePayload(name=name, organization_type=organization_type))
    return _settings_redirect(
        "organization_created",
        detail=name.strip(),
        type=organization_type.value.replace("_", " "),
    )


@app.post("/settings/organizations/{organization_id}/invite")
async def invite_user_form(
    request: Request,
    organization_id: str,
    full_name: str = Form(...),
    email: str = Form(...),
    role: UserRole = Form(UserRole.DEALER_MEMBER),
):
    result = await invite_user(request, organization_id, InviteUserPayload(email=email, full_name=full_name, role=role))
    return _settings_redirect(
        "user_invited",
        detail=email.strip().lower(),
        password=result.get("temporary_password") or "",
    )


@app.post("/settings/organizations/{organization_id}/notifications/email")
async def notification_destination_form(
    request: Request,
    organization_id: str,
    target: str = Form(...),
):
    await create_notification_destination(
        request,
        organization_id,
        NotificationDestinationPayload(
            target=target,
            subscribed_events=[
                NotificationEventType.NEW_ALERT,
                NotificationEventType.CASE_CONFIRMED,
                NotificationEventType.CASE_READY_FOR_GOOGLE,
                NotificationEventType.STATUS_CHANGED,
            ],
        ),
    )
    return _settings_redirect("notification_added", detail=target.strip().lower())


@app.post("/settings/organizations/{organization_id}/gbp/connections/{connection_id}/profiles")
async def connection_profiles_form(
    request: Request,
    organization_id: str,
    connection_id: str,
    profile_ids: list[str] = Form(default=[]),
):
    await select_connection_profiles(
        request,
        organization_id,
        connection_id,
        GbpConnectionProfileSelectionPayload(profile_ids=profile_ids),
    )
    return _settings_redirect("profiles_saved", count=len(profile_ids))


@app.post("/settings/organizations/{organization_id}/gbp/connections/{connection_id}/disconnect")
async def disconnect_gbp_connection_form(request: Request, organization_id: str, connection_id: str):
    await disconnect_gbp_connection(request, organization_id, connection_id)
    return _settings_redirect("gbp_disconnected")


@app.post("/settings/organizations/{organization_id}/gbp/connections/{connection_id}/locations/refresh")
async def refresh_connection_locations_form(request: Request, organization_id: str, connection_id: str):
    try:
        result = await refresh_connection_locations(request, organization_id, connection_id)
    except HTTPException as exc:
        if exc.status_code == 429:
            return _settings_redirect("gbp_rate_limited")
        return _settings_redirect("gbp_discovery_failed")
    return _settings_redirect("locations_refreshed", count=result.get("count", 0))


@app.post("/settings/organizations/{organization_id}/gbp/connections/{connection_id}/locations/bind")
async def bind_connection_locations_form(request: Request, organization_id: str, connection_id: str):
    result = await bind_connection_locations(request, organization_id, connection_id)
    return _settings_redirect("locations_bound", count=result.get("count", 0))


@app.post("/settings/organizations/{organization_id}/gbp/connections/{connection_id}/api-access")
async def update_connection_api_access_form(
    request: Request,
    organization_id: str,
    connection_id: str,
    case_id: str = Form(default=""),
    access_status: str = Form(default="pending_google"),
):
    actor = _require_actor(request)
    _require_org_management(actor, organization_id)
    connection = repository.get_gbp_connection(connection_id)
    if not connection or connection.organization_id != organization_id:
        raise HTTPException(status_code=404, detail="Conexión GBP no encontrada")
    connection.api_access_case_id = case_id.strip() or None
    connection.api_access_status = access_status.strip() or None
    connection.updated_at = datetime.now(UTC)
    repository.save_gbp_connection(connection)
    return _settings_redirect("api_access_logged", detail=connection.api_access_case_id or "")


@app.post("/settings/organizations/{organization_id}/gbp/customer-media/backfill")
async def customer_media_backfill_form(request: Request, organization_id: str, limit: int = Form(default=20)):
    actor = _require_actor(request)
    _require_org_management(actor, organization_id)
    eligible_profiles = [
        profile.id
        for profile in repository.profiles.values()
        if profile.organization_id == organization_id
        and profile.enabled
        and profile.monitoring_mode == MonitoringMode.GBP_PUSH
        and profile.gbp_location_id
    ]
    if not eligible_profiles:
        return _settings_redirect(
            "customer_media_backfill_failed",
            detail="Todavia no hay sedes GBP vinculadas con location oficial para esta organizacion.",
        )
    try:
        result = customer_media_ingest_service().sync_profiles(eligible_profiles, limit=limit)
    except ValueError as exc:
        return _settings_redirect("customer_media_backfill_failed", detail=str(exc))
    except HTTPError as exc:
        if exc.code == 403:
            return _settings_redirect(
                "customer_media_backfill_blocked",
                detail="Google todavia no autoriza a este proyecto a leer customer media oficial para la cuenta conectada.",
            )
        if exc.code == 429:
            return _settings_redirect(
                "customer_media_backfill_blocked",
                detail="Google limito temporalmente la lectura de customer media oficial. Reintenta mas tarde.",
            )
        return _settings_redirect(
            "customer_media_backfill_failed",
            detail="Google devolvio un error al intentar leer customer media oficial.",
        )

    totals = result.get("totals", {})
    processed = totals.get("processed", 0)
    created = totals.get("cases_created", 0)
    updated = totals.get("cases_updated", 0)
    detail = f"{created} casos nuevos, {updated} expedientes enriquecidos."
    return _settings_redirect("customer_media_backfill_done", count=processed, detail=detail)


@app.post("/settings/organizations/{organization_id}/profiles/import-suggestions")
async def import_suggested_profiles_form(
    request: Request,
    organization_id: str,
    profile_ids: list[str] = Form(default=[]),
):
    actor = _require_actor(request)
    _require_org_management(actor, organization_id)
    imported = []
    for profile_id in profile_ids:
        profile = _clone_profile_template_to_organization(profile_id, organization_id)
        if profile:
            imported.append(profile)
    return _settings_redirect("profiles_imported", count=len(imported))


@app.post("/settings/organization-selection")
async def switch_org_form(request: Request, organization_id: str = Form(default="")):
    normalized_org_id = None if organization_id in {"", "__network__"} else organization_id
    try:
        auth_service().switch_organization(request, normalized_org_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return RedirectResponse(url="/settings", status_code=303)


@app.post("/api/import/whitelist")
async def import_whitelist(request: Request, payload: DealerImportRequest):
    actor = _require_actor(request)
    if not actor.can_manage_platform:
        raise HTTPException(status_code=403, detail="Solo super admin puede importar whitelist")
    return {"items": repository.import_whitelist(payload.dealers)}


@app.post("/api/dealers/import")
async def import_profiles(request: Request, payload: ProfileImportRequest):
    actor = _require_actor(request)
    if not actor.can_manage_platform:
        raise HTTPException(status_code=403, detail="Solo super admin puede importar perfiles")
    return {"items": repository.import_profiles(payload.profiles)}


@app.post("/api/scans/run")
async def run_scan(request: Request, payload: ScanRequest):
    _require_actor_or_scheduler(request, scheduler_job_name="vigilante-public-scan-hourly")
    scan = scout_agent().run_public_scan(payload.query, places_search_service.search_clone_candidates(payload.query))
    return {"scan": scan, "cases": dashboard_service(request).repository.list_cases()}


@app.post("/api/webhooks/gbp")
async def gbp_webhook(payload: GbpWebhookPayload):
    if payload.source_type not in {"review_photo", "official_profile_update"}:
        raise HTTPException(status_code=400, detail="source_type invalido")
    case = scout_agent().process_gbp_event(
        ObservedAsset(
            id=repository.next_id("asset"),
            profile_id=payload.profile_id,
            source_type=payload.source_type,
            image_url=payload.image_url,
            external_media_id=payload.external_media_id,
            gbp_location_id=payload.gbp_location_id,
            source_page_url=payload.source_page_url,
            google_maps_uri=payload.google_maps_uri,
            thumbnail_url=payload.thumbnail_url,
            source_url=payload.source_url,
            review_id=payload.review_id,
            ingestion_mode=payload.ingestion_mode,
            review_text=payload.review_text,
            extracted_text=payload.extracted_text,
            raw_payload=payload.raw_payload,
        )
    )
    return {"case": case}


@app.post("/api/webhooks/gbp/customer-media")
async def gbp_customer_media_webhook(request: Request):
    payload = await request.json()
    try:
        result = customer_media_ingest_service().sync_push_payload(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return result


@app.post("/api/gbp/customer-media/backfill")
async def backfill_customer_media(payload: CustomerMediaBackfillRequest):
    try:
        return customer_media_ingest_service().sync_profiles(payload.profile_ids, limit=payload.limit)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except HTTPError as exc:
        if exc.code == 403:
            raise HTTPException(
                status_code=403,
                detail=(
                    "Google todavía no autoriza a este proyecto a leer customer media oficial para la cuenta conectada. "
                    "La conexión y las sedes ya quedaron listas; falta aprobación/acceso de GBP API."
                ),
            ) from exc
        if exc.code == 429:
            raise HTTPException(
                status_code=429,
                detail="Google limitó temporalmente la lectura de customer media oficial. Reintenta más tarde.",
            ) from exc
        raise HTTPException(
            status_code=502,
            detail="Google devolvió un error al intentar leer customer media oficial para las sedes vinculadas.",
        ) from exc


@app.post("/api/evidence/review-photo")
async def ingest_review_photo(request: Request, payload: EvidenceIngestPayload):
    _require_actor(request)
    if payload.source_type not in {"review_photo", "official_profile_update"}:
        raise HTTPException(status_code=400, detail="source_type invalido")
    try:
        case = multi_source_ingest_service().ingest_request(
            EvidenceIngestionRequest(
                profile_id=payload.profile_id,
                organization_id=payload.organization_id,
                source_type=SourceType(payload.source_type),
                source_url=payload.source_url,
                image_url=payload.image_url,
                source_page_url=payload.source_page_url,
                google_maps_uri=payload.google_maps_uri,
                thumbnail_url=payload.thumbnail_url,
                external_media_id=payload.external_media_id,
                gbp_location_id=payload.gbp_location_id,
                review_id=payload.review_id,
                ingestion_mode=payload.ingestion_mode,
                media_origin=payload.media_origin,
                review_text=payload.review_text,
                extracted_text=payload.extracted_text,
                raw_payload=payload.raw_payload,
            )
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"case": case}


@app.get("/api/cases")
async def list_cases(request: Request):
    _require_actor(request)
    return {"items": dashboard_service(request).repository.list_cases()}


@app.get("/api/cases/{case_id}")
async def get_case(request: Request, case_id: str):
    _require_actor(request)
    scoped = dashboard_service(request).repository
    case = scoped.get_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Caso no encontrado")
    evidence = scoped.list_evidence_for_case(case_id)
    report = scoped.get_report(case_id)
    return {"case": case, "evidence": evidence, "report": report}


@app.get("/api/evidence/image")
async def get_evidence_image(path: str):
    if not path:
        raise HTTPException(status_code=404, detail="La evidencia no tiene imagen capturada")
    try:
        payload, content_type = evidence_media_service().load_image(str(path))
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="No fue posible abrir la imagen de evidencia") from exc
    return Response(content=payload, media_type=content_type)


@app.get("/api/evidence/{artifact_id}/image")
async def get_evidence_image_by_artifact(artifact_id: str):
    artifact = repository.evidence.get(artifact_id)
    if not artifact:
        raise HTTPException(status_code=404, detail="Evidencia no encontrada")
    storage_path = (artifact.content or {}).get("evidence_image_path")
    if not storage_path:
        raise HTTPException(status_code=404, detail="La evidencia no tiene imagen capturada")
    return await get_evidence_image(str(storage_path))


@app.post("/api/cases/{case_id}/status")
async def update_case_status(request: Request, case_id: str, payload: StatusUpdateRequest):
    _require_actor(request)
    case = repository.get_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Caso no encontrado")
    previous_status = case.status
    case.status = payload.status
    repository.save_case(case)
    if previous_status != payload.status:
        reporter_agent().notification_service.notify_case_event(case, NotificationEventType.STATUS_CHANGED)
        if payload.status == CaseStatus.CONFIRMED:
            reporter_agent().notification_service.notify_case_event(case, NotificationEventType.CASE_CONFIRMED)
            _maybe_trigger_browser_follow_up(case)
    return {"case": case}


@app.post("/api/cases/{case_id}/generate-report")
async def generate_case_report(request: Request, case_id: str):
    _require_actor(request)
    case = repository.get_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Caso no encontrado")
    report = reporter_agent().generate_report(case)
    case.status = CaseStatus.REPORTED if case.status == CaseStatus.CONFIRMED else case.status
    repository.save_case(case)
    return {"report": report}


@app.get("/api/cases/{case_id}/browser-enforcement")
async def get_case_browser_enforcement(request: Request, case_id: str):
    _require_actor(request)
    case = repository.get_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Caso no encontrado")
    return browser_enforcement_service().get_case_browser_state(case_id)


@app.post("/api/cases/{case_id}/browser-enforcement/prepare")
async def prepare_case_browser_enforcement(request: Request, case_id: str):
    _require_actor(request)
    case = repository.get_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Caso no encontrado")
    try:
        run = browser_enforcement_service().prepare_case(case_id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"run": run}


@app.post("/api/cases/{case_id}/browser-enforcement/approve")
async def approve_case_browser_enforcement(request: Request, case_id: str):
    _require_actor(request)
    case = repository.get_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Caso no encontrado")
    try:
        run = browser_enforcement_service().approve_case(case_id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"run": run}


@app.post("/api/cases/{case_id}/browser-enforcement/submit")
async def submit_case_browser_enforcement(request: Request, case_id: str):
    _require_actor(request)
    case = repository.get_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Caso no encontrado")
    try:
        run = browser_enforcement_service().submit_case(case_id, execution_mode=BrowserExecutionMode.SEMI_AUTO_SUBMIT)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"run": run}


@app.post("/api/cases/{case_id}/browser-enforcement/run-auto")
async def run_case_browser_enforcement_auto(request: Request, case_id: str):
    _require_actor(request)
    case = repository.get_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Caso no encontrado")
    try:
        run = browser_enforcement_service().run_auto(case_id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"run": run}


@app.post("/cases/{case_id}/browser-enforcement/submit")
async def submit_case_browser_enforcement_page(request: Request, case_id: str):
    actor = _require_actor(request)
    case = repository.get_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Caso no encontrado")
    if case.organization_id:
        _require_org_management(actor, case.organization_id)
    try:
        run = browser_enforcement_service().submit_case(case_id, execution_mode=BrowserExecutionMode.SEMI_AUTO_SUBMIT)
        notice = "Denuncia browser ejecutada"
        detail = f"Run {run.id} en estado {run.status.value}"
        tone = "success" if run.status == BrowserRunStatus.SUBMITTED else "warning"
    except ValueError as exc:
        notice = "No fue posible ejecutar la denuncia"
        detail = str(exc)
        tone = "warning"
    return RedirectResponse(
        url=f"/cases/{case_id}?notice={quote(notice)}&detail={quote(detail)}&tone={quote(tone)}",
        status_code=303,
    )


@app.get("/api/browser-runs/{run_id}")
async def get_browser_run(request: Request, run_id: str):
    _require_actor(request)
    run = repository.get_browser_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Browser run no encontrado")
    return {"run": run}


@app.post("/api/browser-sessions/{organization_id}/refresh")
async def refresh_browser_session(request: Request, organization_id: str, payload: BrowserSessionRefreshRequest):
    actor = _require_actor(request)
    _require_org_management(actor, organization_id)
    auth_user_email = payload.auth_user_email or actor.user.email
    session = browser_enforcement_service().refresh_session(
        organization_id=organization_id,
        auth_user_email=auth_user_email,
        session_state=payload.session_state,
    )
    return {"session": session}


@app.get("/api/dashboard/executive")
async def executive_dashboard(request: Request):
    _require_actor(request)
    return dashboard_service(request).executive_summary()


@app.get("/api/dashboard/operations")
async def operations_dashboard(request: Request):
    _require_actor(request)
    return dashboard_service(request).operations_summary()


@app.get("/api/dashboard/threats")
async def threats_dashboard(request: Request):
    _require_actor(request)
    return dashboard_service(request).threat_summary()


@app.get("/api/dashboard/trust")
async def trust_dashboard(request: Request):
    _require_actor(request)
    return dashboard_service(request).trust_summary()


@app.post("/cases/{case_id}/status", response_class=HTMLResponse)
async def update_case_status_form(
    request: Request,
    case_id: str,
    status: CaseStatus = Form(...),
    next_path: str | None = Form(default=None),
):
    case = repository.get_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Caso no encontrado")
    previous_status = case.status
    case.status = status
    repository.save_case(case)
    if previous_status != status:
        reporter_agent().notification_service.notify_case_event(case, NotificationEventType.STATUS_CHANGED)
        if status == CaseStatus.CONFIRMED:
            reporter_agent().notification_service.notify_case_event(case, NotificationEventType.CASE_CONFIRMED)
            _maybe_trigger_browser_follow_up(case)
    if next_path:
        return RedirectResponse(url=next_path, status_code=303)
    scoped = dashboard_service(request)
    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            **_base_context(request),
            "sections": scoped.all_sections(),
            "cases": scoped.repository.list_cases(),
            "evidence_index": scoped.repository.evidence,
        },
    )
