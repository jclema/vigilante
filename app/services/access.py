from __future__ import annotations

from dataclasses import dataclass

from app.models import AuthorizedDealer, DealerProfile, EvidenceArtifact, ThreatCase
from app.models import BrowserRun, BrowserSession
from app.services.auth import ActorContext
from app.store import Repository


@dataclass(slots=True)
class ScopedRepositoryView:
    repository: Repository
    actor: ActorContext | None
    _dealers_cache: dict[str, AuthorizedDealer] | None = None
    _profiles_cache: dict[str, DealerProfile] | None = None
    _evidence_cache: dict[str, EvidenceArtifact] | None = None
    _cases_cache: list[ThreatCase] | None = None
    _jobs_cache: list | None = None
    _scans_cache: list | None = None
    _visible_org_ids_cache: set[str] | None | object = None

    @property
    def dealers(self) -> dict[str, AuthorizedDealer]:
        if self._dealers_cache is None:
            self._dealers_cache = {
                dealer_id: dealer
                for dealer_id, dealer in self.repository.dealers.items()
                if self._can_see_organization(dealer.organization_id)
            }
        return self._dealers_cache

    @property
    def profiles(self) -> dict[str, DealerProfile]:
        if self._profiles_cache is None:
            self._profiles_cache = {
                profile_id: profile
                for profile_id, profile in self.repository.profiles.items()
                if self._can_see_organization(profile.organization_id or self._dealer_org_id(profile.dealer_id))
            }
        return self._profiles_cache

    @property
    def evidence(self) -> dict[str, EvidenceArtifact]:
        if self._evidence_cache is None:
            visible_case_ids = {case.id for case in self.list_cases()}
            self._evidence_cache = {
                evidence_id: artifact
                for evidence_id, artifact in self.repository.evidence.items()
                if artifact.case_id in visible_case_ids
            }
        return self._evidence_cache

    def list_cases(self) -> list[ThreatCase]:
        if self._cases_cache is None:
            cases = self.repository.list_cases()
            self._cases_cache = [case for case in cases if self._can_see_case(case)]
        return self._cases_cache

    def get_case(self, case_id: str) -> ThreatCase | None:
        for case in self.list_cases():
            if case.id == case_id:
                return case
        return None

    def find_case_by_reference(self, source_reference_id: str) -> ThreatCase | None:
        for case in self.list_cases():
            if case.source_reference_id == source_reference_id:
                return case
        return None

    def list_evidence_for_case(self, case_id: str) -> list[EvidenceArtifact]:
        if not self.get_case(case_id):
            return []
        return self.repository.list_evidence_for_case(case_id)

    def get_report(self, case_id: str):
        if not self.get_case(case_id):
            return None
        return self.repository.get_report(case_id)

    def list_jobs(self):
        if self._jobs_cache is None:
            jobs = self.repository.list_jobs()
            if self.actor and not self.actor.can_view_network:
                visible_ids = self.actor.visible_organization_ids() or set()
                jobs = [job for job in jobs if job.organization_id in visible_ids or job.organization_id is None]
            self._jobs_cache = jobs
        return self._jobs_cache

    def list_scans(self):
        if self._scans_cache is None:
            self._scans_cache = self.repository.list_scans()
        return self._scans_cache

    def list_browser_runs(self, case_id: str | None = None) -> list[BrowserRun]:
        if case_id and not self.get_case(case_id):
            return []
        runs = self.repository.list_browser_runs(case_id=case_id)
        if self.actor and not self.actor.can_view_network:
            visible_ids = self.actor.visible_organization_ids() or set()
            runs = [run for run in runs if run.organization_id in visible_ids or run.organization_id is None]
        return runs

    def get_browser_session(self, organization_id: str) -> BrowserSession | None:
        if not self._can_see_organization(organization_id):
            return None
        return self.repository.get_browser_session(organization_id)

    def _can_see_case(self, case: ThreatCase) -> bool:
        return self._can_see_organization(case.organization_id or self._dealer_org_id(case.dealer_id))

    def _dealer_org_id(self, dealer_id: str) -> str | None:
        dealer = self.repository.dealers.get(dealer_id)
        return dealer.organization_id if dealer else None

    def _can_see_organization(self, organization_id: str | None) -> bool:
        if self.actor is None:
            return True
        visible_ids = self._visible_organization_ids()
        if visible_ids is None:
            return True
        if organization_id is None:
            return False
        return organization_id in visible_ids

    def _visible_organization_ids(self) -> set[str] | None:
        if self._visible_org_ids_cache is not None:
            return self._visible_org_ids_cache

        visible_ids = self.actor.visible_organization_ids() if self.actor else None
        if visible_ids is None or not self.actor or not self.actor.active_organization_id:
            self._visible_org_ids_cache = visible_ids
            return visible_ids

        active_org = self.repository.get_organization(self.actor.active_organization_id)
        if active_org and getattr(active_org, "organization_type", None) == "network":
            expanded_ids = {active_org.id}
            expanded_ids.update(
                organization.id
                for organization in self.repository.list_organizations()
                if getattr(organization, "organization_type", None) == "dealer"
            )
            self._visible_org_ids_cache = expanded_ids
            return expanded_ids

        self._visible_org_ids_cache = visible_ids
        return visible_ids
