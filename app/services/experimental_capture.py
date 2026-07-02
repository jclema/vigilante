from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from app.models import SourceType
from app.services.multi_source_ingest import EvidenceIngestionRequest, MultiSourceEvidenceIngestService
from app.store import Repository

if TYPE_CHECKING:
    from app.agents.scout import ScoutAgent


@dataclass(slots=True)
class ExperimentalCaptureRecord:
    profile_id: str
    profile_name: str
    screenshot_path: str
    profile_url: str
    review_text: str | None = None
    extracted_text: str | None = None
    captured_from: str = "experimental_browser_capture"
    final_url: str | None = None
    gallery_opened: bool = False
    gallery_open_method: str | None = None
    all_media_selected: bool = False
    media_filter: str | None = None
    gallery_hint: str | None = None
    browser_surface: str | None = None
    step_trace: list[dict[str, str]] | None = None
    fallback_used: bool = False
    asset_fingerprint: str | None = None
    navigation_confidence: str | None = None
    capture_failure_reason: str | None = None


class ExperimentalCaptureIngestService:
    def __init__(self, repository: Repository, scout_agent: ScoutAgent, evidence_service, text_extractor) -> None:
        self.repository = repository
        self.ingest_service = MultiSourceEvidenceIngestService(
            repository=repository,
            scout_agent=scout_agent,
            evidence_service=evidence_service,
            text_extractor=text_extractor,
        )

    def ingest_capture(self, record: ExperimentalCaptureRecord):
        profile = self.repository.profiles.get(record.profile_id)
        if not profile:
            raise ValueError(f"Perfil no encontrado: {record.profile_id}")

        screenshot_url = self._file_url(record.screenshot_path)
        return self.ingest_service.ingest_request(
            EvidenceIngestionRequest(
                profile_id=record.profile_id,
                source_type=SourceType.REVIEW_PHOTO,
                source_url=screenshot_url,
                image_url=screenshot_url,
                source_page_url=record.profile_url,
                google_maps_uri=record.profile_url,
                ingestion_mode="experimental_browser_capture",
                media_origin="experimental_browser_capture",
                review_text=record.review_text,
                extracted_text=record.extracted_text,
                external_media_id=Path(record.screenshot_path).stem,
                raw_payload={
                    "capture_mode": record.captured_from,
                    "profile_name": record.profile_name,
                    "final_url": record.final_url,
                    "gallery_opened": record.gallery_opened,
                    "gallery_open_method": record.gallery_open_method,
                    "all_media_selected": record.all_media_selected,
                    "media_filter": record.media_filter,
                    "gallery_hint": record.gallery_hint,
                    "browser_surface": record.browser_surface,
                    "step_trace": record.step_trace or [],
                    "fallback_used": record.fallback_used,
                    "asset_fingerprint": record.asset_fingerprint,
                    "navigation_confidence": record.navigation_confidence,
                    "capture_failure_reason": record.capture_failure_reason,
                },
            )
        )

    def run_batch(self, records: list[ExperimentalCaptureRecord]) -> dict[str, object]:
        requests = [
            EvidenceIngestionRequest(
                profile_id=record.profile_id,
                source_type=SourceType.REVIEW_PHOTO,
                source_url=self._file_url(record.screenshot_path),
                image_url=self._file_url(record.screenshot_path),
                source_page_url=record.profile_url,
                google_maps_uri=record.profile_url,
                ingestion_mode="experimental_browser_capture",
                media_origin="experimental_browser_capture",
                review_text=record.review_text,
                extracted_text=record.extracted_text,
                external_media_id=Path(record.screenshot_path).stem,
                raw_payload={
                    "capture_mode": record.captured_from,
                    "profile_name": record.profile_name,
                    "final_url": record.final_url,
                    "gallery_opened": record.gallery_opened,
                    "gallery_open_method": record.gallery_open_method,
                    "all_media_selected": record.all_media_selected,
                    "media_filter": record.media_filter,
                    "gallery_hint": record.gallery_hint,
                    "browser_surface": record.browser_surface,
                    "step_trace": record.step_trace or [],
                    "fallback_used": record.fallback_used,
                    "asset_fingerprint": record.asset_fingerprint,
                    "navigation_confidence": record.navigation_confidence,
                    "capture_failure_reason": record.capture_failure_reason,
                },
            )
            for record in records
        ]
        return self.ingest_service.ingest_batch(
            requests,
            job_type="experimental_browser_capture",
            detail="Procesando capturas experimentales de perfiles oficiales.",
        )

    @staticmethod
    def _file_url(value: str) -> str:
        path = Path(value).expanduser().resolve()
        return path.as_uri()
