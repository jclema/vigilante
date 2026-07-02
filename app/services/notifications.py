from __future__ import annotations

import smtplib
from email.message import EmailMessage

from app.config import settings
from app.models import AlertEvent, DeliveryStatus, NotificationChannel, NotificationEventType, ThreatCase
from app.store import Repository


class NotificationService:
    def __init__(self, repository: Repository) -> None:
        self.repository = repository

    def notify_case_event(self, case: ThreatCase, event_type: NotificationEventType) -> list[AlertEvent]:
        destinations = [
            item
            for item in self.repository.list_notification_destinations(case.organization_id)
            if item.enabled and event_type in item.subscribed_events
        ]
        if not destinations:
            destinations = [
                item
                for item in self.repository.list_notification_destinations()
                if item.enabled and event_type in item.subscribed_events and item.organization_id == "org-yamaha-network"
            ]

        created: list[AlertEvent] = []
        for destination in destinations:
            message = self._build_message(case, event_type)
            delivery_status = self._deliver(destination.channel.value, destination.target, message)
            event = AlertEvent(
                id=self.repository.next_id("alert"),
                case_id=case.id,
                organization_id=case.organization_id,
                channel=destination.channel.value,
                message=message,
                delivery_status=delivery_status,
                destination=destination.target,
            )
            self.repository.save_alert(event)
            created.append(event)
        return created

    def _deliver(self, channel: str, target: str, message: str) -> DeliveryStatus:
        if channel == NotificationChannel.EMAIL.value:
            return self._send_email(target, message)
        return DeliveryStatus.SIMULATED

    def _send_email(self, target: str, message: str) -> DeliveryStatus:
        if not settings.smtp_host or not settings.smtp_from_email:
            return DeliveryStatus.SIMULATED
        email = EmailMessage()
        email["Subject"] = "Vigilante: alerta de caso"
        email["From"] = settings.smtp_from_email
        email["To"] = target
        email.set_content(message)
        try:
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as client:
                if settings.smtp_starttls:
                    client.starttls()
                if settings.smtp_username and settings.smtp_password:
                    client.login(settings.smtp_username, settings.smtp_password)
                client.send_message(email)
        except Exception:
            return DeliveryStatus.FAILED
        return DeliveryStatus.SENT

    @staticmethod
    def _build_message(case: ThreatCase, event_type: NotificationEventType) -> str:
        return (
            f"[{event_type.value}] {case.title}\n"
            f"Sede: {case.dealer_name}\n"
            f"Riesgo: {case.risk_score}/100\n"
            f"Estado: {case.status.value}\n"
            f"Google: {case.google_report_status.value}\n"
            f"Resumen: {case.summary}"
        )
