from __future__ import annotations

from collections import Counter, defaultdict
from zoneinfo import ZoneInfo
from urllib.parse import parse_qs, quote, urlparse

from app.models import CaseStatus, JobStatus, MonitoringMode, RiskBucket, SourceType
from app.services.access import ScopedRepositoryView
from app.services.auth import ActorContext
from app.services.places import places_search_service
from app.store import Repository

COLOMBIA_TZ = ZoneInfo("America/Bogota")


class DashboardService:
    def __init__(self, repository: Repository, actor: ActorContext | None = None) -> None:
        self.repository = ScopedRepositoryView(repository, actor)
        self._dealer_maps_link_cache: dict[str, str | None] = {}

    def _active_cases(self):
        return [case for case in self.repository.list_cases() if case.status != CaseStatus.DISMISSED]

    @staticmethod
    def _format_when(value):
        if not value:
            return "Sin registro"
        try:
            return value.astimezone(COLOMBIA_TZ).strftime("%Y-%m-%d %H:%M COT")
        except Exception:
            return str(value)

    def executive_summary(self) -> dict[str, object]:
        cases = self._active_cases()
        all_cases = self.repository.list_cases()
        confirmed = [case for case in cases if case.status in {CaseStatus.CONFIRMED, CaseStatus.REPORTED}]
        archived = [case for case in all_cases if case.status == CaseStatus.DISMISSED]
        critical = [case for case in cases if case.risk_bucket != RiskBucket.HIGH_RISK_WATCHLIST and case.risk_score >= 80]
        watchlist = [case for case in cases if case.risk_bucket == RiskBucket.HIGH_RISK_WATCHLIST]
        pending_decision_cases = [case for case in cases if case.status in {CaseStatus.NEW, CaseStatus.TRIAGED}]
        active_dealer_ids = {case.dealer_id for case in cases}
        active_cities = [self._display_city(case.city) for case in cases]
        city_counts = Counter(active_cities)
        top_city, top_city_count = city_counts.most_common(1)[0] if city_counts else ("Sin presión visible", 0)
        source_counts = Counter(case.source_type for case in cases)
        top_source = source_counts.most_common(1)[0][0] if source_counts else None
        highest_case = max(cases, key=lambda item: item.risk_score, default=None)
        active_profiles = sum(1 for profile in self.repository.profiles.values() if profile.enabled)
        total_profiles = len([profile for profile in self.repository.profiles.values() if profile.enabled])
        latest_scan = self.repository.list_scans()[0] if self.repository.list_scans() else None
        gbp_profiles = sum(
            1 for profile in self.repository.profiles.values() if profile.monitoring_mode == MonitoringMode.GBP_PUSH
        )
        pending_analysis = len([case for case in cases if case.status in {CaseStatus.NEW, CaseStatus.TRIAGED} and case.risk_score >= 70])
        google_started = [case for case in all_cases if case.google_report_status.value != "not_started"]
        google_effectiveness = (
            round((len([case for case in google_started if case.google_report_status.value in {"acknowledged", "resolved"}]) / len(google_started)) * 100)
            if google_started
            else 0
        )
        summary_lead = (
            {
                "value": f"{len(active_dealer_ids)} sedes bajo presión hoy",
                "context": "Hay al menos una señal activa visible que requiere seguimiento o decisión humana.",
            }
            if cases
            else {
                "value": f"{active_profiles} perfiles protegidos",
                "context": "No hay amenazas activas en este momento y la prioridad es sostener la cobertura.",
            }
        )
        confirmed_label = "incidente confirmado" if len(confirmed) == 1 else "incidentes confirmados"
        return {
            "headline": {
                "protection_level": "🚨 Riesgo activo en la red" if cases else "✅ Red estable bajo vigilancia",
                "coverage": f"{active_profiles} perfiles protegidos",
                "trend": f"{len(confirmed)} {confirmed_label} entre Google Business Profile y Google Maps",
            },
            "summary_lead": summary_lead,
            "situation": {
                "title": "Situación actual de la red",
                "headline": (
                    f"Hoy hay {len(cases)} amenaza{'s' if len(cases) != 1 else ''} activa{'s' if len(cases) != 1 else ''} "
                    f"en {len(active_dealer_ids)} sede{'s' if len(active_dealer_ids) != 1 else ''} "
                    f"de {len(set(active_cities))} municipio{'s' if len(set(active_cities)) != 1 else ''}."
                    if cases
                    else "Hoy no hay amenazas activas en la red vigilada."
                ),
                "summary": (
                    "Lo importante ahora es despejar primero lo crítico y destrabar los casos que todavía dependen de decisión humana."
                    if cases
                    else "La red se ve estable. La tarea clave es sostener la vigilancia y confirmar que el monitoreo siga sano."
                ),
                "signals": [
                    f"🚨 {len(critical)} caso{'s' if len(critical) != 1 else ''} crítico{'s' if len(critical) != 1 else ''}",
                    f"🧭 {len(pending_decision_cases)} pendiente{'s' if len(pending_decision_cases) != 1 else ''} de decisión",
                    f"🏍️ {len(active_dealer_ids)} sede{'s' if len(active_dealer_ids) != 1 else ''} expuesta{'s' if len(active_dealer_ids) != 1 else ''}",
                ],
            },
            "focus": {
                "title": "Dónde mirar primero",
                "headline": top_city if cases else "Sin zona prioritaria",
                "summary": (
                    f"{top_city} concentra {top_city_count} señal{'es' if top_city_count != 1 else ''} activa{'s' if top_city_count != 1 else ''} "
                    f"y hoy merece la primera revisión."
                    if cases and top_source
                    else "No hay una concentración visible de riesgo en este momento."
                ),
                "notes": [
                    f"Señal dominante: {self._source_label(top_source)}" if top_source else "Señal dominante: sin datos",
                    f"Sede más expuesta: {highest_case.dealer_name}" if highest_case else "Sede más expuesta: sin casos abiertos",
                    f"Riesgo máximo observado: {highest_case.risk_score}/100" if highest_case else "Riesgo máximo observado: 0/100",
                ],
            },
            "top_metrics": [
                {
                    "label": "Salud de red",
                    "value": f"{round((active_profiles / total_profiles) * 100) if total_profiles else 0}%",
                    "context": "perfiles oficiales monitoreados",
                    "tone": "calm",
                },
                {
                    "label": "Amenazas activas",
                    "value": str(len(cases)),
                    "context": "ubicaciones, fotos o reseñas bajo observación",
                    "tone": "critical" if critical else "watch",
                },
                {
                    "label": "Watchlist alto riesgo",
                    "value": str(len(watchlist)),
                    "context": "casos visibles que exigen validación humana antes de escalar",
                    "tone": "watch" if watchlist else "neutral",
                },
                {
                    "label": "Análisis pendientes",
                    "value": str(pending_analysis),
                    "context": "casos altos que aún requieren validación humana",
                    "tone": "watch" if pending_analysis else "calm",
                },
                {
                    "label": "Efectividad de mitigación",
                    "value": f"{google_effectiveness}%",
                    "context": "casos con respuesta o cierre por parte de Google",
                    "tone": "calm" if google_effectiveness >= 60 else "neutral",
                },
            ],
            "highlights": [
                {"emoji": "🚨", "label": "Amenazas activas", "value": str(len(cases)), "context": "casos abiertos que siguen pidiendo atención"},
                {"emoji": "🕵️", "label": "Watchlist visible", "value": str(len(watchlist)), "context": "casos ambiguos de alto riesgo pendientes de validación"},
                {"emoji": "📨", "label": "Casos listos para Google", "value": str(sum(case.google_report_status != 'not_started' for case in cases)), "context": "ya preparados o enviados para gestión"},
                {"emoji": "🏍️", "label": "Sedes hoy bajo presión", "value": str(len(active_dealer_ids)), "context": "con al menos una señal activa visible"},
                {"emoji": "🧭", "label": "Decisiones humanas pendientes", "value": str(len(pending_decision_cases)), "context": "casos nuevos o en evaluación que frenan avance"},
            ],
            "ribbon": [
                {"label": "Casos críticos", "value": str(len(critical))},
                {"label": "Archivados tras tuning", "value": str(len(archived))},
                {"label": "Perfiles con GBP", "value": str(gbp_profiles)},
                {"label": "Último barrido", "value": self._format_when(latest_scan.started_at) if latest_scan else "Pendiente"},
            ],
            "alert_feed": self._alert_feed(cases),
            "critical_cards": self._critical_cards(cases),
        }

    def operations_summary(self) -> dict[str, object]:
        jobs = self.repository.list_jobs()
        scans = self.repository.list_scans()
        recent = jobs[:6]
        latest_scan = scans[0] if scans else None
        total_cost = round(sum(job.estimated_api_cost_usd for job in jobs), 2)
        status_counts = Counter(job.job_status for job in jobs)
        all_cases = self.repository.list_cases()
        active_cases = [case for case in all_cases if case.status != CaseStatus.DISMISSED]
        attention_count = status_counts.get("failed", 0) + status_counts.get("degraded", 0)
        return {
            "jobs": [self._job_card(job) for job in recent],
            "lead": {
                "headline": (
                    "Hay procesos que piden revisión"
                    if attention_count
                    else "La operación corre con normalidad"
                ),
                "summary": (
                    f"{attention_count} proceso{'s' if attention_count != 1 else ''} requiere{'n' if attention_count != 1 else ''} atención por error o degradación."
                    if attention_count
                    else "Los barridos y eventos recientes terminaron sin señales operativas que frenen el monitoreo."
                ),
            },
            "costs": {
                "today": f"USD {total_cost:.2f}",
                "places": f"USD {sum(job.estimated_api_cost_usd for job in jobs if job.job_type == 'public_scan'):.2f}",
                "gbp": f"USD {sum(job.estimated_api_cost_usd for job in jobs if job.job_type in {'gbp_event', 'gbp_customer_media_backfill', 'gbp_customer_media_reconcile'}) :.2f}",
                "vision": "USD 0.00",
            },
            "health": {
                "running": status_counts.get("running", 0),
                "completed": status_counts.get("completed", 0),
                "failed": status_counts.get("failed", 0),
                "degraded": status_counts.get("degraded", 0),
                "attention": attention_count,
            },
            "summary": {
                "latest_scan_time": self._format_when(latest_scan.started_at) if latest_scan else "Sin barridos",
                "latest_scan_threats": latest_scan.threats_found if latest_scan else 0,
                "latest_scan_cost": f"USD {latest_scan.estimated_api_cost_usd:.2f}" if latest_scan else "USD 0.00",
                "active_cases": len(active_cases),
                "archived_cases": len([case for case in all_cases if case.status == CaseStatus.DISMISSED]),
                "scheduler": "Cada hora · job activo",
            },
            "google_kanban": self._google_kanban(active_cases),
            "google_flow": [
                {
                    "label": "Sin iniciar con Google",
                    "context": "Todavía no se preparó gestión hacia Google para ese caso.",
                },
                {
                    "label": "Borrador listo para revisión",
                    "context": "El expediente ya está armado y espera validación humana antes de enviarse.",
                },
                {
                    "label": "Enviado a Google",
                    "context": "La red Yamaha ya elevó el caso y ahora corresponde hacer seguimiento.",
                },
                {
                    "label": "Google recibió el caso",
                    "context": "Google confirmó recepción y falta esperar resolución o cambio visible.",
                },
                {
                    "label": "Caso cerrado con Google",
                    "context": "El caso ya se cerró frente a Google y solo queda conservar trazabilidad.",
                },
            ],
        }

    def _google_kanban(self, cases):
        flow_definitions = [
            ("not_started", "Sin iniciar", "Casos que todavía piden decisión interna antes de mover algo frente a Google."),
            ("drafted", "Borrador listo", "Casos ya preparados para revisión antes de enviarse."),
            ("submitted", "Enviado", "Casos ya elevados a Google y pendientes de respuesta."),
            ("acknowledged", "Recibido", "Casos que Google ya recibió y siguen en seguimiento."),
            ("resolved", "Cerrado", "Casos cerrados con Google, conservados como trazabilidad."),
        ]
        columns = []
        status_counts = Counter(case.google_report_status.value for case in cases)
        open_statuses = [status for status, _, _ in flow_definitions if status != "resolved"]
        max_open_count = max((status_counts.get(status, 0) for status in open_statuses), default=0)
        for status_value, label, context in flow_definitions:
            grouped_cases = [
                {
                    "id": case.id,
                    "title": case.title,
                    "dealer_name": case.dealer_name,
                    "city": self._display_city(case.city),
                    "risk_score": case.risk_score,
                    "risk_tone": self._risk_tone(case.risk_score),
                    "risk_label": self._risk_band(case.risk_score)["label"],
                    "case_status_label": self._labelize_value(case.status.value),
                    "recommended_action": self._recommended_action(case.risk_score, case.google_report_status.value, case.risk_bucket),
                }
                for case in sorted(cases, key=lambda item: (item.risk_score, item.updated_at), reverse=True)
                if case.google_report_status.value == status_value
            ]
            is_bottleneck = status_value != "resolved" and len(grouped_cases) >= 2 and len(grouped_cases) == max_open_count
            columns.append(
                {
                    "status": status_value,
                    "label": label,
                    "context": context,
                    "count": len(grouped_cases),
                    "is_bottleneck": is_bottleneck,
                    "bottleneck_label": (
                        "Cuello de botella actual"
                        if is_bottleneck
                        else "Flujo estable"
                    ),
                    "cards": grouped_cases,
                }
            )
        return columns

    def threat_summary(self) -> dict[str, object]:
        all_cases = self.repository.list_cases()
        cases = self._active_cases()
        by_status = Counter(case.status for case in cases)
        by_source = Counter(case.source_type for case in cases)
        primary_cases = sorted(
            [case for case in cases if case.risk_bucket != RiskBucket.HIGH_RISK_WATCHLIST],
            key=lambda item: (item.risk_score, item.updated_at),
            reverse=True,
        )
        watchlist_cases = sorted(
            [case for case in cases if case.risk_bucket == RiskBucket.HIGH_RISK_WATCHLIST],
            key=lambda item: (item.risk_score, item.updated_at),
            reverse=True,
        )
        archived_cases = sorted(
            [case for case in all_cases if case.status == CaseStatus.DISMISSED],
            key=lambda item: item.updated_at,
            reverse=True,
        )
        cards = [self._threat_card(case) for case in primary_cases]
        watchlist_cards = [self._threat_card(case) for case in watchlist_cases]
        return {
            "cases": cases,
            "cards": cards,
            "watchlist_cards": watchlist_cards,
            "archived_cards": [self._archived_case_card(case) for case in archived_cases[:6]],
            "archived_history": [self._archived_case_card(case) for case in archived_cases],
            "status_counts": by_status,
            "source_counts": by_source,
            "archived_count": len(archived_cases),
            "watchlist_count": len(watchlist_cards),
            "filters": {
                "cities": sorted({card["city"] for card in cards}),
                "statuses": sorted({self._labelize_value(case.status.value) for case in cases}),
                "priorities": ["Critico", "Alto", "Medio", "Bajo"],
            },
        }

    def action_center(self) -> dict[str, object]:
        cases = self._active_cases()
        critical = sorted(cases, key=lambda item: item.risk_score, reverse=True)
        latest_scan = self.repository.list_scans()[0] if self.repository.list_scans() else None
        latest_job = self.repository.list_jobs()[0] if self.repository.list_jobs() else None

        if critical:
            focus_case = critical[0]
            threat_card = self._threat_card(focus_case)
            return {
                "headline": "Lo siguiente que conviene hacer",
                "title": "Abrir el caso más urgente",
                "summary": (
                    f"{focus_case.title} concentra hoy la señal más fuerte en {self._display_city(focus_case.city)}. "
                    "Resolverlo primero reduce riesgo y acelera la decisión de reporte."
                ),
                "primary_action": {
                    "label": "Abrir expediente prioritario",
                    "href": f"/cases/{focus_case.id}",
                },
                "secondary_action": (
                    {
                        "label": "Abrir pin en Google Maps",
                        "href": threat_card["maps_link"],
                    }
                    if threat_card["maps_link"]
                    else None
                ),
                "chips": [
                    f"Riesgo {focus_case.risk_score}",
                    f"Estado {self._labelize_value(focus_case.status.value)}",
                    f"Google {self._labelize_value(focus_case.google_report_status.value)}",
                ],
            }

        return {
            "headline": "Lo siguiente que conviene hacer",
            "title": "Supervisar que el sistema siga cubriendo la red",
            "summary": "No hay amenazas abiertas de alta prioridad. Lo más útil ahora es vigilar la continuidad del monitoreo y revisar el siguiente barrido.",
            "primary_action": {"label": "Ir a Operación", "href": "#operations-panel"},
            "secondary_action": None,
            "chips": [
                f"Último barrido {self._format_when(latest_scan.started_at) if latest_scan else 'pendiente'}",
                latest_job.detail if latest_job and latest_job.detail else "Sin incidencias recientes",
            ],
        }

    def territory_summary(self) -> dict[str, object]:
        dealers = list(self.repository.dealers.values())
        cases = self._active_cases()
        dealer_profiles = {profile.dealer_id: profile for profile in self.repository.profiles.values() if profile.enabled}
        positioned_dealers = self._position_dealers(dealers)
        hotspots = []
        for dealer in positioned_dealers:
            dealer_cases = [case for case in cases if case.dealer_id == dealer["id"]]
            risk_index = max((case.risk_score for case in dealer_cases), default=18)
            hotspots.append(
                {
                    **dealer,
                    "risk_index": risk_index,
                    "active_cases": len(dealer_cases),
                    "critical_cases": len([case for case in dealer_cases if case.risk_score >= 80]),
                    "mode": "GBP" if dealer_profiles.get(dealer["id"], None) and dealer_profiles[dealer["id"]].monitoring_mode == MonitoringMode.GBP_PUSH else "Publico",
                    "comfort": self._comfort_label(
                        dealer_profiles[dealer["id"]].monitoring_mode if dealer["id"] in dealer_profiles else MonitoringMode.PUBLIC_SCAN,
                        dealer_cases,
                    ),
                    "maps_link": self._dealer_maps_link(self.repository.dealers.get(dealer["id"])),
                    "profile_count": 1 if dealer["id"] in dealer_profiles else 0,
                }
            )
        hotspots.sort(key=lambda item: (item["critical_cases"], item["active_cases"], item["risk_index"]), reverse=True)
        municipality_cards = self._municipality_cards(hotspots)
        return {
            "hotspots": hotspots,
            "clusters": municipality_cards,
            "dealer_cards": self._territory_dealer_cards(hotspots),
            "headline": "Cómo se distribuye el riesgo en el Valle de Aburrá",
            "message": "La presión fraudulenta no se reparte igual. Este mapa compara municipios, sedes y puntos en observación para decidir dónde conviene mirar primero.",
        }

    def case_detail(self, case_id: str) -> dict[str, object] | None:
        case = self.repository.get_case(case_id)
        if not case:
            return None
        report = self.repository.get_report(case_id)
        evidence = sorted(
            self.repository.list_evidence_for_case(case_id),
            key=lambda artifact: artifact.created_at,
            reverse=True,
        )
        dealer = self.repository.dealers.get(case.dealer_id)
        profile = next(
            (
                profile
                for profile in self.repository.profiles.values()
                if profile.dealer_id == case.dealer_id and profile.enabled
            ),
            None,
        )
        related_cases = [
            item
            for item in self._active_cases()
            if item.dealer_id == case.dealer_id and item.id != case.id
        ][:4]
        latest_scan = self.repository.list_scans()[0] if self.repository.list_scans() else None
        latest_job = self.repository.list_jobs()[0] if self.repository.list_jobs() else None
        browser_runs = self.repository.list_browser_runs(case_id=case.id)
        latest_browser_run = browser_runs[0] if browser_runs else None
        browser_session = self.repository.get_browser_session(case.organization_id or "") if case.organization_id else None
        browser_state = None
        browser_target = None
        browser_enforcement_reasons: list[str] = []
        try:
            browser_state = self.repository.repository.browser_ops_state(case.id) if hasattr(self.repository, "repository") and hasattr(self.repository.repository, "browser_ops_state") else None
        except Exception:
            browser_state = None
        if browser_state:
            browser_target = browser_state.get("target")
            browser_enforcement_reasons = browser_state.get("reasons") or []
        if not browser_state:
            try:
                from app.services.browser_ops import BrowserEnforcementService

                browser_state = BrowserEnforcementService(self.repository.repository if hasattr(self.repository, "repository") else self.repository).get_case_browser_state(case.id)
                browser_target = browser_state.get("eligibility", {}).get("target")
                browser_enforcement_reasons = browser_state.get("eligibility", {}).get("reasons") or []
            except Exception:
                browser_target = None
                browser_enforcement_reasons = []

        risk_band = self._risk_band(case.risk_score)
        mode_label = "Monitoreo prioritario en GBP" if case.monitoring_mode == MonitoringMode.GBP_PUSH else "Barrido público en Google Maps"
        source_label = self._source_label(case.source_type)
        overview = [
            {"label": "Identificado", "value": self._format_when(case.created_at), "context": "Fecha y hora en que Vigilante abrió este caso o lo registró por primera vez."},
            {"label": "Score de riesgo", "value": str(case.risk_score), "context": risk_band["context"]},
            {"label": "Clasificación operativa", "value": self._risk_bucket_label(case.risk_bucket), "context": self._risk_bucket_context(case.risk_bucket)},
            {
                "label": "Browser enforcement",
                "value": self._labelize_value(case.browser_status.value) if case.browser_status else "Sin iniciar",
                "context": (
                    "Auto-denuncia habilitada para este caso crítico."
                    if case.eligible_for_auto_submit
                    else "Todavía no está en modo auto-denuncia o falta preparación manual."
                ),
            },
            {"label": "Cómo se está vigilando", "value": mode_label, "context": "Canal principal desde el que se detectó o sigue este caso"},
            {"label": "Estado actual del caso", "value": self._labelize_value(case.status.value), "context": "Momento actual del proceso de revisión y decisión"},
            {
                "label": "Estado frente a Google",
                "value": self._labelize_value(case.google_report_status.value),
                "context": case.google_report_response or self._google_status_help(case.google_report_status.value),
            },
        ]

        dealer_snapshot = {
            "name": case.dealer_name,
            "city": case.city,
            "address": dealer.address if dealer else case.location_label,
            "phones": dealer.phone_numbers if dealer else [],
            "influence_label": dealer.influence_label if dealer else None,
            "monitoring_mode": mode_label,
            "monitoring_help": self._monitoring_help(case.monitoring_mode),
            "profile_name": profile.name if profile else "Sin perfil configurado",
        }

        timeline = [
            {
                "label": "Amenaza detectada",
                "time": self._format_when(case.created_at),
                "detail": f"{source_label} detectada para {case.dealer_name}.",
                "tone": "critical",
            },
            {
                "label": "Ultima actualizacion",
                "time": self._format_when(case.updated_at),
                "detail": f"Estado actual: {self._labelize_value(case.status.value)}.",
                "tone": "neutral",
            },
            {
                "label": "Barrido mas reciente",
                "time": self._format_when(latest_scan.started_at) if latest_scan else "Sin barridos",
                "detail": (
                    f"Ultimo scan: {latest_scan.threats_found} amenazas, costo USD {latest_scan.estimated_api_cost_usd:.2f}."
                    if latest_scan
                    else "Todavia no hay scans registrados."
                ),
                "tone": "neutral",
            },
            {
                "label": "Pipeline operativo",
                "time": self._format_when(latest_job.started_at) if latest_job else "Sin jobs",
                "detail": latest_job.detail if latest_job and latest_job.detail else "Sin actividad reciente registrada.",
                "tone": "support",
            },
        ]
        if report:
            timeline.append(
                {
                    "label": "Reporte Google",
                    "time": self._format_when(report.updated_at),
                    "detail": report.response_summary or self._google_status_help(report.status.value),
                    "tone": "support",
                }
            )

        evidence_cards = [
            self._evidence_card(artifact, dealer)
            for artifact in evidence
        ]
        report_brief = self._report_brief(evidence, report)
        clone_comparison = self._clone_comparison(case, evidence, dealer)
        if case.source_type == SourceType.REVIEW_PHOTO:
            primary_evidence = next(
                (item for item in evidence_cards if item["media"]),
                next((item for item in evidence_cards if item["maps_link"]), evidence_cards[0] if evidence_cards else None),
            )
        else:
            primary_evidence = next(
                (item for item in evidence_cards if item["maps_link"] or item["media"]),
                evidence_cards[0] if evidence_cards else None,
            )

        action_cards = [
            {
                "label": "Situación frente a Google",
                "value": self._labelize_value(case.google_report_status.value),
                "context": case.google_report_response or self._google_status_help(case.google_report_status.value),
            },
            {
                "label": "Siguiente acción recomendada",
                "value": self._recommended_action(case.risk_score, case.google_report_status.value, case.risk_bucket),
                "context": "La acción que más valor aporta ahora para proteger a la sede y avanzar el caso.",
            },
            {
                "label": "Cobertura actual de la sede",
                "value": mode_label,
                "context": self._comfort_label(case.monitoring_mode, [case] + related_cases),
            },
            {
                "label": "Browser ops",
                "value": self._labelize_value(case.browser_status.value) if case.browser_status else "Sin iniciar",
                "context": case.browser_last_error or (
                    "El caso puede escalar a denuncia automática."
                    if case.eligible_for_auto_submit
                    else "Solo se preparará o denunciará cuando el caso cumpla las reglas."
                ),
            },
        ]

        decision_summary = [
            {
                "label": "Qué pasó",
                "value": source_label,
                "context": case.summary,
            },
            {
                "label": "Qué conviene hacer ahora",
                "value": self._recommended_action(case.risk_score, case.google_report_status.value, case.risk_bucket),
                "context": risk_band["context"],
            },
            {
                "label": "Qué evidencia ya existe",
                "value": f"{len(evidence_cards)} artefactos",
                "context": "Fotos, OCR, ubicaciones y borradores ya consolidados para validar o reportar el caso.",
            },
        ]

        command_center = self._case_action_plan(case, primary_evidence, report)
        playbook = self._case_playbook(case)

        workflow = self._workflow_steps(case)

        browser_show_action = case.source_type == SourceType.REVIEW_PHOTO
        browser_target_available = bool(browser_target)
        browser_session_active = bool(browser_session and browser_session.status.value == "active")
        browser_manual_submit_ready = bool(browser_session_active and browser_target_available)
        browser_blockers: list[str] = []
        browser_blocker_states: list[dict[str, str]] = []
        if not browser_target_available:
            browser_blockers.append("Todavía no hay un target denunciable resuelto desde la evidencia del caso.")
            browser_blocker_states.append(
                {
                    "label": "Target denunciable",
                    "status": "Pendiente",
                    "detail": "Todavía no hay un target denunciable resuelto desde la evidencia del caso.",
                }
            )
        else:
            browser_blocker_states.append(
                {
                    "label": "Target denunciable",
                    "status": "Listo",
                    "detail": "Vigilante ya encontró un target utilizable para abrir el flujo browser.",
                }
            )
        if not browser_session_active:
            browser_blockers.append("Falta refrescar la sesión del concesionario para poder navegar Google autenticado.")
            browser_blocker_states.append(
                {
                    "label": "Sesión del concesionario",
                    "status": "Bloqueado",
                    "detail": "Falta refrescar la sesión del concesionario para poder navegar Google autenticado.",
                }
            )
        else:
            browser_blocker_states.append(
                {
                    "label": "Sesión del concesionario",
                    "status": "Lista",
                    "detail": "La sesión autenticada del concesionario ya está activa para browser enforcement.",
                }
            )
        if not case.eligible_for_auto_submit:
            browser_blockers.append("El caso aún no está marcado como alta certeza para denuncia guiada.")
            browser_blocker_states.append(
                {
                    "label": "Alta certeza",
                    "status": "Pendiente",
                    "detail": "El caso aún no está marcado como alta certeza para denuncia guiada.",
                }
            )
        else:
            browser_blocker_states.append(
                {
                    "label": "Alta certeza",
                    "status": "Lista",
                    "detail": "El caso ya está marcado como alta certeza para denuncia guiada.",
                }
            )

        browser_panel = {
            "eligible": case.eligible_for_auto_submit,
            "target_available": browser_target_available,
            "session_active": browser_session_active,
            "session_owner": browser_session.auth_user_email if browser_session else None,
            "status_label": self._labelize_value(case.browser_status.value) if case.browser_status else "Sin iniciar",
            "reasons": browser_enforcement_reasons,
            "blockers": browser_blockers,
            "blocker_states": browser_blocker_states,
            "help": (
                "En piloto, la denuncia solo se ejecuta cuando un humano hace clic en denunciar."
                if case.eligible_for_auto_submit
                else "Todavía no cumple el umbral de alta certeza para denuncia guiada."
            ),
            "manual_submit_ready": browser_manual_submit_ready,
            "show_submit_action": browser_show_action,
            "latest_run": self._browser_run_card(latest_browser_run) if latest_browser_run else None,
            "runs": [self._browser_run_card(run) for run in browser_runs[:6]],
        }

        return {
            "case": case,
            "report": report,
            "overview": overview,
            "identified_at": self._format_when(case.created_at),
            "decision_summary": decision_summary,
            "command_center": command_center,
            "playbook": playbook,
            "workflow": workflow,
            "browser_panel": browser_panel,
            "clone_comparison": clone_comparison,
            "dealer_snapshot": dealer_snapshot,
            "timeline": timeline,
            "evidence_cards": evidence_cards,
            "primary_evidence": primary_evidence,
            "report_brief": report_brief,
            "action_cards": action_cards,
            "related_cases": related_cases,
            "risk_band": risk_band,
            "risk_tone": self._risk_tone(case.risk_score),
            "risk_gauge": {
                "score": case.risk_score,
                "remaining": max(0, 100 - case.risk_score),
                "angle": max(6, min(case.risk_score, 100) * 3.6),
                "benchmark": self._risk_benchmark(case.risk_score),
            },
            "source_label": source_label,
            "case_status_label": self._labelize_value(case.status.value),
            "google_status_label": self._labelize_value(case.google_report_status.value),
            "monitoring_mode_label": mode_label,
            "sticky_actions": {
                "primary": command_center["primary_action"],
                "secondary": command_center["secondary_action"],
                "follow_up": command_center["follow_up_action"],
            },
            "follow_up_form": self._case_follow_up_form(case),
        }

    def trust_summary(self) -> dict[str, object]:
        cases = self._active_cases()
        profiles_by_dealer = {profile.dealer_id: profile for profile in self.repository.profiles.values() if profile.enabled}
        covered = []
        for dealer in self.repository.dealers.values():
            profile = profiles_by_dealer.get(dealer.id)
            dealer_cases = [case for case in cases if case.dealer_id == dealer.id]
            phone = dealer.phone_numbers[0] if dealer.phone_numbers else None
            covered.append(
                {
                    "dealer_id": dealer.id,
                    "dealer_name": dealer.name,
                    "city": self._display_city(dealer.city),
                    "mode": "GBP" if profile and profile.monitoring_mode == MonitoringMode.GBP_PUSH else "Publico",
                    "mode_key": "gbp" if profile and profile.monitoring_mode == MonitoringMode.GBP_PUSH else "public",
                    "open_cases": len([case for case in dealer_cases if case.status not in {CaseStatus.DISMISSED}]),
                    "reported_cases": len([case for case in dealer_cases if case.status == CaseStatus.REPORTED]),
                    "confirmed_cases": len([case for case in dealer_cases if case.status == CaseStatus.CONFIRMED]),
                    "comfort_label": self._comfort_label(
                        profile.monitoring_mode if profile else MonitoringMode.PUBLIC_SCAN,
                        dealer_cases,
                    ),
                    "influence_label": dealer.influence_label or self._display_city(dealer.city),
                    "radius_label": f"Radio {int(dealer.influence_radius_km)} km" if dealer.influence_radius_km else "Radio base",
                    "maps_link": self._dealer_maps_link(dealer),
                    "phone_link": f"tel:{phone}" if phone else None,
                    "whatsapp_link": self._whatsapp_link(phone),
                    "phone": phone or "Sin teléfono",
                    "risk_index": max((case.risk_score for case in dealer_cases), default=12),
                    "has_alerts": bool(dealer_cases),
                    "latitude": dealer.latitude,
                    "longitude": dealer.longitude,
                }
            )
        groups = []
        for city in sorted({item["city"] for item in covered}):
            city_dealers = [item for item in covered if item["city"] == city]
            groups.append(
                {
                    "city": city,
                    "dealer_count": len(city_dealers),
                    "open_cases": sum(item["open_cases"] for item in city_dealers),
                    "reported_cases": sum(item["reported_cases"] for item in city_dealers),
                    "gbp_count": sum(1 for item in city_dealers if item["mode"] == "GBP"),
                    "dealers": sorted(city_dealers, key=lambda item: (item["risk_index"], item["open_cases"]), reverse=True),
                }
            )
        return {
            "dealers": covered,
            "groups": groups,
            "message": "La red se monitorea con vigilancia continua sobre Google Business Profile y Google Maps, con trazabilidad clara por concesionario.",
            "table": sorted(
                [
                    {
                        "dealer_id": item["dealer_id"],
                        "dealer_name": item["dealer_name"],
                        "city": item["city"],
                        "phone": item["phone"],
                        "mode": item["mode"],
                        "mode_key": item["mode_key"],
                        "last_scan": self._format_when(self.repository.list_scans()[0].started_at) if self.repository.list_scans() else "Sin barrido",
                        "maps_link": item["maps_link"],
                        "risk_index": item["risk_index"],
                        "has_alerts": item["has_alerts"],
                    }
                    for item in covered
                ],
                key=lambda item: (item["risk_index"], item["dealer_name"]),
                reverse=True,
            ),
        }

    @staticmethod
    def _comfort_label(mode, dealer_cases):
        if mode == MonitoringMode.GBP_PUSH and not dealer_cases:
            return "Cobertura prioritaria en tiempo casi real sobre Google Business Profile"
        if mode == MonitoringMode.GBP_PUSH:
            return "Bajo observación prioritaria en Google Business Profile"
        if dealer_cases:
            return "Escaneo público en Google Maps con seguimiento activo"
        return "Cobertura preventiva sin eventos críticos recientes"

    def all_sections(self) -> dict[str, object]:
        return {
            "executive": self.executive_summary(),
            "action_center": self.action_center(),
            "territory": self.territory_summary(),
            "operations": self.operations_summary(),
            "threats": self.threat_summary(),
            "trust": self.trust_summary(),
        }

    def _critical_cards(self, cases):
        cards = []
        for case in sorted(cases, key=lambda item: (item.risk_score, item.updated_at), reverse=True)[:4]:
            cards.append(
                {
                    "id": case.id,
                    "title": case.title,
                    "city": self._display_city(case.city),
                    "risk_score": case.risk_score,
                    "risk_label": self._risk_band(case.risk_score)["label"],
                    "risk_tone": self._risk_tone(case.risk_score),
                    "action": self._recommended_action(case.risk_score, case.google_report_status.value, case.risk_bucket),
                    "status": self._labelize_value(case.status.value),
                    "google_status": self._labelize_value(case.google_report_status.value),
                    "reasons": case.risk_reasons[:3],
                }
            )
        return cards

    @staticmethod
    def _artifact_summary(artifact_type: str, content: dict[str, object]) -> str:
        if artifact_type == "observed_place":
            name = content.get("name", "Punto observado")
            phone = content.get("phone_number") or "sin telefono visible"
            address = content.get("address", "sin direccion")
            return f"{name} · {phone} · {address}"
        if artifact_type == "observed_asset":
            source = content.get("media_origin")
            text = content.get("ocr_text") or content.get("extracted_text") or content.get("review_text")
            phones = content.get("detected_phone_numbers") or []
            if source == "gbp_customer_media":
                prefix = "Foto pública del perfil oficial"
            elif content.get("ingestion_mode") == "experimental_browser_capture":
                prefix = "Captura experimental del perfil oficial"
            else:
                prefix = "Evento observado"
            if text and phones:
                return f"{prefix} · OCR: {str(text)[:110]} · Telefonos: {', '.join(str(item) for item in phones[:2])}"
            if text:
                return f"{prefix} · OCR: {str(text)[:150]}"
            status = content.get("download_status", "sin estado")
            return f"{prefix} · captura {status}"
        if artifact_type == "google_report_draft":
            status = content.get("status", "drafted")
            report_url = content.get("report_url", "sin enlace")
            return f"{status} · {report_url}"
        if artifact_type == "browser_enforcement_run":
            status = content.get("status", "sin estado")
            mode = content.get("execution_mode", "sin modo")
            target = content.get("target_type", "asset")
            return f"{status} · {mode} · {target}"
        return "Evidencia consolidada para investigacion."

    def _browser_run_card(self, run):
        if not run:
            return None
        return {
            "id": run.id,
            "status_label": self._labelize_value(run.status.value),
            "status_value": run.status.value,
            "execution_mode_label": self._labelize_value(run.execution_mode.value),
            "flow_type_label": self._labelize_value(run.flow_type.value),
            "started_at": self._format_when(run.started_at),
            "finished_at": self._format_when(run.finished_at) if run.finished_at else "En curso",
            "target_url": run.target_url,
            "target_type": run.target_type,
            "screenshots": run.screenshots,
            "error_detail": run.error_detail,
            "audit_log": run.audit_log[-5:],
        }

    @staticmethod
    def _report_brief(evidence, report):
        draft = next((artifact for artifact in evidence if artifact.artifact_type == "google_report_draft"), None)
        content = (draft.content if draft else None) or {}
        if not content and not report:
            return None
        report_url = content.get("report_url") or (report.report_url if report else None)
        official_phone_numbers = content.get("official_phone_numbers") or []
        suspicious_phone_numbers = content.get("suspicious_phone_numbers") or []
        return {
            "title": content.get("report_title") or "Borrador listo para Google",
            "summary": content.get("summary") or (report.response_summary if report else "Borrador listo para revisión humana antes del envío."),
            "executive_summary": content.get("executive_summary"),
            "policy_basis": content.get("policy_basis"),
            "official_phone": content.get("official_phone") or (official_phone_numbers[0] if official_phone_numbers else "Sin teléfono oficial"),
            "suspicious_phone": content.get("suspicious_phone") or (suspicious_phone_numbers[0] if suspicious_phone_numbers else "Sin teléfono sospechoso"),
            "official_phone_numbers": official_phone_numbers,
            "suspicious_phone_numbers": suspicious_phone_numbers,
            "requested_action": content.get("requested_action"),
            "submission_notes": content.get("submission_notes") or [],
            "copy_ready_text": content.get("copy_ready_text"),
            "evidence_links": content.get("evidence_links") or [],
            "source_links": content.get("source_links") or [],
            "report_url": report_url,
        }

    def _dealer_phone_by_name(self, dealer_name: str) -> str:
        for dealer in self.repository.dealers.values():
            if dealer.name == dealer_name:
                return dealer.phone_numbers[0] if dealer.phone_numbers else "Sin teléfono"
        return "Sin teléfono"

    def _threat_card(self, case):
        dealer = self.repository.dealers.get(case.dealer_id)
        evidence = [
            self.repository.evidence[evidence_id]
            for evidence_id in case.evidence_ids
            if evidence_id in self.repository.evidence
        ]
        primary = evidence[0] if evidence else None
        media = self._evidence_visual(primary.content, primary.label) if primary else None
        maps_link = self._maps_link(primary.content) if primary else None
        return {
            "case": case,
            "evidence_badges": [artifact.artifact_type for artifact in evidence],
            "maps_link": maps_link,
            "dealer_maps_link": self._dealer_maps_link(dealer),
            "media": media,
            "identified_at": self._format_when(case.created_at),
            "observed_name": self._observed_name(primary),
            "source_label": self._source_label(case.source_type),
            "risk_bucket_label": self._risk_bucket_label(case.risk_bucket),
            "risk_bucket_tone": self._risk_bucket_tone(case.risk_bucket),
            "case_status_label": self._labelize_value(case.status.value),
            "google_status_label": self._labelize_value(case.google_report_status.value),
            "recommended_action": self._recommended_action(case.risk_score, case.google_report_status.value, case.risk_bucket),
            "priority_label": self._risk_band(case.risk_score)["label"],
            "visual_tone": self._risk_tone(case.risk_score, case.risk_bucket),
            "city": self._display_city(case.city),
            "dealer_id": case.dealer_id,
            "monitoring_mode_label": "GBP" if case.monitoring_mode == MonitoringMode.GBP_PUSH else "Publico",
        }

    def _archived_case_card(self, case):
        return {
            "id": case.id,
            "title": case.title,
            "dealer_name": case.dealer_name,
            "city": self._display_city(case.city),
            "source_label": self._source_label(case.source_type),
            "archived_at": self._format_when(case.updated_at),
            "summary": case.summary,
            "risk_score": case.risk_score,
        }

    def _alert_feed(self, cases):
        feed = []
        for case in sorted(cases, key=lambda item: (item.risk_score, item.updated_at), reverse=True)[:5]:
            feed.append(
                {
                    "id": case.id,
                    "title": case.title,
                    "dealer_name": case.dealer_name,
                    "city": self._display_city(case.city),
                    "risk_score": case.risk_score,
                    "tone": self._risk_tone(case.risk_score, case.risk_bucket),
                    "priority": self._risk_band(case.risk_score)["label"],
                    "risk_bucket_label": self._risk_bucket_label(case.risk_bucket),
                    "source_label": self._source_label(case.source_type),
                    "alert_type": self._source_label(case.source_type),
                    "google_status": self._labelize_value(case.google_report_status.value),
                    "google_status_value": case.google_report_status.value,
                    "google_status_tone": self._google_flow_tone(case.google_report_status.value),
                    "action": self._recommended_action(case.risk_score, case.google_report_status.value, case.risk_bucket),
                }
            )
        return feed

    def _municipality_cards(self, hotspots):
        grouped = defaultdict(list)
        for hotspot in hotspots:
            grouped[hotspot["city"]].append(hotspot)

        cards = []
        for city, items in grouped.items():
            risk_index = max(item["risk_index"] for item in items)
            active_cases = sum(item["active_cases"] for item in items)
            critical_cases = sum(item["critical_cases"] for item in items)
            gbp_count = sum(1 for item in items if item["mode"] == "GBP")
            cards.append(
                {
                    "city": city,
                    "dealer_count": len(items),
                    "active_cases": active_cases,
                    "critical_cases": critical_cases,
                    "risk_index": risk_index,
                    "risk_tone": self._risk_tone(risk_index),
                    "coverage_label": f"{gbp_count} con GBP · {len(items) - gbp_count} en público",
                    "summary": self._municipality_summary(city, active_cases, critical_cases, risk_index),
                }
            )
        return sorted(cards, key=lambda item: (item["critical_cases"], item["active_cases"], item["risk_index"]), reverse=True)

    def _territory_dealer_cards(self, hotspots):
        cards = []
        for hotspot in hotspots:
            cards.append(
                {
                    "id": hotspot["id"],
                    "name": hotspot["name"],
                    "city": self._display_city(hotspot["city"]),
                    "mode": hotspot["mode"],
                    "active_cases": hotspot["active_cases"],
                    "risk_index": hotspot["risk_index"],
                    "risk_tone": self._risk_tone(hotspot["risk_index"]),
                    "influence_label": hotspot.get("address") or self._display_city(hotspot["city"]),
                    "radius_label": self.repository.dealers[hotspot["id"]].influence_label or self._display_city(hotspot["city"]),
                    "maps_link": hotspot["maps_link"],
                }
            )
        return cards

    @staticmethod
    def _municipality_summary(city: str, active_cases: int, critical_cases: int, risk_index: int) -> str:
        if critical_cases:
            return f"{city} concentra la mayor presión visible y conviene revisarlo primero."
        if active_cases:
            return f"{city} tiene señales activas en seguimiento y necesita revisión priorizada."
        if risk_index >= 45:
            return f"{city} mantiene vigilancia preventiva por señales todavía no críticas."
        return f"{city} se ve estable en este momento, con cobertura preventiva activa."

    @staticmethod
    def _risk_benchmark(risk_score: int) -> str:
        if risk_score >= 85:
            return "100 es el máximo de urgencia y este caso ya está en zona crítica."
        if risk_score >= 70:
            return "Este score ya supera el umbral de triage fuerte y pide decisión rápida."
        if risk_score >= 45:
            return "Todavía no es crítico, pero sí suficientemente serio para revisión humana."
        return "Permanece en seguimiento preventivo sin urgencia alta."

    @staticmethod
    def _whatsapp_link(phone: str | None):
        if not phone:
            return None
        digits = "".join(char for char in phone if char.isdigit())
        if not digits:
            return None
        if not digits.startswith("57") and len(digits) == 10:
            digits = f"57{digits}"
        return f"https://wa.me/{digits}"

    @staticmethod
    def _display_city(city: str | None) -> str:
        if not city:
            return "Sin ciudad"
        return (
            city.strip()
            .replace("Medellin", "Medellín")
            .replace("Itagui", "Itagüí")
        )

    def _job_card(self, job):
        return {
            "type_label": self._job_type_label(job.job_type),
            "status_label": self._job_status_label(job.job_status),
            "detail": job.detail or "Sin novedad registrada.",
            "cost_label": f"USD {job.estimated_api_cost_usd:.2f}",
        }

    def _evidence_card(self, artifact, dealer):
        maps_label = "Abrir ficha en Google Maps"
        dealer_maps_label = "Ver sede oficial"
        if artifact.artifact_type == "observed_place":
            maps_label = "Abrir ficha del clon"
            dealer_maps_label = "Abrir ficha oficial"
        return {
            "id": artifact.id,
            "type": artifact.artifact_type,
            "label": artifact.label,
            "created_at": self._format_when(artifact.created_at),
            "summary": self._artifact_summary(artifact.artifact_type, artifact.content),
            "content": artifact.content,
            "media": self._evidence_visual(artifact.content, artifact.label),
            "maps_link": self._maps_link(artifact.content),
            "maps_link_label": maps_label,
            "dealer_maps_link": self._dealer_maps_link(dealer),
            "dealer_maps_link_label": dealer_maps_label,
        }

    @staticmethod
    def _observed_name(artifact) -> str | None:
        if not artifact:
            return None
        if artifact.label:
            return artifact.label
        if artifact.content:
            name = artifact.content.get("name")
            if name:
                return str(name)
        return None

    @staticmethod
    def _place_maps_link(name: str | None = None, address: str | None = None, place_id: str | None = None, google_maps_uri: str | None = None):
        if google_maps_uri and DashboardService._is_precise_maps_link(str(google_maps_uri)):
            return google_maps_uri
        if place_id:
            return DashboardService._place_id_maps_link(name, address, str(place_id))
        if google_maps_uri and not DashboardService._is_generic_maps_landing(str(google_maps_uri)):
            return google_maps_uri
        query = " ".join(part for part in [str(name or ""), str(address or "")] if part).strip()
        if query:
            return f"https://www.google.com/maps/search/?api=1&query={quote(query)}"
        if google_maps_uri:
            return google_maps_uri
        return None

    def _resolve_dealer_place_link(self, dealer):
        if not dealer or dealer.id in self._dealer_maps_link_cache:
            return self._dealer_maps_link_cache.get(dealer.id if dealer else "")
        resolved = None
        if places_search_service.is_configured():
            query = " ".join(part for part in [dealer.name, dealer.address, dealer.city, "Colombia"] if part).strip()
            try:
                results = places_search_service.search_text(query)
            except Exception:
                results = []
            if results:
                best = results[0]
                raw_uri = (best.raw_payload or {}).get("googleMapsUri")
                resolved = self._place_maps_link(best.name, best.address, best.place_id, raw_uri)
        self._dealer_maps_link_cache[dealer.id] = resolved
        return resolved

    def _dealer_maps_link(self, dealer, prefer_resolution: bool = False):
        if not dealer:
            return None
        profile = next(
            (
                item
                for item in self.repository.profiles.values()
                if item.enabled and item.dealer_id == dealer.id and item.google_place_id
            ),
            None,
        )
        if profile and profile.google_place_id:
            return self._place_maps_link(dealer.name, dealer.address, profile.google_place_id)
        if prefer_resolution:
            resolved = self._resolve_dealer_place_link(dealer)
            if resolved:
                return resolved
        if getattr(dealer, "name", None):
            query = f"{dealer.name} {dealer.address} {dealer.city} Colombia".strip()
            return f"https://www.google.com/maps/search/?api=1&query={quote(query)}"
        if dealer.latitude is not None and dealer.longitude is not None:
            return f"https://www.google.com/maps?q={dealer.latitude},{dealer.longitude}"
        return f"https://www.google.com/maps/search/?api=1&query={quote(dealer.address)}"

    @staticmethod
    def _maps_link(content: dict[str, object] | None):
        if not content:
            return None
        raw_payload = content.get("raw_payload") if isinstance(content.get("raw_payload"), dict) else {}
        google_maps_uri = str(content.get("google_maps_uri") or raw_payload.get("googleMapsUri") or "")
        place_id = content.get("place_id") or raw_payload.get("placeId")
        if google_maps_uri and not place_id:
            place_id = DashboardService._place_id_from_maps_link(google_maps_uri)
        name = content.get("name") or content.get("address") or "Ubicacion observada"
        address = content.get("address")
        if google_maps_uri and DashboardService._is_precise_maps_link(google_maps_uri):
            return google_maps_uri
        if place_id:
            return DashboardService._place_maps_link(str(name), str(address or ""), str(place_id))
        google_maps_uri = content.get("source_page_url")
        if google_maps_uri and DashboardService._is_precise_maps_link(str(google_maps_uri)):
            return str(google_maps_uri)
        if google_maps_uri and not DashboardService._is_generic_maps_landing(str(google_maps_uri)):
            return str(google_maps_uri)
        if name or address:
            query = " ".join(part for part in [str(name), str(address or "")] if part).strip()
            if query:
                return f"https://www.google.com/maps/search/?api=1&query={quote(query)}"
        return DashboardService._coordinate_maps_link(content, raw_payload)

    @staticmethod
    def _coordinate_maps_link(content: dict[str, object], raw_payload: dict[str, object] | None = None) -> str | None:
        raw_payload = raw_payload or {}
        location = raw_payload.get("location") if isinstance(raw_payload.get("location"), dict) else {}
        latitude = content.get("latitude") or location.get("latitude")
        longitude = content.get("longitude") or location.get("longitude")
        if latitude is None or longitude is None:
            return None
        return f"https://www.google.com/maps/search/?api=1&query={quote(f'{latitude},{longitude}')}"

    @staticmethod
    def _place_id_maps_link(name: str | None, address: str | None, place_id: str) -> str:
        query = " ".join(part for part in [str(name or ""), str(address or "")] if part).strip() or "Google Maps"
        return f"https://www.google.com/maps/search/?api=1&query={quote(query)}&query_place_id={quote(place_id)}"

    @staticmethod
    def _place_id_from_maps_link(url: str) -> str | None:
        parsed = urlparse(url)
        query = parse_qs(parsed.query)
        query_place_id = query.get("query_place_id", [""])[0]
        if query_place_id:
            return query_place_id
        for key in ("q",):
            value = query.get(key, [""])[0]
            if value.startswith("place_id:"):
                return value.removeprefix("place_id:")
        return None

    @staticmethod
    def _is_precise_maps_link(url: str) -> bool:
        parsed = urlparse(url)
        query = parse_qs(parsed.query)
        if query.get("cid", [""])[0]:
            return True
        if query.get("query_place_id", [""])[0]:
            return True
        if query.get("q", [""])[0].startswith("place_id:"):
            return True
        return "/maps/place" in parsed.path

    @staticmethod
    def _is_generic_maps_landing(url: str) -> bool:
        parsed = urlparse(url)
        path = parsed.path
        if "/maps/@" in path:
            return True
        if path.rstrip("/") in {"/maps", "/maps/search"} and "query_place_id=" not in parsed.query and "place_id:" not in parsed.query:
            return True
        return False

    def _clone_comparison(self, case, evidence, dealer):
        if case.source_type != SourceType.PLACE_CLONE:
            return None
        observed = next((artifact for artifact in evidence if artifact.artifact_type == "observed_place"), None)
        if not observed:
            return None
        content = observed.content or {}
        official_name = dealer.name if dealer else case.dealer_name
        official_address = dealer.address if dealer else case.location_label
        official_phones = dealer.phone_numbers if dealer else []
        clone_name = content.get("name") or observed.label or "Punto sospechoso"
        clone_address = content.get("address") or "Sin dirección visible"
        clone_phone = content.get("phone_number") or "Sin teléfono visible"
        query_hits = content.get("query_hits") or []
        source_query = content.get("source_query")
        distance_m = None
        if dealer and content.get("latitude") is not None and content.get("longitude") is not None and dealer.latitude is not None and dealer.longitude is not None:
            distance_m = self._distance_meters(
                float(content["latitude"]),
                float(content["longitude"]),
                float(dealer.latitude),
                float(dealer.longitude),
            )
        reasons = case.risk_reasons[:4]
        return {
            "clone_name": clone_name,
            "clone_address": clone_address,
            "clone_phone": clone_phone,
            "clone_category": content.get("category") or "Sin categoría visible",
            "clone_rating": content.get("rating"),
            "clone_reviews": content.get("user_rating_count"),
            "clone_maps_link": self._maps_link(content),
            "official_name": official_name,
            "official_address": official_address,
            "official_phones": official_phones,
            "official_maps_link": self._dealer_maps_link(dealer, prefer_resolution=True),
            "source_query": source_query,
            "query_hits": query_hits,
            "distance_m": distance_m,
            "reasons": reasons,
        }

    @staticmethod
    def _distance_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> int:
        from math import asin, cos, radians, sin, sqrt

        dlat = radians(lat2 - lat1)
        dlon = radians(lon2 - lon1)
        lat1r = radians(lat1)
        lat2r = radians(lat2)
        a = sin(dlat / 2) ** 2 + cos(lat1r) * cos(lat2r) * sin(dlon / 2) ** 2
        return int(6371000 * 2 * asin(sqrt(a)))

    def _evidence_visual(self, content: dict[str, object] | None, label: str):
        if not content:
            return None
        image_url = content.get("internal_image_url") or content.get("captured_image_url") or content.get("image_url")
        extracted_text = content.get("ocr_text") or content.get("extracted_text") or content.get("review_text")
        if image_url:
            source = content.get("media_origin")
            caption = (
                "Copia preservada de foto pública del perfil oficial para validación humana"
                if source == "gbp_customer_media"
                else "Foto observada para validacion humana"
            )
            return {"kind": "image", "url": image_url, "caption": caption}
        if extracted_text:
            preview = self._preview_svg(
                title=label,
                subtitle="Reconstruccion visual basada en OCR",
                suspect_text=str(extracted_text),
            )
            return {"kind": "reconstruction", "url": preview, "caption": "Vista reconstruida a partir del texto extraido"}
        return None

    @staticmethod
    def _preview_svg(title: str, subtitle: str, suspect_text: str) -> str:
        safe_title = DashboardService._svg_escape(title[:32])
        safe_subtitle = DashboardService._svg_escape(subtitle[:46])
        safe_text = DashboardService._svg_escape(suspect_text[:42])
        svg = f"""
        <svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 620 420'>
          <defs>
            <linearGradient id='bg' x1='0' y1='0' x2='1' y2='1'>
              <stop offset='0%' stop-color='#f6efe6'/>
              <stop offset='100%' stop-color='#ead9c3'/>
            </linearGradient>
          </defs>
          <rect width='620' height='420' rx='34' fill='url(#bg)'/>
          <rect x='48' y='70' width='524' height='292' rx='26' fill='#fdf9f3' stroke='#d8c1a7' stroke-width='3'/>
          <rect x='88' y='120' width='444' height='78' rx='20' fill='#50311f'/>
          <text x='310' y='168' text-anchor='middle' font-size='30' font-family='Verdana' fill='#fff3e4'>{safe_title}</text>
          <text x='310' y='226' text-anchor='middle' font-size='20' font-family='Verdana' fill='#7b5b43'>{safe_subtitle}</text>
          <rect x='124' y='252' width='372' height='56' rx='16' fill='#f6dfcf' stroke='#cc8b63' stroke-width='2'/>
          <text x='310' y='289' text-anchor='middle' font-size='28' font-family='Verdana' font-weight='700' fill='#ad2f1e'>{safe_text}</text>
        </svg>
        """
        return f"data:image/svg+xml;charset=UTF-8,{quote(svg)}"

    @staticmethod
    def _svg_escape(value: str) -> str:
        return (
            value.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&apos;")
        )

    @staticmethod
    def _source_label(source_type: SourceType) -> str:
        mapping = {
            SourceType.PLACE_CLONE: "Posible clon en Google Maps",
            SourceType.REVIEW_PHOTO: "Foto sospechosa en media pública",
            SourceType.OFFICIAL_PROFILE_UPDATE: "Actualizacion sospechosa en perfil oficial",
        }
        return mapping.get(source_type, str(source_type))

    @staticmethod
    def _risk_band(risk_score: int) -> dict[str, str]:
        if risk_score >= 85:
            return {"label": "Critico", "context": "Debe atenderse de inmediato con reporte priorizado."}
        if risk_score >= 70:
            return {"label": "Alto", "context": "Hay evidencia suficiente para triage y consolidacion."}
        if risk_score >= 45:
            return {"label": "Medio", "context": "Requiere validacion antes de escalarlo a Google."}
        return {"label": "Bajo", "context": "Mantener en observacion sin alarmar a negocio."}

    @staticmethod
    def _risk_tone(risk_score: int, risk_bucket: RiskBucket = RiskBucket.CLONE_RISK) -> str:
        if risk_bucket == RiskBucket.HIGH_RISK_WATCHLIST:
            return "risk-watchlist"
        if risk_score >= 85:
            return "risk-critical"
        if risk_score >= 70:
            return "risk-high"
        if risk_score >= 45:
            return "risk-medium"
        return "risk-low"

    @staticmethod
    def _recommended_action(risk_score: int, report_status: str, risk_bucket: RiskBucket = RiskBucket.CLONE_RISK) -> str:
        if report_status == "resolved":
            return "Mantener trazabilidad y cerrar seguimiento"
        if report_status in {"submitted", "acknowledged"}:
            return "Hacer seguimiento al expediente"
        if risk_bucket == RiskBucket.HIGH_RISK_WATCHLIST:
            return "Validar manualmente antes de escalar"
        if risk_score >= 85:
            return "Confirmar y reportar hoy"
        if risk_score >= 70:
            return "Validar evidencia y preparar reporte"
        return "Mantener en observacion"

    @staticmethod
    def _monitoring_help(mode: MonitoringMode) -> str:
        if mode == MonitoringMode.GBP_PUSH:
            return "Monitoreo prioritario sobre el perfil oficial del concesionario."
        return "Seguimiento a partir de señales visibles en Google Maps y barridos publicos."

    def _case_action_plan(self, case, primary_evidence, report):
        return {
            "headline": "Siguiente mejor acción",
            "title": self._recommended_action(case.risk_score, case.google_report_status.value, case.risk_bucket),
            "summary": self._command_summary(case),
            "primary_action": self._case_primary_action(case, primary_evidence, report),
            "secondary_action": self._case_secondary_action(case, primary_evidence, report),
            "follow_up_action": self._case_follow_up_action(case),
            "status_suggestion": self._case_status_suggestion(case),
        }

    def _case_primary_action(self, case, primary_evidence, report):
        if case.google_report_status.value == "resolved":
            return {"label": "Ver trazabilidad del caso", "href": "#follow-up"}
        if case.status == CaseStatus.REPORTED or case.google_report_status.value in {"submitted", "acknowledged"}:
            if report and report.report_url:
                return {"label": "Abrir gestión con Google", "href": report.report_url}
            return {"label": "Ir al seguimiento con Google", "href": "#follow-up"}
        if case.status == CaseStatus.CONFIRMED:
            if report and report.report_url:
                return {"label": "Abrir borrador para Google", "href": report.report_url}
            return {"label": "Preparar reporte para Google", "href": "#follow-up"}
        if case.status == CaseStatus.TRIAGED:
            return {"label": "Revisar prueba principal", "href": "#evidence"}
        if primary_evidence and primary_evidence.get("maps_link"):
            return {"label": "Abrir evidencia en Maps", "href": primary_evidence["maps_link"]}
        return {"label": "Ir a prueba principal", "href": "#evidence"}

    def _case_secondary_action(self, case, primary_evidence, report):
        if case.google_report_status.value == "resolved":
            if primary_evidence and primary_evidence.get("dealer_maps_link"):
                return {"label": "Abrir sede oficial", "href": primary_evidence["dealer_maps_link"]}
            return None
        if case.status == CaseStatus.REPORTED or case.google_report_status.value in {"submitted", "acknowledged"}:
            if primary_evidence and primary_evidence.get("maps_link"):
                return {"label": "Ver punto reportado en Maps", "href": primary_evidence["maps_link"]}
            return None
        if case.status == CaseStatus.CONFIRMED:
            if primary_evidence and primary_evidence.get("maps_link"):
                return {"label": "Contrastar punto sospechoso", "href": primary_evidence["maps_link"]}
            return {"label": "Ir a evidencia consolidada", "href": "#evidence"}
        if case.status == CaseStatus.TRIAGED:
            return {"label": "Actualizar decisión del caso", "href": "#follow-up"}
        if primary_evidence and primary_evidence.get("dealer_maps_link"):
            return {"label": "Abrir sede oficial", "href": primary_evidence["dealer_maps_link"]}
        if report and report.report_url:
            return {"label": "Abrir borrador para Google", "href": report.report_url}
        return {"label": "Actualizar seguimiento", "href": "#follow-up"}

    def _case_follow_up_action(self, case):
        if case.status == CaseStatus.DISMISSED:
            return {"label": "Caso archivado para consulta", "href": "#follow-up"}
        if case.google_report_status.value == "resolved":
            return {"label": "Cerrar seguimiento interno", "href": "#follow-up"}
        if case.status == CaseStatus.REPORTED or case.google_report_status.value in {"submitted", "acknowledged"}:
            return {"label": "Registrar respuesta de Google", "href": "#follow-up"}
        if case.risk_bucket == RiskBucket.HIGH_RISK_WATCHLIST and case.status == CaseStatus.NEW:
            return {"label": "Validar o archivar la watchlist", "href": "#follow-up"}
        if case.status == CaseStatus.CONFIRMED:
            return {"label": "Marcar como reportado", "href": "#follow-up"}
        if case.status == CaseStatus.TRIAGED:
            return {"label": "Confirmar o archivar el caso", "href": "#follow-up"}
        return {"label": "Pasar el caso a evaluación", "href": "#follow-up"}

    def _case_status_suggestion(self, case):
        if case.status == CaseStatus.DISMISSED:
            return "dismissed"
        if case.google_report_status.value == "resolved":
            return "reported"
        if case.status == CaseStatus.REPORTED or case.google_report_status.value in {"submitted", "acknowledged"}:
            return "reported"
        if case.risk_bucket == RiskBucket.HIGH_RISK_WATCHLIST and case.status == CaseStatus.NEW:
            return "triaged"
        if case.status == CaseStatus.CONFIRMED:
            return "reported"
        if case.status == CaseStatus.TRIAGED:
            return "confirmed"
        return "triaged"

    def _case_follow_up_form(self, case):
        if case.status == CaseStatus.DISMISSED:
            return {
                "label": "Caso archivado por falso positivo o descarte",
                "help": "El caso ya salió de la vista principal. Puedes dejarlo archivado para consulta futura o reabrirlo si aparece nueva evidencia.",
                "submit_label": "Guardar estado del caso",
            }
        if case.google_report_status.value == "resolved":
            return {
                "label": "Dejar cierre y trazabilidad del caso",
                "help": "Usa este paso para dejar constancia final y mantener vigilancia por si la amenaza reaparece.",
                "submit_label": "Guardar cierre del caso",
            }
        if case.status == CaseStatus.REPORTED or case.google_report_status.value in {"submitted", "acknowledged"}:
            return {
                "label": "Registrar seguimiento con Google",
                "help": "Actualiza aquí el caso cuando recibas respuesta, cambio visible o nueva evidencia desde Google Maps o Google Business Profile.",
                "submit_label": "Guardar seguimiento con Google",
            }
        if case.risk_bucket == RiskBucket.HIGH_RISK_WATCHLIST and case.status == CaseStatus.NEW:
            return {
                "label": "Validar la watchlist antes de escalar",
                "help": "Este caso entró como watchlist de alto riesgo. Úsalo para confirmar si realmente debe escalar a clon confirmado o archivarse como falso positivo.",
                "submit_label": "Guardar validación de watchlist",
            }
        if case.status == CaseStatus.CONFIRMED:
            return {
                "label": "Preparar el paso a reporte",
                "help": "El caso ya está confirmado. Usa este control para dejarlo listo como reportado cuando la gestión hacia Google ya esté preparada.",
                "submit_label": "Guardar paso a reporte",
            }
        if case.status == CaseStatus.TRIAGED:
            return {
                "label": "Confirmar la decisión del caso",
                "help": "Después de revisar evidencia, usa este control para dejar el caso confirmado o archivado sin retrabajo.",
                "submit_label": "Guardar decisión del caso",
            }
        return {
            "label": "Mover el caso a la siguiente etapa",
            "help": "Usa este control para pasar la alerta a evaluación formal o archivarla si la evidencia no se sostiene.",
            "submit_label": "Guardar siguiente paso",
        }

    def _command_summary(self, case):
        if case.google_report_status.value == "resolved":
            return "Google ya cerró o resolvió el caso. Conviene conservar la trazabilidad, verificar que la amenaza no reaparezca y cerrar seguimiento interno."
        if case.risk_bucket == RiskBucket.HIGH_RISK_WATCHLIST:
            return "Este caso quedó en watchlist de alto riesgo: la señal es preocupante y visible, pero primero debe pasar por validación humana antes de escalarse como clon confirmado."
        if case.status == CaseStatus.REPORTED:
            return "El caso ya fue reportado. Ahora lo más valioso es seguir la respuesta de Google y documentar cualquier cambio visible en Maps o GBP."
        if case.status == CaseStatus.CONFIRMED:
            return "La red ya considera este caso real. Conviene consolidar el expediente y moverlo a reporte sin perder tiempo en análisis que ya no cambian la decisión."
        if case.status == CaseStatus.TRIAGED:
            return "El caso ya está en evaluación. Ahora hay que cerrar criterio con la evidencia disponible para decidir si se confirma o se archiva."
        if case.risk_score >= 85:
            return "Este caso ya tiene suficiente señal para priorizar una validación humana rápida y preparar el reporte sin esperar otro barrido."
        if case.risk_score >= 70:
            return "La evidencia ya justifica triage. Conviene verificar la ubicación, revisar la prueba visual y decidir si pasa a confirmado."
        return "El caso merece seguimiento, pero todavía necesita más validación antes de escalarlo."

    def _case_playbook(self, case):
        if case.google_report_status.value == "resolved":
            return {
                "label": "Caso resuelto",
                "headline": "Cerrar seguimiento interno y vigilar reaparición",
                "summary": "La prioridad ya no es demostrar el fraude, sino confirmar que la remediación siga visible y que la amenaza no vuelva a aparecer.",
                "checks": [
                    "Verificar que el cambio ya sea visible en Google Maps o GBP.",
                    "Guardar la respuesta final como trazabilidad.",
                    "Dejar el caso listo para cierre interno.",
                ],
            }
        if case.status == CaseStatus.REPORTED or case.google_report_status.value in {"submitted", "acknowledged"}:
            return {
                "label": "Caso reportado",
                "headline": "Hacer seguimiento y registrar respuesta de Google",
                "summary": "La amenaza ya fue elevada. Ahora el operador debe evitar retrabajo y concentrarse en seguimiento, respuesta y evidencia de cambio.",
                "checks": [
                    "Revisar si Google ya respondió o pidió contexto adicional.",
                    "Registrar cualquier cambio visible en la ficha o el contenido reportado.",
                    "Mantener el expediente listo hasta cierre o resolución.",
                ],
            }
        if case.status == CaseStatus.CONFIRMED:
            return {
                "label": "Caso confirmado",
                "headline": "Preparar reporte y escalar sin demoras",
                "summary": "La validación interna ya está hecha. Lo que sigue es convertir esa certeza en una gestión clara frente a Google.",
                "checks": [
                    "Confirmar que la evidencia principal sea suficiente y legible.",
                    "Abrir o completar el borrador de reporte.",
                    "Mover el caso a reportado cuando el envío esté listo.",
                ],
            }
        if case.status == CaseStatus.TRIAGED:
            return {
                "label": "Caso en evaluación",
                "headline": "Cerrar criterio: confirmar o archivar",
                "summary": "Aquí el operador ya no necesita más contexto general, sino resolver si la señal es real y amerita reporte.",
                "checks": [
                    "Contrastar evidencia visual, ubicación y teléfono.",
                    "Definir si la amenaza es real o si debe archivarse.",
                    "Si se confirma, dejar listo el reporte.",
                ],
            }
        return {
            "label": "Caso nuevo",
            "headline": "Validar rápido si esta alerta merece escalarse",
            "summary": "Este es un caso recién abierto. La misión del operador es revisar la evidencia principal y decidir si pasa a evaluación formal.",
            "checks": [
                "Revisar la prueba principal antes de bajar a detalles secundarios.",
                "Comparar el punto sospechoso contra la sede oficial.",
                "Mover el caso a evaluación o archivarlo si no se sostiene.",
            ],
        }

    def _workflow_steps(self, case):
        status = case.status
        if case.google_report_status.value == "resolved":
            current_index = 3
        elif status == CaseStatus.DISMISSED:
            current_index = 2
        elif status == CaseStatus.REPORTED:
            current_index = 3
        elif status == CaseStatus.CONFIRMED:
            current_index = 2
        elif status == CaseStatus.TRIAGED:
            current_index = 1
        else:
            current_index = 0

        base_steps = [
            {
                "label": "1. Revisar evidencia",
                "context": "Confirmar si la prueba visual y la ubicación respaldan la alerta.",
            },
            {
                "label": "2. Confirmar internamente",
                "context": "Definir si el caso es real o si debe archivarse.",
            },
            {
                "label": "3. Preparar reporte",
                "context": "Consolidar la narrativa y el enlace que se enviará a Google.",
            },
            {
                "label": "4. Hacer seguimiento",
                "context": "Esperar respuesta y dejar trazabilidad del resultado.",
            },
        ]

        steps = []
        for index, step in enumerate(base_steps):
            if status == CaseStatus.DISMISSED:
                tone = "done" if index < 2 else "muted"
            elif index < current_index:
                tone = "done"
            elif index == current_index:
                tone = "current"
            else:
                tone = "muted"
            badge = "Ahora" if tone == "current" else "Hecho" if tone == "done" else "Después"
            steps.append({**step, "tone": tone, "badge": badge})
        return steps

    @staticmethod
    def _labelize_value(value: str) -> str:
        mapping = {
            "new": "Nuevo",
            "triaged": "En evaluación",
            "confirmed": "Confirmado",
            "dismissed": "Archivado",
            "reported": "Reportado",
            "not_started": "Sin iniciar con Google",
            "drafted": "Borrador listo para revisión",
            "submitted": "Enviado a Google",
            "acknowledged": "Google recibió el caso",
            "resolved": "Caso cerrado con Google",
        }
        return mapping.get(value, value.replace("_", " ").capitalize())

    @staticmethod
    def _risk_bucket_label(risk_bucket: RiskBucket) -> str:
        if risk_bucket == RiskBucket.HIGH_RISK_WATCHLIST:
            return "Watchlist alto riesgo"
        return "Clon potencial"

    @staticmethod
    def _risk_bucket_context(risk_bucket: RiskBucket) -> str:
        if risk_bucket == RiskBucket.HIGH_RISK_WATCHLIST:
            return "Señal visible y preocupante que exige validación humana antes de abrir un caso duro o escalarlo a Google."
        return "Patrón de clonación con fuerza suficiente para operar como caso formal."

    @staticmethod
    def _risk_bucket_tone(risk_bucket: RiskBucket) -> str:
        if risk_bucket == RiskBucket.HIGH_RISK_WATCHLIST:
            return "watchlist"
        return "clone"

    @staticmethod
    def _google_status_help(value: str) -> str:
        mapping = {
            "not_started": "Todavía no se ha preparado ni enviado gestión alguna a Google para este caso.",
            "drafted": "El expediente ya está armado y listo para revisión humana antes de enviarlo a Google.",
            "submitted": "El caso ya fue enviado a Google y ahora corresponde hacer seguimiento hasta recibir respuesta.",
            "acknowledged": "Google ya recibió el caso. Falta esperar resolución, validar cambios y mantener seguimiento.",
            "resolved": "El caso ya tuvo cierre frente a Google. Ahora conviene conservar trazabilidad y vigilar que no reaparezca.",
        }
        return mapping.get(value, "Este estado resume el avance actual del caso dentro del flujo con Google.")

    @staticmethod
    def _google_flow_tone(value: str) -> str:
        if value == "not_started":
            return "danger"
        if value == "drafted":
            return "info"
        if value in {"submitted", "acknowledged", "resolved"}:
            return "success"
        return "neutral"

    @staticmethod
    def _job_type_label(value: str) -> str:
        mapping = {
            "public_scan": "Barrido público",
            "gbp_event": "Evento de perfil oficial",
            "gbp_customer_media_backfill": "Sincronización de fotos públicas",
            "gbp_customer_media_reconcile": "Reconciliación de fotos públicas",
            "ocr_analysis": "Análisis de texto en imagen",
            "report_generation": "Preparación de reporte",
        }
        return mapping.get(value, value.replace("_", " ").capitalize())

    @staticmethod
    def _job_status_label(value: JobStatus | str) -> str:
        raw = value.value if hasattr(value, "value") else str(value)
        mapping = {
            "queued": "En fila",
            "running": "En curso",
            "completed": "Completado",
            "failed": "Con error",
            "degraded": "Con degradación",
        }
        return mapping.get(raw, raw.replace("_", " ").capitalize())

    @staticmethod
    def _position_dealers(dealers):
        valid = [dealer for dealer in dealers if dealer.latitude is not None and dealer.longitude is not None]
        if not valid:
            return [
                {
                    "id": dealer.id,
                    "name": dealer.name,
                    "city": DashboardService._display_city(dealer.city),
                    "address": dealer.address,
                    "left": 50,
                    "top": 50,
                }
                for dealer in dealers
            ]

        latitudes = [dealer.latitude for dealer in valid]
        longitudes = [dealer.longitude for dealer in valid]
        lat_min, lat_max = min(latitudes), max(latitudes)
        lon_min, lon_max = min(longitudes), max(longitudes)

        def normalize(value, lower, upper, fallback):
            if upper == lower:
                return fallback
            return round(((value - lower) / (upper - lower)) * 64 + 18, 1)

        positioned = []
        for dealer in dealers:
            if dealer.latitude is None or dealer.longitude is None:
                left = 50
                top = 50
            else:
                left = normalize(dealer.longitude, lon_min, lon_max, 50)
                top = 90 - normalize(dealer.latitude, lat_min, lat_max, 50)
            positioned.append(
                {
                    "id": dealer.id,
                    "name": dealer.name,
                    "city": DashboardService._display_city(dealer.city),
                    "address": dealer.address,
                    "left": left,
                    "top": top,
                }
            )
        return positioned
