from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class MonitoringMode(str, Enum):
    GBP_PUSH = "gbp_push"
    PUBLIC_SCAN = "public_scan"


class SourceType(str, Enum):
    PLACE_CLONE = "place_clone"
    REVIEW_PHOTO = "review_photo"
    OFFICIAL_PROFILE_UPDATE = "official_profile_update"


class CaseStatus(str, Enum):
    NEW = "new"
    TRIAGED = "triaged"
    CONFIRMED = "confirmed"
    DISMISSED = "dismissed"
    REPORTED = "reported"


class RiskBucket(str, Enum):
    CLONE_RISK = "clone_risk"
    HIGH_RISK_WATCHLIST = "high_risk_watchlist"


class JobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    DEGRADED = "degraded"


class GoogleReportStatus(str, Enum):
    NOT_STARTED = "not_started"
    DRAFTED = "drafted"
    SUBMITTED = "submitted"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"


class BrowserExecutionMode(str, Enum):
    MANUAL_PREPARE = "manual_prepare"
    SEMI_AUTO_SUBMIT = "semi_auto_submit"
    AUTO_SUBMIT = "auto_submit"


class BrowserFlowType(str, Enum):
    REPORT_PHOTO_DESKTOP = "report_photo_desktop"
    REPORT_PHOTO_MOBILE = "report_photo_mobile"
    REPORT_CONTRIBUTOR_PROFILE = "report_contributor_profile"


class BrowserRunStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    PREPARED = "prepared"
    SUBMITTED = "submitted"
    FAILED = "failed"
    NEEDS_REAUTH = "needs_reauth"
    BLOCKED_BY_GOOGLE = "blocked_by_google"


class BrowserSessionStatus(str, Enum):
    PENDING = "pending"
    ACTIVE = "active"
    EXPIRED = "expired"


class OrganizationType(str, Enum):
    PLATFORM = "platform"
    NETWORK = "network"
    DEALER = "dealer"


class UserRole(str, Enum):
    SUPER_ADMIN = "super_admin"
    YAMAHA_ADMIN = "yamaha_admin"
    DEALER_ADMIN = "dealer_admin"
    DEALER_MEMBER = "dealer_member"


class ConnectionStatus(str, Enum):
    PENDING = "pending"
    CONNECTED = "connected"
    ERROR = "error"
    DISCONNECTED = "disconnected"


class NotificationChannel(str, Enum):
    EMAIL = "email"
    WEBHOOK = "webhook"


class NotificationEventType(str, Enum):
    NEW_ALERT = "new_alert"
    CASE_CONFIRMED = "case_confirmed"
    CASE_READY_FOR_GOOGLE = "case_ready_for_google"
    STATUS_CHANGED = "status_changed"


class DeliveryStatus(str, Enum):
    PENDING = "pending"
    SENT = "sent"
    SIMULATED = "simulated"
    FAILED = "failed"


class Organization(BaseModel):
    id: str
    name: str
    organization_type: OrganizationType
    is_active: bool = True
    created_at: datetime = Field(default_factory=utc_now)


class User(BaseModel):
    id: str
    email: str
    full_name: str
    password_hash: str | None = None
    google_subject: str | None = None
    is_active: bool = True
    created_at: datetime = Field(default_factory=utc_now)


class Membership(BaseModel):
    id: str
    user_id: str
    organization_id: str
    role: UserRole
    created_at: datetime = Field(default_factory=utc_now)


class GbpConnection(BaseModel):
    id: str
    organization_id: str
    provider_account_id: str
    provider_email: str | None = None
    gbp_account_name: str | None = None
    encrypted_refresh_token: str | None = None
    scopes: list[str] = Field(default_factory=list)
    selected_profile_ids: list[str] = Field(default_factory=list)
    available_locations: list[dict[str, str]] = Field(default_factory=list)
    api_access_case_id: str | None = None
    api_access_status: str | None = None
    status: ConnectionStatus = ConnectionStatus.PENDING
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    last_sync_at: datetime | None = None
    last_locations_sync_at: datetime | None = None
    last_error_at: datetime | None = None
    last_error: str | None = None


class NotificationDestination(BaseModel):
    id: str
    organization_id: str
    channel: NotificationChannel
    target: str
    subscribed_events: list[NotificationEventType] = Field(default_factory=list)
    enabled: bool = True
    created_at: datetime = Field(default_factory=utc_now)


class AuthorizedDealer(BaseModel):
    id: str
    organization_id: str | None = None
    name: str
    city: str
    address: str
    phone_numbers: list[str]
    latitude: float | None = None
    longitude: float | None = None
    influence_label: str | None = None
    influence_radius_km: float | None = None


class DealerProfile(BaseModel):
    id: str
    dealer_id: str
    organization_id: str | None = None
    name: str
    google_place_id: str | None = None
    gbp_location_id: str | None = None
    monitoring_mode: MonitoringMode
    enabled: bool = True


class ObservedPlace(BaseModel):
    id: str
    source_type: SourceType = SourceType.PLACE_CLONE
    place_id: str
    name: str
    address: str
    phone_number: str | None = None
    category: str | None = None
    latitude: float
    longitude: float
    source_query: str
    query_rank: int | None = None
    rating: float | None = None
    user_rating_count: int | None = None
    business_status: str | None = None
    first_seen_at: datetime | None = None
    observed_at: datetime = Field(default_factory=utc_now)
    raw_payload: dict[str, Any] = Field(default_factory=dict)


class ObservedAsset(BaseModel):
    id: str
    profile_id: str
    organization_id: str | None = None
    source_type: SourceType
    image_url: str | None = None
    external_media_id: str | None = None
    gbp_location_id: str | None = None
    source_page_url: str | None = None
    google_maps_uri: str | None = None
    thumbnail_url: str | None = None
    source_url: str | None = None
    captured_image_url: str | None = None
    evidence_image_path: str | None = None
    review_id: str | None = None
    ingestion_mode: str | None = None
    media_hash: str | None = None
    download_status: str | None = None
    review_text: str | None = None
    extracted_text: str | None = None
    observed_at: datetime = Field(default_factory=utc_now)
    raw_payload: dict[str, Any] = Field(default_factory=dict)


class EvidenceArtifact(BaseModel):
    id: str
    case_id: str
    artifact_type: str
    label: str
    content: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)


class GoogleReport(BaseModel):
    id: str
    case_id: str
    status: GoogleReportStatus = GoogleReportStatus.NOT_STARTED
    report_url: str | None = None
    response_summary: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class AlertEvent(BaseModel):
    id: str
    case_id: str
    organization_id: str | None = None
    channel: str
    message: str
    delivery_status: DeliveryStatus = DeliveryStatus.PENDING
    destination: str | None = None
    sent_at: datetime = Field(default_factory=utc_now)


class ScanRun(BaseModel):
    id: str
    query: str
    started_at: datetime = Field(default_factory=utc_now)
    finished_at: datetime | None = None
    threats_found: int = 0
    estimated_api_cost_usd: float = 0.0
    notes: str | None = None


class JobRun(BaseModel):
    id: str
    job_type: str
    organization_id: str | None = None
    job_status: JobStatus
    started_at: datetime = Field(default_factory=utc_now)
    finished_at: datetime | None = None
    estimated_api_cost_usd: float = 0.0
    detail: str | None = None


class BrowserSession(BaseModel):
    id: str
    organization_id: str
    auth_user_email: str | None = None
    encrypted_session_state: str | None = None
    status: BrowserSessionStatus = BrowserSessionStatus.PENDING
    last_refreshed_at: datetime | None = None
    last_error: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class BrowserRun(BaseModel):
    id: str
    case_id: str
    organization_id: str | None = None
    profile_id: str | None = None
    target_type: str
    target_url: str | None = None
    target_fingerprint: str | None = None
    flow_type: BrowserFlowType
    execution_mode: BrowserExecutionMode
    status: BrowserRunStatus = BrowserRunStatus.QUEUED
    started_at: datetime = Field(default_factory=utc_now)
    finished_at: datetime | None = None
    error_code: str | None = None
    error_detail: str | None = None
    screenshots: list[str] = Field(default_factory=list)
    dom_hints: dict[str, Any] = Field(default_factory=dict)
    audit_log: list[dict[str, Any]] = Field(default_factory=list)


class ThreatCase(BaseModel):
    id: str
    title: str
    dealer_id: str
    organization_id: str | None = None
    dealer_name: str
    city: str
    monitoring_mode: MonitoringMode
    source_type: SourceType
    status: CaseStatus = CaseStatus.NEW
    risk_bucket: RiskBucket = RiskBucket.CLONE_RISK
    risk_score: int = 0
    risk_reasons: list[str] = Field(default_factory=list)
    summary: str
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    location_label: str
    google_report_status: GoogleReportStatus = GoogleReportStatus.NOT_STARTED
    google_report_response: str | None = None
    browser_execution_mode: BrowserExecutionMode | None = None
    browser_status: BrowserRunStatus | None = None
    browser_flow_type: BrowserFlowType | None = None
    browser_last_run_at: datetime | None = None
    browser_last_submitted_at: datetime | None = None
    browser_last_target_fingerprint: str | None = None
    eligible_for_auto_submit: bool = False
    browser_last_error: str | None = None
    source_reference_id: str | None = None
    evidence_ids: list[str] = Field(default_factory=list)


class DashboardBlock(BaseModel):
    label: str
    value: str
    context: str
