from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from time import sleep
from urllib.parse import urlencode
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from app.config import settings
from app.models import ConnectionStatus, DealerProfile, GbpConnection, JobRun, JobStatus, MonitoringMode, SourceType
from app.services.auth import decrypt_secret
from app.services.multi_source_ingest import EvidenceIngestionRequest, MultiSourceEvidenceIngestService
from app.store import Repository


@dataclass(slots=True)
class CustomerMediaItem:
    name: str
    location_name: str
    image_url: str | None
    thumbnail_url: str | None
    source_page_url: str | None
    description: str | None
    create_time: str | None
    raw_payload: dict[str, object]


@dataclass(slots=True)
class GbpResolvedCredentials:
    access_token: str
    account_names: list[str]
    connection: GbpConnection | None = None


class GbpCustomerMediaClient:
    def __init__(
        self,
        access_token: str | None = None,
        account_id: str | None = None,
        account_names: list[str] | None = None,
    ) -> None:
        self.access_token = access_token or settings.google_gbp_access_token
        configured_account = account_id or settings.google_gbp_account_id
        normalized_configured = self._normalize_account_name(configured_account) if configured_account else None
        self.account_names = account_names or ([normalized_configured] if normalized_configured else [])

    def list_customer_media(self, location_name: str, page_size: int = 20) -> list[CustomerMediaItem]:
        last_error: Exception | None = None
        for normalized in self.normalize_location_names(location_name):
            query = urlencode({"pageSize": str(page_size)})
            url = f"https://mybusiness.googleapis.com/v4/{normalized}/media/customers?{query}"
            try:
                payload = self._get_json(url)
            except Exception as exc:
                last_error = exc
                continue
            raw_items = (
                payload.get("mediaItems")
                or payload.get("customerMedia")
                or payload.get("media")
                or payload.get("items")
                or []
            )
            results: list[CustomerMediaItem] = []
            for raw in raw_items:
                image_url = (
                    raw.get("sourceUrl")
                    or raw.get("googleUrl")
                    or raw.get("url")
                    or raw.get("thumbnailUrl")
                )
                results.append(
                    CustomerMediaItem(
                        name=str(raw.get("name") or ""),
                        location_name=normalized,
                        image_url=image_url,
                        thumbnail_url=raw.get("thumbnailUrl"),
                        source_page_url=raw.get("googleUrl") or raw.get("sourceUrl"),
                        description=raw.get("description"),
                        create_time=raw.get("createTime") or raw.get("updateTime"),
                        raw_payload=raw,
                    )
                )
            return results
        if last_error:
            raise last_error
        raise ValueError("No fue posible resolver la ruta de customer media para el perfil GBP.")

    def normalize_location_names(self, value: str) -> list[str]:
        if value.startswith("accounts/"):
            return [value]
        if value.startswith("locations/"):
            if not self.account_names:
                raise ValueError("Falta una cuenta GBP conectada para completar la ruta del location.")
            return [f"{account_name}/{value}" for account_name in self.account_names]
        raise ValueError(f"Ruta GBP invalida: {value}")

    @staticmethod
    def location_suffix(value: str) -> str:
        if "/locations/" in value and value.startswith("accounts/"):
            return value.split("/", 2)[-1]
        return value

    @staticmethod
    def _normalize_account_name(value: str) -> str:
        return value if value.startswith("accounts/") else f"accounts/{value}"

    def _get_json(self, url: str) -> dict[str, object]:
        if not self.access_token:
            raise ValueError("Falta GOOGLE_GBP_ACCESS_TOKEN para leer customer media.")
        request = Request(
            url,
            headers={
                "Authorization": f"Bearer {self.access_token}",
                "Accept": "application/json",
            },
        )
        with urlopen(request, timeout=20) as response:  # noqa: S310 - fixed Google API endpoint
            return json.loads(response.read().decode("utf-8"))


class GbpOrganizationConnectionResolver:
    def __init__(self, repository: Repository) -> None:
        self.repository = repository

    def credentials_for_profile(self, profile: DealerProfile) -> GbpResolvedCredentials:
        candidate_connections = self._candidate_connections(profile)
        last_error: Exception | None = None
        for connection in candidate_connections:
            refresh_token = decrypt_secret(connection.encrypted_refresh_token)
            if not refresh_token:
                continue
            try:
                access_token = self._refresh_access_token(refresh_token)
                account_names = [connection.gbp_account_name] if connection.gbp_account_name else self._list_account_names(access_token)
            except Exception as exc:
                connection.status = ConnectionStatus.ERROR
                connection.last_error = str(exc)
                connection.last_error_at = datetime.now(UTC)
                connection.updated_at = datetime.now(UTC)
                self.repository.save_gbp_connection(connection)
                last_error = exc
                continue
            connection.status = ConnectionStatus.CONNECTED
            connection.last_error = None
            connection.last_error_at = None
            connection.last_sync_at = datetime.now(UTC)
            connection.updated_at = datetime.now(UTC)
            if account_names:
                connection.gbp_account_name = account_names[0]
            self.repository.save_gbp_connection(connection)
            return GbpResolvedCredentials(
                access_token=access_token,
                account_names=account_names or ([connection.gbp_account_name] if connection.gbp_account_name else []),
                connection=connection,
            )
        if settings.google_gbp_access_token:
            configured_account = settings.google_gbp_account_id or None
            return GbpResolvedCredentials(
                access_token=settings.google_gbp_access_token,
                account_names=[GbpCustomerMediaClient._normalize_account_name(configured_account)] if configured_account else [],
                connection=None,
            )
        if last_error:
            raise last_error
        raise ValueError("No hay una conexión GBP activa para este perfil.")

    def discover_locations(self, *, organization_id: str, connection_id: str) -> list[dict[str, str]]:
        connection = self.repository.get_gbp_connection(connection_id)
        if not connection or connection.organization_id != organization_id:
            raise ValueError("Conexión GBP no encontrada")
        refresh_token = decrypt_secret(connection.encrypted_refresh_token)
        if not refresh_token:
            raise ValueError("La conexión GBP no tiene un refresh token activo")
        access_token = self._refresh_access_token(refresh_token)
        account_names = [connection.gbp_account_name] if connection.gbp_account_name else self._list_account_names(access_token)
        if account_names and not connection.gbp_account_name:
            connection.gbp_account_name = account_names[0]
        locations: list[dict[str, str]] = []
        for account_name in account_names:
            locations.extend(self._list_locations_for_account(access_token, account_name))
        deduped = self._dedupe_locations(locations)
        connection.available_locations = deduped
        connection.status = ConnectionStatus.CONNECTED
        connection.last_locations_sync_at = datetime.now(UTC)
        connection.last_sync_at = datetime.now(UTC)
        connection.last_error = None
        connection.last_error_at = None
        connection.updated_at = datetime.now(UTC)
        self.repository.save_gbp_connection(connection)
        return deduped

    def _candidate_connections(self, profile: DealerProfile) -> list[GbpConnection]:
        if not profile.organization_id:
            return []
        connections = [
            item
            for item in self.repository.list_gbp_connections(profile.organization_id)
            if item.status == ConnectionStatus.CONNECTED and item.encrypted_refresh_token
        ]
        targeted = [item for item in connections if profile.id in item.selected_profile_ids]
        if targeted:
            return targeted
        selected_any = any(item.selected_profile_ids for item in connections)
        if not selected_any:
            return connections
        return []

    def _refresh_access_token(self, refresh_token: str) -> str:
        if not settings.google_oauth_client_id or not settings.google_oauth_client_secret:
            raise ValueError("Faltan credenciales OAuth para refrescar la conexión GBP.")
        payload = urlencode(
            {
                "client_id": settings.google_oauth_client_id,
                "client_secret": settings.google_oauth_client_secret,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            }
        ).encode("utf-8")
        request = Request(
            "https://oauth2.googleapis.com/token",
            data=payload,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        with urlopen(request, timeout=20) as response:  # noqa: S310 - fixed Google OAuth endpoint
            token_data = json.loads(response.read().decode("utf-8"))
        access_token = token_data.get("access_token")
        if not isinstance(access_token, str) or not access_token:
            raise ValueError("Google no devolvió un access token válido para la conexión GBP.")
        return access_token

    def _list_account_names(self, access_token: str) -> list[str]:
        try:
            payload = self._authorized_json_request(
                "https://mybusinessaccountmanagement.googleapis.com/v1/accounts",
                access_token=access_token,
            )
        except HTTPError as exc:
            if exc.code == 429:
                return ["accounts/me"]
            raise
        accounts = payload.get("accounts") or []
        names = [
            str(account.get("name"))
            for account in accounts
            if isinstance(account, dict) and isinstance(account.get("name"), str) and str(account.get("name")).startswith("accounts/")
        ]
        if not names:
            return ["accounts/me"]
        if "accounts/me" not in names:
            names.insert(0, "accounts/me")
        if not names:
            raise ValueError("La cuenta conectada no expone cuentas GBP accesibles para Vigilante.")
        return names

    def _list_locations_for_account(self, access_token: str, account_name: str) -> list[dict[str, str]]:
        page_token = ""
        locations: list[dict[str, str]] = []
        while True:
            query = {
                "pageSize": "100",
                "readMask": "name,title,storeCode,metadata.placeId",
            }
            if page_token:
                query["pageToken"] = page_token
            payload = self._authorized_json_request(
                f"https://mybusinessbusinessinformation.googleapis.com/v1/{account_name}/locations?{urlencode(query)}",
                access_token=access_token,
            )
            for raw in payload.get("locations") or []:
                if not isinstance(raw, dict):
                    continue
                metadata = raw.get("metadata") if isinstance(raw.get("metadata"), dict) else {}
                location_name = raw.get("name")
                title = raw.get("title")
                if not isinstance(location_name, str) or not isinstance(title, str):
                    continue
                locations.append(
                    {
                        "name": location_name,
                        "title": title,
                        "account_name": account_name,
                        "place_id": str(metadata.get("placeId") or ""),
                        "store_code": str(raw.get("storeCode") or ""),
                    }
                )
            page_token = str(payload.get("nextPageToken") or "")
            if not page_token:
                break
        return locations

    def _authorized_json_request(self, url: str, *, access_token: str, retries: int = 3) -> dict[str, object]:
        last_error: Exception | None = None
        for attempt in range(retries):
            request = Request(
                url,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/json",
                },
            )
            try:
                with urlopen(request, timeout=20) as response:  # noqa: S310 - fixed Google API endpoint
                    return json.loads(response.read().decode("utf-8"))
            except HTTPError as exc:
                last_error = exc
                if exc.code in {429, 500, 502, 503, 504} and attempt < retries - 1:
                    sleep(1.5 * (attempt + 1))
                    continue
                raise
        if last_error:
            raise last_error
        raise ValueError("No fue posible completar la llamada a Google Business Profile.")

    @staticmethod
    def _dedupe_locations(locations: list[dict[str, str]]) -> list[dict[str, str]]:
        seen: set[str] = set()
        deduped: list[dict[str, str]] = []
        for location in locations:
            key = location.get("name") or f"{location.get('title')}:{location.get('place_id')}"
            if not key or key in seen:
                continue
            seen.add(key)
            deduped.append(location)
        return deduped


class ImageTextExtractor:
    def extract_text(
        self,
        *,
        image_bytes: bytes | None,
        content_type: str | None,
        raw_payload: dict[str, object] | None,
        fallback_text: str | None,
    ) -> str | None:
        if raw_payload:
            for key in ("ocr_text", "detectedText", "fullText"):
                value = raw_payload.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()
        if fallback_text:
            return fallback_text
        if not image_bytes or not settings.enable_google_vision_ocr:
            return None
        try:
            from google.cloud import vision
        except ImportError:  # pragma: no cover - optional cloud deps in local env
            return None
        client = vision.ImageAnnotatorClient()
        image = vision.Image(content=image_bytes)

        detectors = [
            client.text_detection,
            client.document_text_detection,
        ]
        for detector in detectors:
            result = detector(image=image)
            if result.error.message:
                continue
            annotations = result.text_annotations or []
            if annotations and annotations[0].description.strip():
                return annotations[0].description.strip()
            full_text = getattr(result, "full_text_annotation", None)
            if full_text and getattr(full_text, "text", "").strip():
                return full_text.text.strip()
        return None


class GbpCustomerMediaIngestService:
    def __init__(
        self,
        repository: Repository,
        scout_agent,
        media_client: GbpCustomerMediaClient | None,
        evidence_service,
        text_extractor: ImageTextExtractor | None = None,
        credentials_resolver: GbpOrganizationConnectionResolver | None = None,
    ) -> None:
        self.repository = repository
        self.scout_agent = scout_agent
        self.media_client = media_client
        self.credentials_resolver = credentials_resolver or GbpOrganizationConnectionResolver(repository)
        self.text_extractor = text_extractor or ImageTextExtractor()
        self.ingest_service = MultiSourceEvidenceIngestService(
            repository=repository,
            scout_agent=scout_agent,
            evidence_service=evidence_service,
            text_extractor=self.text_extractor,
        )

    def sync_profiles(self, profile_ids: list[str] | None = None, limit: int = 20) -> dict[str, object]:
        profiles = [
            profile
            for profile in self.repository.profiles.values()
            if profile.enabled and profile.monitoring_mode == MonitoringMode.GBP_PUSH and profile.gbp_location_id
        ]
        if profile_ids:
            wanted = set(profile_ids)
            profiles = [profile for profile in profiles if profile.id in wanted]

        totals = {"profiles": 0, "processed": 0, "cases_created": 0, "cases_updated": 0, "download_failures": 0}
        runs = []
        for profile in profiles:
            run = self.sync_profile(profile.id, limit=limit, ingestion_mode="backfill")
            totals["profiles"] += 1
            totals["processed"] += run["processed"]
            totals["cases_created"] += run["cases_created"]
            totals["cases_updated"] += run["cases_updated"]
            totals["download_failures"] += run["download_failures"]
            runs.append(run)
        return {"totals": totals, "profiles": runs}

    def sync_profile(self, profile_id: str, limit: int = 20, ingestion_mode: str = "backfill") -> dict[str, object]:
        profile = self.repository.profiles.get(profile_id)
        if not profile or not profile.enabled or not profile.gbp_location_id:
            raise ValueError(f"Perfil GBP no disponible para sync: {profile_id}")

        job = JobRun(
            id=self.repository.next_id("job"),
            job_type="gbp_customer_media_reconcile" if ingestion_mode == "push" else "gbp_customer_media_backfill",
            job_status=JobStatus.RUNNING,
            organization_id=profile.organization_id,
            detail=f"Sincronizando customer media para {profile.name}.",
        )
        self.repository.save_job(job)
        media_client = self._client_for_profile(profile)
        items = media_client.list_customer_media(profile.gbp_location_id, page_size=limit)
        processed = 0
        created = 0
        updated = 0
        download_failures = 0

        for item in items:
            request = self._build_request(profile.id, item, ingestion_mode=ingestion_mode)
            previous_case_ids = {case.id for case in self.repository.list_cases()}
            case = self.ingest_service.ingest_request(request)
            processed += 1
            if case:
                latest_evidence = self.repository.list_evidence_for_case(case.id)[-1]
                if (latest_evidence.content or {}).get("download_status") == "download_failed":
                    download_failures += 1
            if case:
                if case.id not in previous_case_ids:
                    created += 1
                else:
                    updated += 1

        job.job_status = JobStatus.DEGRADED if download_failures else JobStatus.COMPLETED
        job.finished_at = datetime.now(UTC)
        job.detail = (
            f"Customer media procesado para {profile.name}. {processed} fotos revisadas, "
            f"{created} caso(s) nuevos, {updated} caso(s) enriquecidos."
        )
        self.repository.save_job(job)
        return {
            "profile_id": profile.id,
            "profile_name": profile.name,
            "processed": processed,
            "cases_created": created,
            "cases_updated": updated,
            "download_failures": download_failures,
        }

    def sync_push_payload(self, payload: dict[str, object], limit: int = 20) -> dict[str, object]:
        if "message" in payload and isinstance(payload["message"], dict):
            data = payload["message"].get("data")
            if isinstance(data, str) and data:
                decoded = json.loads(base64.b64decode(data).decode("utf-8"))
                payload = decoded

        profile_id = payload.get("profile_id")
        location_name = payload.get("gbp_location_id") or payload.get("location_name")
        if profile_id:
            return self.sync_profile(str(profile_id), limit=limit, ingestion_mode="push")
        if location_name:
            normalized = GbpCustomerMediaClient.location_suffix(str(location_name))
            profile = next(
                (
                    item
                    for item in self.repository.profiles.values()
                    if item.enabled
                    and item.gbp_location_id
                    and GbpCustomerMediaClient.location_suffix(item.gbp_location_id) == normalized
                ),
                None,
            )
            if profile:
                return self.sync_profile(profile.id, limit=limit, ingestion_mode="push")
        raise ValueError("No se pudo resolver el perfil GBP a partir del payload recibido.")

    def _client_for_profile(self, profile: DealerProfile) -> GbpCustomerMediaClient:
        if self.media_client is not None:
            return self.media_client
        credentials = self.credentials_resolver.credentials_for_profile(profile)
        return GbpCustomerMediaClient(
            access_token=credentials.access_token,
            account_names=credentials.account_names,
        )

    def _build_request(self, profile_id: str, item: CustomerMediaItem, ingestion_mode: str) -> EvidenceIngestionRequest:
        observed_at = None
        if item.create_time:
            try:
                observed_at = datetime.fromisoformat(item.create_time.replace("Z", "+00:00"))
            except ValueError:
                observed_at = None
        return EvidenceIngestionRequest(
            profile_id=profile_id,
            source_type=SourceType.REVIEW_PHOTO,
            image_url=item.image_url or item.thumbnail_url,
            external_media_id=item.name or None,
            gbp_location_id=item.location_name,
            source_page_url=item.source_page_url,
            google_maps_uri=item.source_page_url,
            thumbnail_url=item.thumbnail_url,
            source_url=item.image_url,
            review_text=item.description,
            ingestion_mode=ingestion_mode,
            media_origin="gbp_customer_media",
            observed_at=observed_at or datetime.now(UTC),
            raw_payload=item.raw_payload,
        )
