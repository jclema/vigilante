from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from itertools import count
from typing import TypeVar

try:
    from google.cloud import firestore
except ImportError:  # pragma: no cover - local fallback when cloud deps are not installed
    firestore = None

from app.config import settings
from app.models import (
    AlertEvent,
    AuthorizedDealer,
    BrowserRun,
    BrowserSession,
    DealerProfile,
    EvidenceArtifact,
    GbpConnection,
    GoogleReport,
    JobRun,
    Membership,
    NotificationDestination,
    Organization,
    ScanRun,
    ThreatCase,
    User,
)
from app.services import demo_data
from app.services.auth import hash_password


ModelT = TypeVar("ModelT")


class Repository(ABC):
    @property
    @abstractmethod
    def dealers(self) -> dict[str, AuthorizedDealer]:
        raise NotImplementedError

    @property
    @abstractmethod
    def profiles(self) -> dict[str, DealerProfile]:
        raise NotImplementedError

    @property
    @abstractmethod
    def evidence(self) -> dict[str, EvidenceArtifact]:
        raise NotImplementedError

    @property
    @abstractmethod
    def organizations(self) -> dict[str, Organization]:
        raise NotImplementedError

    @property
    @abstractmethod
    def users(self) -> dict[str, User]:
        raise NotImplementedError

    @property
    @abstractmethod
    def memberships(self) -> dict[str, Membership]:
        raise NotImplementedError

    @property
    @abstractmethod
    def gbp_connections(self) -> dict[str, GbpConnection]:
        raise NotImplementedError

    @property
    @abstractmethod
    def notification_destinations(self) -> dict[str, NotificationDestination]:
        raise NotImplementedError

    @property
    @abstractmethod
    def browser_sessions(self) -> dict[str, BrowserSession]:
        raise NotImplementedError

    @property
    @abstractmethod
    def browser_runs(self) -> dict[str, BrowserRun]:
        raise NotImplementedError

    @abstractmethod
    def seed(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def next_id(self, prefix: str) -> str:
        raise NotImplementedError

    @abstractmethod
    def import_whitelist(self, dealers: list[AuthorizedDealer]) -> list[AuthorizedDealer]:
        raise NotImplementedError

    @abstractmethod
    def import_profiles(self, profiles: list[DealerProfile]) -> list[DealerProfile]:
        raise NotImplementedError

    @abstractmethod
    def save_scan(self, scan: ScanRun) -> ScanRun:
        raise NotImplementedError

    @abstractmethod
    def save_job(self, job: JobRun) -> JobRun:
        raise NotImplementedError

    @abstractmethod
    def save_case(self, case: ThreatCase) -> ThreatCase:
        raise NotImplementedError

    @abstractmethod
    def save_evidence(self, artifact: EvidenceArtifact) -> EvidenceArtifact:
        raise NotImplementedError

    @abstractmethod
    def get_case(self, case_id: str) -> ThreatCase | None:
        raise NotImplementedError

    @abstractmethod
    def list_cases(self) -> list[ThreatCase]:
        raise NotImplementedError

    @abstractmethod
    def find_case_by_reference(self, source_reference_id: str) -> ThreatCase | None:
        raise NotImplementedError

    @abstractmethod
    def save_alert(self, event: AlertEvent) -> AlertEvent:
        raise NotImplementedError

    @abstractmethod
    def upsert_report(self, report: GoogleReport) -> GoogleReport:
        raise NotImplementedError

    @abstractmethod
    def get_report(self, case_id: str) -> GoogleReport | None:
        raise NotImplementedError

    @abstractmethod
    def list_evidence_for_case(self, case_id: str) -> list[EvidenceArtifact]:
        raise NotImplementedError

    @abstractmethod
    def list_jobs(self) -> list[JobRun]:
        raise NotImplementedError

    @abstractmethod
    def list_scans(self) -> list[ScanRun]:
        raise NotImplementedError

    @abstractmethod
    def save_organization(self, organization: Organization) -> Organization:
        raise NotImplementedError

    @abstractmethod
    def get_organization(self, organization_id: str) -> Organization | None:
        raise NotImplementedError

    @abstractmethod
    def list_organizations(self) -> list[Organization]:
        raise NotImplementedError

    @abstractmethod
    def save_user(self, user: User) -> User:
        raise NotImplementedError

    @abstractmethod
    def get_user(self, user_id: str) -> User | None:
        raise NotImplementedError

    @abstractmethod
    def find_user_by_email(self, email: str) -> User | None:
        raise NotImplementedError

    @abstractmethod
    def find_user_by_google_subject(self, google_subject: str) -> User | None:
        raise NotImplementedError

    @abstractmethod
    def list_users(self) -> list[User]:
        raise NotImplementedError

    @abstractmethod
    def save_membership(self, membership: Membership) -> Membership:
        raise NotImplementedError

    @abstractmethod
    def list_memberships_for_user(self, user_id: str) -> list[Membership]:
        raise NotImplementedError

    @abstractmethod
    def list_memberships_for_organization(self, organization_id: str) -> list[Membership]:
        raise NotImplementedError

    @abstractmethod
    def save_gbp_connection(self, connection: GbpConnection) -> GbpConnection:
        raise NotImplementedError

    @abstractmethod
    def get_gbp_connection(self, connection_id: str) -> GbpConnection | None:
        raise NotImplementedError

    @abstractmethod
    def list_gbp_connections(self, organization_id: str | None = None) -> list[GbpConnection]:
        raise NotImplementedError

    @abstractmethod
    def save_notification_destination(self, destination: NotificationDestination) -> NotificationDestination:
        raise NotImplementedError

    @abstractmethod
    def list_notification_destinations(self, organization_id: str | None = None) -> list[NotificationDestination]:
        raise NotImplementedError

    @abstractmethod
    def save_browser_session(self, session: BrowserSession) -> BrowserSession:
        raise NotImplementedError

    @abstractmethod
    def get_browser_session(self, organization_id: str) -> BrowserSession | None:
        raise NotImplementedError

    @abstractmethod
    def save_browser_run(self, run: BrowserRun) -> BrowserRun:
        raise NotImplementedError

    @abstractmethod
    def get_browser_run(self, run_id: str) -> BrowserRun | None:
        raise NotImplementedError

    @abstractmethod
    def list_browser_runs(self, case_id: str | None = None) -> list[BrowserRun]:
        raise NotImplementedError


@dataclass
class InMemoryRepository(Repository):
    _organizations: dict[str, Organization] = field(default_factory=dict)
    _users: dict[str, User] = field(default_factory=dict)
    _memberships: dict[str, Membership] = field(default_factory=dict)
    _gbp_connections: dict[str, GbpConnection] = field(default_factory=dict)
    _notification_destinations: dict[str, NotificationDestination] = field(default_factory=dict)
    _browser_sessions: dict[str, BrowserSession] = field(default_factory=dict)
    _browser_runs: dict[str, BrowserRun] = field(default_factory=dict)
    _dealers: dict[str, AuthorizedDealer] = field(default_factory=dict)
    _profiles: dict[str, DealerProfile] = field(default_factory=dict)
    _cases: dict[str, ThreatCase] = field(default_factory=dict)
    _evidence: dict[str, EvidenceArtifact] = field(default_factory=dict)
    _reports: dict[str, GoogleReport] = field(default_factory=dict)
    _alerts: dict[str, AlertEvent] = field(default_factory=dict)
    _scans: dict[str, ScanRun] = field(default_factory=dict)
    _jobs: dict[str, JobRun] = field(default_factory=dict)
    _counter: count = field(default_factory=lambda: count(1))

    @property
    def dealers(self) -> dict[str, AuthorizedDealer]:
        return self._dealers

    @property
    def profiles(self) -> dict[str, DealerProfile]:
        return self._profiles

    @property
    def evidence(self) -> dict[str, EvidenceArtifact]:
        return self._evidence

    @property
    def organizations(self) -> dict[str, Organization]:
        return self._organizations

    @property
    def users(self) -> dict[str, User]:
        return self._users

    @property
    def memberships(self) -> dict[str, Membership]:
        return self._memberships

    @property
    def gbp_connections(self) -> dict[str, GbpConnection]:
        return self._gbp_connections

    @property
    def notification_destinations(self) -> dict[str, NotificationDestination]:
        return self._notification_destinations

    @property
    def browser_sessions(self) -> dict[str, BrowserSession]:
        return self._browser_sessions

    @property
    def browser_runs(self) -> dict[str, BrowserRun]:
        return self._browser_runs

    def seed(self) -> None:
        if self._dealers:
            return
        for organization in demo_data.demo_organizations():
            self._organizations[organization.id] = organization
        for user in demo_data.demo_users(hash_password):
            self._users[user.id] = user
        for membership in demo_data.demo_memberships():
            self._memberships[membership.id] = membership
        for destination in demo_data.demo_notification_destinations():
            self._notification_destinations[destination.id] = destination
        for dealer in demo_data.demo_dealers():
            self._dealers[dealer.id] = dealer
        for profile in demo_data.demo_profiles():
            self._profiles[profile.id] = profile

    def next_id(self, prefix: str) -> str:
        return f"{prefix}-{next(self._counter)}"

    def import_whitelist(self, dealers: list[AuthorizedDealer]) -> list[AuthorizedDealer]:
        for dealer in dealers:
            self._dealers[dealer.id] = dealer
        return dealers

    def import_profiles(self, profiles: list[DealerProfile]) -> list[DealerProfile]:
        for profile in profiles:
            self._profiles[profile.id] = profile
        return profiles

    def save_scan(self, scan: ScanRun) -> ScanRun:
        self._scans[scan.id] = scan
        return scan

    def save_job(self, job: JobRun) -> JobRun:
        self._jobs[job.id] = job
        return job

    def save_case(self, case: ThreatCase) -> ThreatCase:
        case.updated_at = datetime.utcnow()
        self._cases[case.id] = case
        return case

    def save_evidence(self, artifact: EvidenceArtifact) -> EvidenceArtifact:
        self._evidence[artifact.id] = artifact
        case = self._cases[artifact.case_id]
        if artifact.id not in case.evidence_ids:
            case.evidence_ids.append(artifact.id)
        self._cases[artifact.case_id] = case
        return artifact

    def get_case(self, case_id: str) -> ThreatCase | None:
        return self._cases.get(case_id)

    def list_cases(self) -> list[ThreatCase]:
        return sorted(self._cases.values(), key=lambda item: item.created_at, reverse=True)

    def find_case_by_reference(self, source_reference_id: str) -> ThreatCase | None:
        for case in self._cases.values():
            if case.source_reference_id == source_reference_id:
                return case
        return None

    def save_alert(self, event: AlertEvent) -> AlertEvent:
        self._alerts[event.id] = event
        return event

    def upsert_report(self, report: GoogleReport) -> GoogleReport:
        report.updated_at = datetime.utcnow()
        self._reports[report.case_id] = report
        case = self._cases[report.case_id]
        case.google_report_status = report.status
        case.google_report_response = report.response_summary
        self._cases[case.id] = case
        return report

    def get_report(self, case_id: str) -> GoogleReport | None:
        return self._reports.get(case_id)

    def list_evidence_for_case(self, case_id: str) -> list[EvidenceArtifact]:
        return [artifact for artifact in self._evidence.values() if artifact.case_id == case_id]

    def list_jobs(self) -> list[JobRun]:
        return sorted(self._jobs.values(), key=lambda item: item.started_at, reverse=True)

    def list_scans(self) -> list[ScanRun]:
        return sorted(self._scans.values(), key=lambda item: item.started_at, reverse=True)

    def save_organization(self, organization: Organization) -> Organization:
        self._organizations[organization.id] = organization
        return organization

    def get_organization(self, organization_id: str) -> Organization | None:
        return self._organizations.get(organization_id)

    def list_organizations(self) -> list[Organization]:
        return sorted(self._organizations.values(), key=lambda item: item.created_at)

    def save_user(self, user: User) -> User:
        self._users[user.id] = user
        return user

    def get_user(self, user_id: str) -> User | None:
        return self._users.get(user_id)

    def find_user_by_email(self, email: str) -> User | None:
        normalized = email.strip().lower()
        for user in self._users.values():
            if user.email.lower() == normalized:
                return user
        return None

    def find_user_by_google_subject(self, google_subject: str) -> User | None:
        for user in self._users.values():
            if user.google_subject == google_subject:
                return user
        return None

    def list_users(self) -> list[User]:
        return sorted(self._users.values(), key=lambda item: item.created_at)

    def save_membership(self, membership: Membership) -> Membership:
        self._memberships[membership.id] = membership
        return membership

    def list_memberships_for_user(self, user_id: str) -> list[Membership]:
        return sorted(
            [item for item in self._memberships.values() if item.user_id == user_id],
            key=lambda item: item.created_at,
        )

    def list_memberships_for_organization(self, organization_id: str) -> list[Membership]:
        return sorted(
            [item for item in self._memberships.values() if item.organization_id == organization_id],
            key=lambda item: item.created_at,
        )

    def save_gbp_connection(self, connection: GbpConnection) -> GbpConnection:
        self._gbp_connections[connection.id] = connection
        return connection

    def get_gbp_connection(self, connection_id: str) -> GbpConnection | None:
        return self._gbp_connections.get(connection_id)

    def list_gbp_connections(self, organization_id: str | None = None) -> list[GbpConnection]:
        items = self._gbp_connections.values()
        if organization_id:
            items = [item for item in items if item.organization_id == organization_id]
        return sorted(items, key=lambda item: item.created_at, reverse=True)

    def save_notification_destination(self, destination: NotificationDestination) -> NotificationDestination:
        self._notification_destinations[destination.id] = destination
        return destination

    def list_notification_destinations(self, organization_id: str | None = None) -> list[NotificationDestination]:
        items = self._notification_destinations.values()
        if organization_id:
            items = [item for item in items if item.organization_id == organization_id]
        return sorted(items, key=lambda item: item.created_at, reverse=True)

    def save_browser_session(self, session: BrowserSession) -> BrowserSession:
        session.updated_at = datetime.utcnow()
        self._browser_sessions[session.organization_id] = session
        return session

    def get_browser_session(self, organization_id: str) -> BrowserSession | None:
        return self._browser_sessions.get(organization_id)

    def save_browser_run(self, run: BrowserRun) -> BrowserRun:
        self._browser_runs[run.id] = run
        return run

    def get_browser_run(self, run_id: str) -> BrowserRun | None:
        return self._browser_runs.get(run_id)

    def list_browser_runs(self, case_id: str | None = None) -> list[BrowserRun]:
        items = self._browser_runs.values()
        if case_id:
            items = [item for item in items if item.case_id == case_id]
        return sorted(items, key=lambda item: item.started_at, reverse=True)


class FirestoreRepository(Repository):
    def __init__(self, project_id: str) -> None:
        if firestore is None:
            raise RuntimeError("google-cloud-firestore is required for STORAGE_BACKEND=firestore")
        self.client = firestore.Client(project=project_id)
        self.collections = {
            "organizations": "organizations",
            "users": "users",
            "memberships": "memberships",
            "gbp_connections": "gbp_connections",
            "notification_destinations": "notification_destinations",
            "browser_sessions": "browser_sessions",
            "browser_runs": "browser_runs",
            "dealers": "authorized_dealers",
            "profiles": "dealer_profiles",
            "cases": "cases",
            "evidence": "evidence_artifacts",
            "reports": "google_reports",
            "alerts": "alerts",
            "scans": "scan_runs",
            "jobs": "job_runs",
            "counters": "counters",
        }

    @property
    def dealers(self) -> dict[str, AuthorizedDealer]:
        return self._load_collection(self.collections["dealers"], AuthorizedDealer)

    @property
    def profiles(self) -> dict[str, DealerProfile]:
        return self._load_collection(self.collections["profiles"], DealerProfile)

    @property
    def evidence(self) -> dict[str, EvidenceArtifact]:
        return self._load_collection(self.collections["evidence"], EvidenceArtifact)

    @property
    def organizations(self) -> dict[str, Organization]:
        return self._load_collection(self.collections["organizations"], Organization)

    @property
    def users(self) -> dict[str, User]:
        return self._load_collection(self.collections["users"], User)

    @property
    def memberships(self) -> dict[str, Membership]:
        return self._load_collection(self.collections["memberships"], Membership)

    @property
    def gbp_connections(self) -> dict[str, GbpConnection]:
        return self._load_collection(self.collections["gbp_connections"], GbpConnection)

    @property
    def notification_destinations(self) -> dict[str, NotificationDestination]:
        return self._load_collection(self.collections["notification_destinations"], NotificationDestination)

    @property
    def browser_sessions(self) -> dict[str, BrowserSession]:
        return self._load_collection(self.collections["browser_sessions"], BrowserSession)

    @property
    def browser_runs(self) -> dict[str, BrowserRun]:
        return self._load_collection(self.collections["browser_runs"], BrowserRun)

    def _collection(self, name: str):
        return self.client.collection(name)

    def _load_collection(self, name: str, model_cls: type[ModelT]) -> dict[str, ModelT]:
        docs = self._collection(name).stream()
        return {doc.id: model_cls.model_validate(doc.to_dict()) for doc in docs}

    def _write(self, collection_name: str, doc_id: str, model) -> None:
        self._collection(collection_name).document(doc_id).set(model.model_dump(mode="json"))

    def seed(self) -> None:
        if self.dealers:
            return
        for organization in demo_data.demo_organizations():
            self.save_organization(organization)
        for user in demo_data.demo_users(hash_password):
            self.save_user(user)
        for membership in demo_data.demo_memberships():
            self.save_membership(membership)
        for destination in demo_data.demo_notification_destinations():
            self.save_notification_destination(destination)
        self.import_whitelist(demo_data.demo_dealers())
        self.import_profiles(demo_data.demo_profiles())

    def next_id(self, prefix: str) -> str:
        counter_ref = self._collection(self.collections["counters"]).document(prefix)

        @firestore.transactional
        def increment_counter(transaction):
            snapshot = counter_ref.get(transaction=transaction)
            current = 0
            if snapshot.exists:
                current = int(snapshot.to_dict().get("value", 0))
            next_value = current + 1
            transaction.set(counter_ref, {"value": next_value})
            return next_value

        value = increment_counter(self.client.transaction())
        return f"{prefix}-{value}"

    def import_whitelist(self, dealers: list[AuthorizedDealer]) -> list[AuthorizedDealer]:
        for dealer in dealers:
            self._write(self.collections["dealers"], dealer.id, dealer)
        return dealers

    def import_profiles(self, profiles: list[DealerProfile]) -> list[DealerProfile]:
        for profile in profiles:
            self._write(self.collections["profiles"], profile.id, profile)
        return profiles

    def save_scan(self, scan: ScanRun) -> ScanRun:
        self._write(self.collections["scans"], scan.id, scan)
        return scan

    def save_job(self, job: JobRun) -> JobRun:
        self._write(self.collections["jobs"], job.id, job)
        return job

    def save_case(self, case: ThreatCase) -> ThreatCase:
        case.updated_at = datetime.utcnow()
        self._write(self.collections["cases"], case.id, case)
        return case

    def save_evidence(self, artifact: EvidenceArtifact) -> EvidenceArtifact:
        self._write(self.collections["evidence"], artifact.id, artifact)
        case = self.get_case(artifact.case_id)
        if case and artifact.id not in case.evidence_ids:
            case.evidence_ids.append(artifact.id)
            self.save_case(case)
        return artifact

    def get_case(self, case_id: str) -> ThreatCase | None:
        snapshot = self._collection(self.collections["cases"]).document(case_id).get()
        if not snapshot.exists:
            return None
        return ThreatCase.model_validate(snapshot.to_dict())

    def list_cases(self) -> list[ThreatCase]:
        docs = self._collection(self.collections["cases"]).stream()
        cases = [ThreatCase.model_validate(doc.to_dict()) for doc in docs]
        return sorted(cases, key=lambda item: item.created_at, reverse=True)

    def find_case_by_reference(self, source_reference_id: str) -> ThreatCase | None:
        query = self._collection(self.collections["cases"]).where(
            filter=firestore.FieldFilter("source_reference_id", "==", source_reference_id)
        )
        docs = list(query.limit(1).stream())
        if not docs:
            return None
        return ThreatCase.model_validate(docs[0].to_dict())

    def save_alert(self, event: AlertEvent) -> AlertEvent:
        self._write(self.collections["alerts"], event.id, event)
        return event

    def upsert_report(self, report: GoogleReport) -> GoogleReport:
        report.updated_at = datetime.utcnow()
        self._write(self.collections["reports"], report.case_id, report)
        case = self.get_case(report.case_id)
        if case:
            case.google_report_status = report.status
            case.google_report_response = report.response_summary
            self.save_case(case)
        return report

    def get_report(self, case_id: str) -> GoogleReport | None:
        snapshot = self._collection(self.collections["reports"]).document(case_id).get()
        if not snapshot.exists:
            return None
        return GoogleReport.model_validate(snapshot.to_dict())

    def list_evidence_for_case(self, case_id: str) -> list[EvidenceArtifact]:
        query = self._collection(self.collections["evidence"]).where(
            filter=firestore.FieldFilter("case_id", "==", case_id)
        )
        return [EvidenceArtifact.model_validate(doc.to_dict()) for doc in query.stream()]

    def list_jobs(self) -> list[JobRun]:
        docs = self._collection(self.collections["jobs"]).stream()
        jobs = [JobRun.model_validate(doc.to_dict()) for doc in docs]
        return sorted(jobs, key=lambda item: item.started_at, reverse=True)

    def list_scans(self) -> list[ScanRun]:
        docs = self._collection(self.collections["scans"]).stream()
        scans = [ScanRun.model_validate(doc.to_dict()) for doc in docs]
        return sorted(scans, key=lambda item: item.started_at, reverse=True)

    def save_organization(self, organization: Organization) -> Organization:
        self._write(self.collections["organizations"], organization.id, organization)
        return organization

    def get_organization(self, organization_id: str) -> Organization | None:
        snapshot = self._collection(self.collections["organizations"]).document(organization_id).get()
        if not snapshot.exists:
            return None
        return Organization.model_validate(snapshot.to_dict())

    def list_organizations(self) -> list[Organization]:
        docs = self._collection(self.collections["organizations"]).stream()
        items = [Organization.model_validate(doc.to_dict()) for doc in docs]
        return sorted(items, key=lambda item: item.created_at)

    def save_user(self, user: User) -> User:
        self._write(self.collections["users"], user.id, user)
        return user

    def get_user(self, user_id: str) -> User | None:
        snapshot = self._collection(self.collections["users"]).document(user_id).get()
        if not snapshot.exists:
            return None
        return User.model_validate(snapshot.to_dict())

    def find_user_by_email(self, email: str) -> User | None:
        query = self._collection(self.collections["users"]).where(
            filter=firestore.FieldFilter("email", "==", email.strip().lower())
        )
        docs = list(query.limit(1).stream())
        if not docs:
            return None
        return User.model_validate(docs[0].to_dict())

    def find_user_by_google_subject(self, google_subject: str) -> User | None:
        query = self._collection(self.collections["users"]).where(
            filter=firestore.FieldFilter("google_subject", "==", google_subject)
        )
        docs = list(query.limit(1).stream())
        if not docs:
            return None
        return User.model_validate(docs[0].to_dict())

    def list_users(self) -> list[User]:
        docs = self._collection(self.collections["users"]).stream()
        items = [User.model_validate(doc.to_dict()) for doc in docs]
        return sorted(items, key=lambda item: item.created_at)

    def save_membership(self, membership: Membership) -> Membership:
        self._write(self.collections["memberships"], membership.id, membership)
        return membership

    def list_memberships_for_user(self, user_id: str) -> list[Membership]:
        query = self._collection(self.collections["memberships"]).where(
            filter=firestore.FieldFilter("user_id", "==", user_id)
        )
        items = [Membership.model_validate(doc.to_dict()) for doc in query.stream()]
        return sorted(items, key=lambda item: item.created_at)

    def list_memberships_for_organization(self, organization_id: str) -> list[Membership]:
        query = self._collection(self.collections["memberships"]).where(
            filter=firestore.FieldFilter("organization_id", "==", organization_id)
        )
        items = [Membership.model_validate(doc.to_dict()) for doc in query.stream()]
        return sorted(items, key=lambda item: item.created_at)

    def save_gbp_connection(self, connection: GbpConnection) -> GbpConnection:
        self._write(self.collections["gbp_connections"], connection.id, connection)
        return connection

    def get_gbp_connection(self, connection_id: str) -> GbpConnection | None:
        snapshot = self._collection(self.collections["gbp_connections"]).document(connection_id).get()
        if not snapshot.exists:
            return None
        return GbpConnection.model_validate(snapshot.to_dict())

    def list_gbp_connections(self, organization_id: str | None = None) -> list[GbpConnection]:
        if organization_id:
            query = self._collection(self.collections["gbp_connections"]).where(
                filter=firestore.FieldFilter("organization_id", "==", organization_id)
            )
            items = [GbpConnection.model_validate(doc.to_dict()) for doc in query.stream()]
        else:
            items = [
                GbpConnection.model_validate(doc.to_dict())
                for doc in self._collection(self.collections["gbp_connections"]).stream()
            ]
        return sorted(items, key=lambda item: item.created_at, reverse=True)

    def save_notification_destination(self, destination: NotificationDestination) -> NotificationDestination:
        self._write(self.collections["notification_destinations"], destination.id, destination)
        return destination

    def list_notification_destinations(self, organization_id: str | None = None) -> list[NotificationDestination]:
        if organization_id:
            query = self._collection(self.collections["notification_destinations"]).where(
                filter=firestore.FieldFilter("organization_id", "==", organization_id)
            )
            items = [NotificationDestination.model_validate(doc.to_dict()) for doc in query.stream()]
        else:
            items = [
                NotificationDestination.model_validate(doc.to_dict())
                for doc in self._collection(self.collections["notification_destinations"]).stream()
            ]
        return sorted(items, key=lambda item: item.created_at, reverse=True)

    def save_browser_session(self, session: BrowserSession) -> BrowserSession:
        session.updated_at = datetime.utcnow()
        self._write(self.collections["browser_sessions"], session.organization_id, session)
        return session

    def get_browser_session(self, organization_id: str) -> BrowserSession | None:
        snapshot = self._collection(self.collections["browser_sessions"]).document(organization_id).get()
        if not snapshot.exists:
            return None
        return BrowserSession.model_validate(snapshot.to_dict())

    def save_browser_run(self, run: BrowserRun) -> BrowserRun:
        self._write(self.collections["browser_runs"], run.id, run)
        return run

    def get_browser_run(self, run_id: str) -> BrowserRun | None:
        snapshot = self._collection(self.collections["browser_runs"]).document(run_id).get()
        if not snapshot.exists:
            return None
        return BrowserRun.model_validate(snapshot.to_dict())

    def list_browser_runs(self, case_id: str | None = None) -> list[BrowserRun]:
        if case_id:
            query = self._collection(self.collections["browser_runs"]).where(
                filter=firestore.FieldFilter("case_id", "==", case_id)
            )
            items = [BrowserRun.model_validate(doc.to_dict()) for doc in query.stream()]
        else:
            items = [
                BrowserRun.model_validate(doc.to_dict())
                for doc in self._collection(self.collections["browser_runs"]).stream()
            ]
        return sorted(items, key=lambda item: item.started_at, reverse=True)


def get_repository() -> Repository:
    if settings.storage_backend == "firestore":
        return FirestoreRepository(settings.google_cloud_project)
    return InMemoryRepository()


repository: Repository = get_repository()
