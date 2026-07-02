from __future__ import annotations

from app.agents.forensic import is_likely_colombian_phone, normalize_phone
from app.models import AlertEvent, EvidenceArtifact, GoogleReport, GoogleReportStatus, NotificationEventType, ThreatCase
from app.services.notifications import NotificationService
from app.store import Repository


class ReporterAgent:
    def __init__(self, repository: Repository, notification_service: NotificationService | None = None) -> None:
        self.repository = repository
        self.notification_service = notification_service or NotificationService(repository)

    def create_alert(self, case: ThreatCase) -> AlertEvent:
        dispatched = self.notification_service.notify_case_event(case, NotificationEventType.NEW_ALERT)
        if dispatched:
            return dispatched[0]
        event = AlertEvent(
            id=self.repository.next_id("alert"),
            case_id=case.id,
            organization_id=case.organization_id,
            channel="ops-webhook",
            message=f"[{case.risk_score}] {case.title}: {case.summary}",
        )
        self.repository.save_alert(event)
        return event

    def generate_report(self, case: ThreatCase) -> GoogleReport:
        report = self.repository.get_report(case.id) or GoogleReport(
            id=self.repository.next_id("report"),
            case_id=case.id,
        )
        package = self._build_report_package(case)
        report.status = GoogleReportStatus.DRAFTED
        report.report_url = f"https://support.google.com/business/contact/business_redressal_form?case={case.id}"
        report.response_summary = package["summary"]
        self.repository.upsert_report(report)
        self.notification_service.notify_case_event(case, NotificationEventType.CASE_READY_FOR_GOOGLE)
        self.repository.save_evidence(
            EvidenceArtifact(
                id=self.repository.next_id("evidence"),
                case_id=case.id,
                artifact_type="google_report_draft",
                label="Borrador de reporte Google",
                content={
                    **report.model_dump(mode="json"),
                    **package,
                },
            )
        )
        return report

    def _build_report_package(self, case: ThreatCase) -> dict[str, object]:
        dealer = self.repository.dealers.get(case.dealer_id)
        evidence = self.repository.list_evidence_for_case(case.id)
        official_numbers = [normalize_phone(number) for number in (dealer.phone_numbers if dealer else [])]
        suspicious_numbers: list[str] = []
        visual_evidence = []
        source_urls = []

        for artifact in evidence:
            content = artifact.content or {}
            for number in content.get("detected_phone_numbers", []) or []:
                normalized = normalize_phone(str(number))
                if (
                    normalized
                    and is_likely_colombian_phone(normalized)
                    and normalized not in official_numbers
                    and normalized not in suspicious_numbers
                ):
                    suspicious_numbers.append(normalized)
            image_url = content.get("internal_image_url") or content.get("captured_image_url")
            if image_url:
                visual_evidence.append({"label": artifact.label, "url": image_url})
            maps_url = content.get("google_maps_uri") or content.get("source_page_url") or content.get("source_image_url")
            if maps_url and maps_url not in source_urls:
                source_urls.append(maps_url)

        suspicious_phone = suspicious_numbers[0] if suspicious_numbers else "Sin teléfono detectado"
        official_phone = official_numbers[0] if official_numbers else "Sin teléfono oficial registrado"
        official_address = dealer.address if dealer else case.location_label
        summary = (
            f"Se preparó un borrador para Google con evidencia visual, OCR y contraste contra la whitelist oficial "
            f"de {case.dealer_name}. Conviene revisar el teléfono sospechoso {suspicious_phone} antes de enviarlo."
        )
        evidence_url = visual_evidence[0]["url"] if visual_evidence else None
        source_url = source_urls[0] if source_urls else None
        copy_ready_text = (
            f"Solicito revisión del perfil oficial de {case.dealer_name} por contenido engañoso.\n\n"
            f"La evidencia visual muestra una foto pública con la marca Yamaha y un teléfono no autorizado.\n"
            f"Sede oficial: {case.dealer_name}.\n"
            f"Dirección oficial: {official_address}.\n"
            f"Teléfono oficial: {official_phone}.\n"
            f"Teléfono sospechoso detectado en la imagen: {suspicious_phone}.\n\n"
            f"Esta imagen puede desviar clientes desde Google Maps o Google Business Profile al publicar datos de contacto falsos para una sede oficial.\n"
            f"Solicito retirar o corregir la foto pública y cualquier referencia visual que publique teléfonos o datos de contacto no autorizados."
        )
        if evidence_url or source_url:
            copy_ready_text += "\n\nEnlaces de soporte:"
            if evidence_url:
                copy_ready_text += f"\n- Evidencia preservada: {evidence_url}"
            if source_url:
                copy_ready_text += f"\n- Fuente observada en Google: {source_url}"
        return {
            "report_title": f"Suplantación visual del perfil oficial de {case.dealer_name}",
            "summary": summary,
            "executive_summary": (
                f"El perfil oficial de {case.dealer_name} muestra una imagen pública con marca Yamaha y un contacto "
                f"no autorizado que puede desviar clientes desde Google Maps o Google Business Profile."
            ),
            "policy_basis": (
                "La evidencia sugiere contenido engañoso sobre una sede oficial: usa marca, fachada y un teléfono "
                "distinto al registrado en la whitelist interna."
            ),
            "official_phone_numbers": official_numbers,
            "suspicious_phone_numbers": suspicious_numbers,
            "official_phone": official_phone,
            "suspicious_phone": suspicious_phone,
            "requested_action": (
                "Retirar o corregir la foto pública y cualquier referencia visual que publique teléfonos o datos "
                "de contacto no autorizados para la sede oficial."
            ),
            "submission_notes": [
                f"Sede oficial afectada: {case.dealer_name}.",
                f"Dirección oficial: {official_address}.",
                f"Teléfono oficial registrado: {official_phone}.",
                f"Teléfono sospechoso detectado: {suspicious_phone}.",
            ],
            "copy_ready_text": copy_ready_text,
            "evidence_links": visual_evidence,
            "source_links": source_urls,
        }
