from __future__ import annotations

from collections import defaultdict
from datetime import UTC

from app.agents.forensic import ForensicAgent, extract_phone_numbers
from app.models import (
    CaseStatus,
    EvidenceArtifact,
    JobRun,
    JobStatus,
    MonitoringMode,
    ObservedAsset,
    ObservedPlace,
    RiskBucket,
    ScanRun,
    SourceType,
    ThreatCase,
)
from app.store import Repository


class ScoutAgent:
    def __init__(self, repository: Repository, forensic: ForensicAgent) -> None:
        self.repository = repository
        self.forensic = forensic

    def run_public_scan(self, query: str, observed_places: list[ObservedPlace]) -> ScanRun:
        scan = ScanRun(id=self.repository.next_id("scan"), query=query)
        job = JobRun(
            id=self.repository.next_id("job"),
            job_type="public_scan",
            job_status=JobStatus.RUNNING,
            detail=f"Ejecutando busqueda publica para {query}.",
        )
        self.repository.save_job(job)
        self.repository.save_scan(scan)

        threats = 0
        contextual_observations = 0
        for place in self._consolidate_places(observed_places):
            dealers = list(self.repository.dealers.values())
            existing = self.repository.find_case_by_reference(place.place_id)
            official_matches = [
                dealer for dealer in dealers if self.forensic.looks_like_official_place(dealer, place)
            ]
            if official_matches:
                if existing:
                    self._dismiss_stale_place_case(existing, "Reclasificado como punto oficial autorizado.")
                continue

            ranked = sorted(
                (
                    (self.forensic.dealer_relevance_score(dealer, place), dealer)
                    for dealer in dealers
                ),
                key=lambda item: item[0],
                reverse=True,
            )
            if not ranked or ranked[0][0] < 35:
                if existing:
                    self._dismiss_stale_place_case(existing, "Reclasificado como punto sin relevancia suficiente para alerta.")
                continue

            _, dealer = ranked[0]
            assessment = self.forensic.classify_place(dealer, place)
            score, reasons = assessment.score, assessment.reasons
            if assessment.classification == "non_official_legit":
                contextual_observations += 1
                if existing:
                    self._dismiss_stale_place_case(existing, "Reclasificado como punto legítimo en el re-scan.")
                continue
            if not assessment.should_open_case:
                if existing:
                    self._dismiss_stale_place_case(existing, "Reclasificado sin evidencia suficiente para mantener alerta.")
                continue

            threats += 1
            if existing:
                existing.risk_score = max(existing.risk_score, score)
                existing.risk_reasons = sorted(set(existing.risk_reasons + reasons))
                if existing.status in {CaseStatus.NEW, CaseStatus.TRIAGED}:
                    if assessment.classification == "high_risk_watchlist":
                        existing.risk_bucket = RiskBucket.HIGH_RISK_WATCHLIST
                        existing.title = f"Watchlist de alto riesgo de {dealer.name}"
                    else:
                        existing.risk_bucket = RiskBucket.CLONE_RISK
                        existing.title = f"Posible clon de {dealer.name}"
                existing.summary = (
                    f"Persisten senales de riesgo alrededor de {dealer.name}: "
                    f"{self._clone_summary(place, assessment.classification)}"
                )
                existing.dealer_id = dealer.id
                existing.dealer_name = dealer.name
                existing.city = dealer.city
                self.repository.save_case(existing)
                continue
            case = ThreatCase(
                id=self.repository.next_id("case"),
                title=(
                    f"Watchlist de alto riesgo de {dealer.name}"
                    if assessment.classification == "high_risk_watchlist"
                    else f"Posible clon de {dealer.name}"
                ),
                dealer_id=dealer.id,
                organization_id=dealer.organization_id,
                dealer_name=dealer.name,
                city=dealer.city,
                monitoring_mode=MonitoringMode.PUBLIC_SCAN,
                source_type=SourceType.PLACE_CLONE,
                risk_bucket=(
                    RiskBucket.HIGH_RISK_WATCHLIST
                    if assessment.classification == "high_risk_watchlist"
                    else RiskBucket.CLONE_RISK
                ),
                risk_score=score,
                risk_reasons=reasons,
                summary=self._clone_summary(place, assessment.classification),
                location_label=place.address,
                source_reference_id=place.place_id,
            )
            self.repository.save_case(case)
            self.repository.save_evidence(
                EvidenceArtifact(
                    id=self.repository.next_id("evidence"),
                    case_id=case.id,
                    artifact_type="observed_place",
                    label=place.name,
                    content={
                        **place.model_dump(mode="json"),
                        "classification": assessment.classification,
                        "subscores": assessment.subscores,
                        "query_hits": place.raw_payload.get("query_hits", [place.source_query]),
                    },
                )
            )
        scan.finished_at = scan.started_at.astimezone(UTC)
        scan.threats_found = threats
        scan.estimated_api_cost_usd = round(max(0.03, len(observed_places) * 0.016), 2)
        if contextual_observations:
            scan.notes = f"{contextual_observations} puntos no oficiales se mantuvieron como contexto y no escalaron a caso."
        self.repository.save_scan(scan)

        job.job_status = JobStatus.COMPLETED
        job.finished_at = scan.finished_at
        job.estimated_api_cost_usd = scan.estimated_api_cost_usd
        job.detail = (
            f"Scan completado. {threats} amenazas detectadas y {contextual_observations} puntos no oficiales quedaron en observacion."
        )
        self.repository.save_job(job)
        return scan

    def _dismiss_stale_place_case(self, case: ThreatCase, reason: str) -> None:
        if case.source_type != SourceType.PLACE_CLONE or case.status == CaseStatus.DISMISSED:
            return
        case.status = CaseStatus.DISMISSED
        case.summary = f"{reason} Se conserva en histórico como falso positivo o alerta superada."
        case.risk_reasons = sorted(set(case.risk_reasons + [reason]))
        self.repository.save_case(case)

    def process_gbp_event(self, asset: ObservedAsset) -> ThreatCase | None:
        profile = self.repository.profiles.get(asset.profile_id)
        if not profile:
            return None
        dealer = self.repository.dealers.get(profile.dealer_id)
        if not dealer:
            return None
        job = JobRun(
            id=self.repository.next_id("job"),
            job_type="gbp_event",
            organization_id=profile.organization_id or dealer.organization_id,
            job_status=JobStatus.RUNNING,
            detail=f"Procesando evento GBP para {profile.name}.",
        )
        self.repository.save_job(job)
        score, reasons = self.forensic.score_asset(dealer, asset)
        if score < 45:
            job.job_status = JobStatus.COMPLETED
            job.detail = "Evento GBP analizado sin amenaza confirmable."
            job.finished_at = asset.observed_at
            self.repository.save_job(job)
            return None

        reference_id = asset.external_media_id or asset.id
        existing = self.repository.find_case_by_reference(reference_id)
        if not existing and asset.source_type == SourceType.REVIEW_PHOTO:
            existing = self._find_related_review_photo_case(dealer.id, asset)

        if existing:
            existing.risk_score = max(existing.risk_score, score)
            existing.risk_reasons = sorted(set(existing.risk_reasons + reasons))
            existing.summary = f"Persisten senales de alteracion sobre el perfil oficial de {dealer.name}."
            self.repository.save_case(existing)
            self._save_asset_evidence(existing.id, profile.name, asset, score, reasons)
            job.job_status = JobStatus.COMPLETED
            job.finished_at = asset.observed_at
            job.detail = "Evento GBP agregado a un caso existente."
            self.repository.save_job(job)
            return existing
        case = ThreatCase(
            id=self.repository.next_id("case"),
            title=f"Posible foto manipulada en {dealer.name}",
            dealer_id=dealer.id,
            organization_id=profile.organization_id or dealer.organization_id,
            dealer_name=dealer.name,
            city=dealer.city,
            monitoring_mode=MonitoringMode.GBP_PUSH,
            source_type=asset.source_type,
            risk_score=score,
            risk_reasons=reasons,
            summary=f"Se detecto contenido sospechoso en el perfil oficial de {dealer.name}.",
            location_label=dealer.address,
            source_reference_id=reference_id,
        )
        self.repository.save_case(case)
        self._save_asset_evidence(case.id, profile.name, asset, score, reasons)
        job.job_status = JobStatus.COMPLETED
        job.finished_at = asset.observed_at
        job.estimated_api_cost_usd = 0.01
        job.detail = "Evento GBP convertido en caso."
        self.repository.save_job(job)
        return case

    def _save_asset_evidence(
        self,
        case_id: str,
        label: str,
        asset: ObservedAsset,
        score: int,
        reasons: list[str],
    ) -> None:
        external_media_id = asset.external_media_id
        existing_evidence = self.repository.list_evidence_for_case(case_id)
        for artifact in existing_evidence:
            content = artifact.content or {}
            if external_media_id and content.get("external_media_id") == external_media_id:
                return
            if asset.media_hash and content.get("media_hash") == asset.media_hash:
                return

        detected_numbers = extract_phone_numbers(asset.extracted_text or asset.review_text)
        raw_media_origin = (asset.raw_payload or {}).get("media_origin")
        content = {
            **asset.model_dump(mode="json"),
            "internal_image_url": asset.captured_image_url,
            "source_image_url": asset.source_url or asset.image_url or asset.thumbnail_url,
            "ocr_text": asset.extracted_text,
            "detected_phone_numbers": detected_numbers,
            "media_origin": raw_media_origin or ("gbp_customer_media" if asset.source_type == SourceType.REVIEW_PHOTO else "gbp_profile_event"),
            "download_status": asset.download_status or "not_requested",
            "forensic_summary": {
                "score": score,
                "reasons": reasons,
            },
        }
        self.repository.save_evidence(
            EvidenceArtifact(
                id=self.repository.next_id("evidence"),
                case_id=case_id,
                artifact_type="observed_asset",
                label=label,
                content=content,
            )
        )

    def _find_related_review_photo_case(self, dealer_id: str, asset: ObservedAsset) -> ThreatCase | None:
        candidates = [
            case
            for case in self.repository.list_cases()
            if case.dealer_id == dealer_id
            and case.source_type == SourceType.REVIEW_PHOTO
            and case.status != CaseStatus.DISMISSED
        ]
        if not candidates:
            return None

        detected_numbers = set(extract_phone_numbers(asset.extracted_text or asset.review_text))
        if detected_numbers:
            for case in candidates:
                for artifact in self.repository.list_evidence_for_case(case.id):
                    numbers = set((artifact.content or {}).get("detected_phone_numbers", []))
                    if numbers.intersection(detected_numbers):
                        return case

        if len(candidates) == 1 and asset.media_hash:
            return candidates[0]
        return None

    def _consolidate_places(self, observed_places: list[ObservedPlace]) -> list[ObservedPlace]:
        grouped: dict[str, list[ObservedPlace]] = defaultdict(list)
        for place in observed_places:
            grouped[place.place_id].append(place)

        consolidated: list[ObservedPlace] = []
        for places in grouped.values():
            primary = sorted(
                places,
                key=lambda item: (
                    item.query_rank if item.query_rank is not None else 999,
                    -(item.user_rating_count or 0),
                    item.observed_at,
                ),
            )[0]
            query_hits = sorted({item.source_query for item in places if item.source_query})
            best_rank = min((item.query_rank for item in places if item.query_rank is not None), default=primary.query_rank)
            richest = max(places, key=lambda item: item.user_rating_count or 0)
            primary.query_rank = best_rank
            primary.rating = richest.rating if richest.rating is not None else primary.rating
            primary.user_rating_count = (
                richest.user_rating_count if richest.user_rating_count is not None else primary.user_rating_count
            )
            primary.business_status = richest.business_status or primary.business_status
            primary.first_seen_at = min(
                (item.first_seen_at for item in places if item.first_seen_at is not None),
                default=primary.first_seen_at,
            )
            primary.raw_payload = {
                **primary.raw_payload,
                "query_hits": query_hits,
                "query_hit_count": len(query_hits),
            }
            consolidated.append(primary)
        return consolidated

    def _clone_summary(self, place: ObservedPlace, classification: str) -> str:
        query_hits = place.raw_payload.get("query_hits", [place.source_query])
        query_label = ", ".join(query_hits[:3]) if isinstance(query_hits, list) else str(query_hits)
        if classification == "clone_risk":
            return (
                f"El punto {place.name} aparece en busquedas como [{query_label}] y combina naming sospechoso, "
                "findability competitiva y cercania a una sede oficial."
            )
        if classification == "high_risk_watchlist":
            return (
                f"El punto {place.name} aparece en busquedas como [{query_label}] y entra a watchlist de alto riesgo "
                "porque mezcla visibilidad competitiva, mismatch operativo y cercania relevante, pero todavía exige validación humana."
            )
        return f"El punto {place.name} sigue en observacion contextual desde las busquedas [{query_label}]."
