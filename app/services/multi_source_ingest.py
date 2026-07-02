from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from app.agents.forensic import extract_phone_numbers
from app.models import JobRun, JobStatus, ObservedAsset, SourceType
from app.store import Repository


@dataclass(slots=True)
class EvidenceIngestionRequest:
    profile_id: str
    source_type: SourceType
    organization_id: str | None = None
    source_url: str | None = None
    image_url: str | None = None
    source_page_url: str | None = None
    google_maps_uri: str | None = None
    thumbnail_url: str | None = None
    external_media_id: str | None = None
    gbp_location_id: str | None = None
    review_id: str | None = None
    review_text: str | None = None
    extracted_text: str | None = None
    ingestion_mode: str | None = None
    media_origin: str | None = None
    raw_payload: dict[str, object] | None = None
    observed_at: datetime | None = None


class MultiSourceEvidenceIngestService:
    def __init__(self, repository: Repository, scout_agent, evidence_service, text_extractor) -> None:
        self.repository = repository
        self.scout_agent = scout_agent
        self.evidence_service = evidence_service
        self.text_extractor = text_extractor

    def ingest_request(self, request: EvidenceIngestionRequest):
        asset = self._build_asset(request)
        asset = self._capture_asset(asset, request)
        return self.scout_agent.process_gbp_event(asset)

    def ingest_batch(
        self,
        requests: list[EvidenceIngestionRequest],
        *,
        job_type: str,
        detail: str,
    ) -> dict[str, object]:
        job = JobRun(
            id=self.repository.next_id("job"),
            job_type=job_type,
            job_status=JobStatus.RUNNING,
            detail=detail,
        )
        self.repository.save_job(job)

        processed = 0
        cases_touched = 0
        download_failures = 0
        for request in requests:
            case = self.ingest_request(request)
            processed += 1
            if case:
                cases_touched += 1
            evidence = self.repository.list_evidence_for_case(case.id)[-1] if case else None
            if evidence and (evidence.content or {}).get("download_status") == "download_failed":
                download_failures += 1

        job.job_status = JobStatus.DEGRADED if download_failures else JobStatus.COMPLETED
        job.finished_at = datetime.now(UTC)
        job.detail = f"{detail} {processed} evidencia(s) revisadas, {cases_touched} caso(s) generados o enriquecidos."
        self.repository.save_job(job)
        return {
            "processed": processed,
            "cases_touched": cases_touched,
            "download_failures": download_failures,
        }

    def _build_asset(self, request: EvidenceIngestionRequest) -> ObservedAsset:
        return ObservedAsset(
            id=self.repository.next_id("asset"),
            profile_id=request.profile_id,
            organization_id=request.organization_id or self._profile_organization_id(request.profile_id),
            source_type=request.source_type,
            image_url=request.image_url,
            external_media_id=request.external_media_id,
            gbp_location_id=request.gbp_location_id,
            source_page_url=request.source_page_url,
            google_maps_uri=request.google_maps_uri,
            thumbnail_url=request.thumbnail_url,
            source_url=request.source_url or request.image_url or request.thumbnail_url,
            review_id=request.review_id,
            ingestion_mode=request.ingestion_mode,
            review_text=request.review_text,
            extracted_text=request.extracted_text,
            observed_at=request.observed_at or datetime.now(UTC),
            raw_payload=request.raw_payload or {},
        )

    def _capture_asset(self, asset: ObservedAsset, request: EvidenceIngestionRequest) -> ObservedAsset:
        artifact_id = (asset.external_media_id or asset.id).replace("/", "-")
        captured = self.evidence_service.capture_image(
            case_id=asset.profile_id,
            artifact_id=artifact_id,
            source_url=asset.source_url,
        )
        asset.captured_image_url = captured.internal_url
        asset.evidence_image_path = captured.storage_path
        asset.media_hash = captured.checksum
        asset.download_status = captured.download_status
        extracted = self.text_extractor.extract_text(
            image_bytes=captured.bytes_payload,
            content_type=captured.content_type,
            raw_payload=asset.raw_payload,
            fallback_text=asset.extracted_text or asset.review_text,
        )
        asset.extracted_text = extracted
        raw_payload = dict(asset.raw_payload)
        raw_payload["detected_phone_numbers"] = extract_phone_numbers(extracted or asset.review_text)
        raw_payload["media_origin"] = request.media_origin or raw_payload.get("media_origin")
        asset.raw_payload = raw_payload
        return asset

    def _profile_organization_id(self, profile_id: str) -> str | None:
        profile = self.repository.profiles.get(profile_id)
        if not profile:
            return None
        return profile.organization_id
