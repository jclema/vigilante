from __future__ import annotations

import hashlib
from dataclasses import asdict
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Protocol

from app.config import settings
from app.models import (
    BrowserExecutionMode,
    BrowserFlowType,
    BrowserRun,
    BrowserRunStatus,
    BrowserSession,
    BrowserSessionStatus,
    EvidenceArtifact,
    SourceType,
    ThreatCase,
)
from app.services.auth import encrypt_secret
from app.store import Repository


@dataclass(slots=True)
class BrowserTarget:
    target_type: str
    target_url: str
    target_fingerprint: str
    flow_type: BrowserFlowType
    contributor_profile_url: str | None = None


@dataclass(slots=True)
class BrowserEligibility:
    eligible: bool
    reasons: list[str]
    suspicious_phone: str | None = None
    target: BrowserTarget | None = None


@dataclass(slots=True)
class BrowserExecutionResult:
    status: BrowserRunStatus
    screenshots: list[str]
    dom_hints: dict[str, object]
    audit_log: list[dict[str, object]]
    error_code: str | None = None
    error_detail: str | None = None


class BrowserExecutor(Protocol):
    def submit(
        self,
        *,
        run: BrowserRun,
        case: ThreatCase,
        target: BrowserTarget,
        session: BrowserSession,
    ) -> BrowserExecutionResult:
        ...


class PlaywrightBrowserExecutor:
    def submit(
        self,
        *,
        run: BrowserRun,
        case: ThreatCase,
        target: BrowserTarget,
        session: BrowserSession,
    ) -> BrowserExecutionResult:
        if not settings.enable_browser_enforcement:
            return BrowserExecutionResult(
                status=BrowserRunStatus.FAILED,
                screenshots=[],
                dom_hints={"execution_mode": "disabled"},
                audit_log=[{"step": "browser_runtime_disabled", "at": datetime.now(UTC).isoformat()}],
                error_code="browser_runtime_disabled",
                error_detail="El runtime de browser enforcement no está habilitado en este entorno.",
            )
        try:
            import playwright  # type: ignore  # pragma: no cover
        except Exception:
            return BrowserExecutionResult(
                status=BrowserRunStatus.FAILED,
                screenshots=[],
                dom_hints={"execution_mode": "playwright_missing"},
                audit_log=[{"step": "playwright_missing", "at": datetime.now(UTC).isoformat()}],
                error_code="playwright_missing",
                error_detail="Playwright no está instalado en el servicio principal. Usa el worker/browser job.",
            )
        return BrowserExecutionResult(
            status=BrowserRunStatus.FAILED,
            screenshots=[],
            dom_hints={"execution_mode": "worker_required", "playwright_module": str(playwright)},
            audit_log=[{"step": "worker_required", "at": datetime.now(UTC).isoformat()}],
            error_code="worker_required",
            error_detail="La ejecución real debe correr desde el worker/browser container con Playwright.",
        )


class BrowserEnforcementService:
    def __init__(self, repository: Repository, executor: BrowserExecutor | None = None) -> None:
        self.repository = repository
        self.executor = executor or PlaywrightBrowserExecutor()

    def refresh_session(
        self,
        *,
        organization_id: str,
        auth_user_email: str | None,
        session_state: str | None = None,
    ) -> BrowserSession:
        session = self.repository.get_browser_session(organization_id) or BrowserSession(
            id=self.repository.next_id("browser-session"),
            organization_id=organization_id,
        )
        session.auth_user_email = auth_user_email
        session.encrypted_session_state = encrypt_secret(session_state) if session_state else session.encrypted_session_state
        session.status = BrowserSessionStatus.ACTIVE
        session.last_refreshed_at = datetime.now(UTC)
        session.last_error = None
        return self.repository.save_browser_session(session)

    def get_case_browser_state(self, case_id: str) -> dict[str, object]:
        case = self.repository.get_case(case_id)
        if not case:
            raise ValueError("Caso no encontrado")
        eligibility = self.evaluate_case(case)
        session = self.repository.get_browser_session(case.organization_id or "")
        return {
            "case": case,
            "eligibility": {
                "eligible": eligibility.eligible,
                "reasons": eligibility.reasons,
                "suspicious_phone": eligibility.suspicious_phone,
                "target": asdict(eligibility.target) if eligibility.target else None,
            },
            "session": session,
            "runs": self.repository.list_browser_runs(case_id=case.id),
        }

    def prepare_case(self, case_id: str) -> BrowserRun:
        case = self._get_case(case_id)
        eligibility = self.evaluate_case(case)
        if not eligibility.target:
            raise ValueError("No se pudo resolver un target denunciable para este caso.")
        existing = self._latest_run_for_target(case.id, eligibility.target.target_fingerprint)
        if existing and existing.status in {BrowserRunStatus.PREPARED, BrowserRunStatus.SUBMITTED, BrowserRunStatus.RUNNING}:
            return existing
        run = BrowserRun(
            id=self.repository.next_id("browser-run"),
            case_id=case.id,
            organization_id=case.organization_id,
            profile_id=self._profile_id_for_case(case),
            target_type=eligibility.target.target_type,
            target_url=eligibility.target.target_url,
            target_fingerprint=eligibility.target.target_fingerprint,
            flow_type=eligibility.target.flow_type,
            execution_mode=BrowserExecutionMode.MANUAL_PREPARE,
            status=BrowserRunStatus.PREPARED,
            dom_hints={"contributor_profile_url": eligibility.target.contributor_profile_url},
            audit_log=[
                {"step": "prepared", "at": datetime.now(UTC).isoformat(), "reasons": eligibility.reasons},
            ],
        )
        self.repository.save_browser_run(run)
        self._persist_run_evidence(case, run, eligibility=eligibility, phase="prepared")
        self._apply_browser_state(
            case,
            status=BrowserRunStatus.PREPARED,
            execution_mode=BrowserExecutionMode.MANUAL_PREPARE,
            flow_type=eligibility.target.flow_type,
            target_fingerprint=eligibility.target.target_fingerprint,
            error=None,
        )
        return run

    def approve_case(self, case_id: str) -> BrowserRun:
        return self.submit_case(case_id, execution_mode=BrowserExecutionMode.SEMI_AUTO_SUBMIT)

    def run_auto(self, case_id: str) -> BrowserRun:
        return self.submit_case(case_id, execution_mode=BrowserExecutionMode.AUTO_SUBMIT)

    def submit_case(self, case_id: str, *, execution_mode: BrowserExecutionMode) -> BrowserRun:
        case = self._get_case(case_id)
        eligibility = self.evaluate_case(case)
        if execution_mode == BrowserExecutionMode.AUTO_SUBMIT and not eligibility.eligible:
            raise ValueError("El caso no cumple las reglas de auto-submit.")
        if not eligibility.target:
            raise ValueError("No se pudo resolver un target denunciable para este caso.")
        existing = self._latest_run_for_target(case.id, eligibility.target.target_fingerprint)
        if existing and existing.status == BrowserRunStatus.SUBMITTED:
            return existing
        self._ensure_not_duplicate(case, eligibility.target.target_fingerprint)
        session = self._require_active_session(case.organization_id)
        run = BrowserRun(
            id=self.repository.next_id("browser-run"),
            case_id=case.id,
            organization_id=case.organization_id,
            profile_id=self._profile_id_for_case(case),
            target_type=eligibility.target.target_type,
            target_url=eligibility.target.target_url,
            target_fingerprint=eligibility.target.target_fingerprint,
            flow_type=eligibility.target.flow_type,
            execution_mode=execution_mode,
            status=BrowserRunStatus.RUNNING,
            dom_hints={"contributor_profile_url": eligibility.target.contributor_profile_url},
            audit_log=[{"step": "queued_for_submit", "at": datetime.now(UTC).isoformat()}],
        )
        self.repository.save_browser_run(run)
        self._apply_browser_state(
            case,
            status=BrowserRunStatus.RUNNING,
            execution_mode=execution_mode,
            flow_type=eligibility.target.flow_type,
            target_fingerprint=eligibility.target.target_fingerprint,
            error=None,
        )
        result = self.executor.submit(run=run, case=case, target=eligibility.target, session=session)
        run.status = result.status
        run.screenshots = result.screenshots
        run.dom_hints = result.dom_hints
        run.audit_log.extend(result.audit_log)
        run.error_code = result.error_code
        run.error_detail = result.error_detail
        run.finished_at = datetime.now(UTC)
        self.repository.save_browser_run(run)
        self._persist_run_evidence(case, run, eligibility=eligibility, phase="submitted")
        error_text = result.error_detail or result.error_code
        self._apply_browser_state(
            case,
            status=result.status,
            execution_mode=execution_mode,
            flow_type=eligibility.target.flow_type,
            target_fingerprint=eligibility.target.target_fingerprint,
            error=error_text,
            submitted=result.status == BrowserRunStatus.SUBMITTED,
        )
        return run

    def evaluate_case(self, case: ThreatCase) -> BrowserEligibility:
        if case.source_type != SourceType.REVIEW_PHOTO:
            return BrowserEligibility(False, ["Solo las fotos críticas entran a browser enforcement."], None, None)
        evidence = self.repository.list_evidence_for_case(case.id)
        if not evidence:
            return BrowserEligibility(False, ["El caso no tiene evidencia primaria."], None, None)
        dealer = self.repository.dealers.get(case.dealer_id)
        official_numbers = {self._normalize_phone(value) for value in (dealer.phone_numbers if dealer else []) if value}
        suspicious_phone = None
        yamaha_visual = False
        target_url = None
        contributor_profile_url = None
        reasons: list[str] = []
        for artifact in evidence:
            content = artifact.content or {}
            raw_payload = content.get("raw_payload") or {}
            numbers = content.get("detected_phone_numbers") or raw_payload.get("detected_phone_numbers") or []
            for number in numbers:
                normalized = self._normalize_phone(str(number))
                if normalized and normalized not in official_numbers:
                    suspicious_phone = normalized
                    reasons.append("Se detectó un teléfono distinto al whitelist oficial.")
                    break
            text_blob = " ".join(
                str(item or "")
                for item in [
                    artifact.label,
                    content.get("ocr_text"),
                    content.get("extracted_text"),
                    content.get("review_text"),
                ]
            ).lower()
            if "yamaha" in text_blob:
                yamaha_visual = True
            target_url = (
                raw_payload.get("report_url")
                or raw_payload.get("report_surface_url")
                or raw_payload.get("profile_url")
                or raw_payload.get("source_page_url")
                or content.get("source_page_url")
                or content.get("google_maps_uri")
                or content.get("source_url")
                or content.get("source_image_url")
                or content.get("internal_image_url")
                or content.get("captured_image_url")
                or content.get("image_url")
                or target_url
            )
            contributor_profile_url = (
                raw_payload.get("contributor_profile_url")
                or content.get("contributor_profile_url")
                or contributor_profile_url
            )
        if not target_url:
            reasons.append("La evidencia no incluye una URL denunciable del asset.")
            return BrowserEligibility(False, reasons, suspicious_phone, None)
        if "/local/content/rap/report" not in str(target_url) and "google.com" not in str(target_url):
            reasons.append("Se usará una URL de contexto o captura para abrir la navegación del caso en modo piloto.")
        if suspicious_phone:
            reasons.append("La evidencia visual es apta para denuncia directa del asset.")
        if yamaha_visual:
            reasons.append("La foto conserva señales de marca Yamaha en el contexto capturado.")
        if case.risk_score >= 85:
            reasons.append("El score del caso ya está en zona crítica.")
        target = self._build_target(case, target_url=str(target_url), contributor_profile_url=self._string_or_none(contributor_profile_url))
        eligible = bool(
            suspicious_phone
            and yamaha_visual
            and case.risk_score >= 85
            and case.source_type == SourceType.REVIEW_PHOTO
        )
        return BrowserEligibility(eligible, reasons, suspicious_phone, target)

    def _build_target(self, case: ThreatCase, *, target_url: str, contributor_profile_url: str | None) -> BrowserTarget:
        flow_type = BrowserFlowType.REPORT_PHOTO_MOBILE if "wv=1" in target_url or "/local/content/rap/report" in target_url else BrowserFlowType.REPORT_PHOTO_DESKTOP
        fingerprint = hashlib.sha256(f"{case.id}|{target_url}".encode("utf-8")).hexdigest()[:24]
        return BrowserTarget(
            target_type="photo_asset",
            target_url=target_url,
            target_fingerprint=fingerprint,
            flow_type=flow_type,
            contributor_profile_url=contributor_profile_url,
        )

    def _require_active_session(self, organization_id: str | None) -> BrowserSession:
        if not organization_id:
            raise ValueError("El caso no está ligado a una organización.")
        session = self.repository.get_browser_session(organization_id)
        if not session or session.status != BrowserSessionStatus.ACTIVE:
            raise ValueError("La organización requiere reautenticación del dealer para browser enforcement.")
        return session

    def _ensure_not_duplicate(self, case: ThreatCase, target_fingerprint: str | None) -> None:
        if not target_fingerprint:
            return
        if case.browser_last_target_fingerprint != target_fingerprint:
            return
        if not case.browser_last_submitted_at:
            return
        cooldown = timedelta(hours=settings.browser_auto_submit_cooldown_hours)
        if datetime.now(UTC) - case.browser_last_submitted_at < cooldown:
            raise ValueError("Ya existe una denuncia reciente para este mismo asset dentro del cooldown.")

    def _apply_browser_state(
        self,
        case: ThreatCase,
        *,
        status: BrowserRunStatus,
        execution_mode: BrowserExecutionMode,
        flow_type: BrowserFlowType,
        target_fingerprint: str | None,
        error: str | None,
        submitted: bool = False,
    ) -> None:
        case.browser_execution_mode = execution_mode
        case.browser_status = status
        case.browser_flow_type = flow_type
        case.browser_last_run_at = datetime.now(UTC)
        case.browser_last_target_fingerprint = target_fingerprint
        case.browser_last_error = error
        case.eligible_for_auto_submit = self.evaluate_case(case).eligible
        if submitted:
            case.browser_last_submitted_at = datetime.now(UTC)
        self.repository.save_case(case)

    def _latest_run_for_target(self, case_id: str, target_fingerprint: str | None) -> BrowserRun | None:
        if not target_fingerprint:
            return None
        for run in self.repository.list_browser_runs(case_id=case_id):
            if run.target_fingerprint == target_fingerprint:
                return run
        return None

    def _persist_run_evidence(
        self,
        case: ThreatCase,
        run: BrowserRun,
        *,
        eligibility: BrowserEligibility,
        phase: str,
    ) -> None:
        session = self.repository.get_browser_session(case.organization_id or "") if case.organization_id else None
        artifact = EvidenceArtifact(
            id=self.repository.next_id("evidence"),
            case_id=case.id,
            artifact_type="browser_enforcement_run",
            label=f"Browser enforcement · {phase}",
            content={
                "browser_run_id": run.id,
                "phase": phase,
                "execution_mode": run.execution_mode.value,
                "status": run.status.value,
                "flow_type": run.flow_type.value,
                "target_type": run.target_type,
                "target_url": run.target_url,
                "target_fingerprint": run.target_fingerprint,
                "screenshots": run.screenshots,
                "dom_hints": run.dom_hints,
                "audit_log": run.audit_log,
                "error_code": run.error_code,
                "error_detail": run.error_detail,
                "started_at": run.started_at.isoformat() if run.started_at else None,
                "finished_at": run.finished_at.isoformat() if run.finished_at else None,
                "auth_user_email": session.auth_user_email if session else None,
                "eligible_for_auto_submit": eligibility.eligible,
                "eligibility_reasons": eligibility.reasons,
                "suspicious_phone": eligibility.suspicious_phone,
            },
        )
        self.repository.save_evidence(artifact)

    def _profile_id_for_case(self, case: ThreatCase) -> str | None:
        for profile in self.repository.profiles.values():
            if profile.dealer_id == case.dealer_id and profile.enabled:
                return profile.id
        return None

    def _get_case(self, case_id: str) -> ThreatCase:
        case = self.repository.get_case(case_id)
        if not case:
            raise ValueError("Caso no encontrado")
        case.eligible_for_auto_submit = self.evaluate_case(case).eligible
        return case

    @staticmethod
    def _normalize_phone(value: str) -> str:
        return "".join(char for char in value if char.isdigit())

    @staticmethod
    def _string_or_none(value: object) -> str | None:
        if value in (None, ""):
            return None
        return str(value)
