from __future__ import annotations

import hashlib
import mimetypes
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

try:
    from google.cloud import storage
except ImportError:  # pragma: no cover - optional in local test env
    storage = None

from app.config import settings


@dataclass(slots=True)
class CapturedEvidenceImage:
    internal_url: str | None
    storage_path: str | None
    checksum: str | None
    content_type: str | None
    size_bytes: int
    download_status: str
    bytes_payload: bytes | None = None


class EvidenceMediaService:
    def __init__(self) -> None:
        self.bucket_name = settings.evidence_bucket_name
        self.local_dir = Path(settings.evidence_local_dir)
        self._storage_client = None

    def capture_image(
        self,
        *,
        case_id: str,
        artifact_id: str,
        source_url: str | None,
    ) -> CapturedEvidenceImage:
        if not source_url:
            return CapturedEvidenceImage(
                internal_url=None,
                storage_path=None,
                checksum=None,
                content_type=None,
                size_bytes=0,
                download_status="missing_source_url",
            )

        try:
            image_bytes, content_type = self._download_bytes(source_url)
        except (HTTPError, URLError, ValueError):
            return CapturedEvidenceImage(
                internal_url=None,
                storage_path=None,
                checksum=None,
                content_type=None,
                size_bytes=0,
                download_status="download_failed",
            )

        checksum = hashlib.sha256(image_bytes).hexdigest()
        extension = self._extension_for(content_type, source_url)
        storage_key = f"cases/{case_id}/{artifact_id}-{checksum[:12]}{extension}"
        storage_path = self._store_bytes(storage_key, image_bytes, content_type)

        return CapturedEvidenceImage(
            internal_url=f"/api/evidence/image?path={quote(storage_path, safe='')}",
            storage_path=storage_path,
            checksum=checksum,
            content_type=content_type,
            size_bytes=len(image_bytes),
            download_status="captured",
            bytes_payload=image_bytes,
        )

    def load_image(self, storage_path: str) -> tuple[bytes, str]:
        if storage_path.startswith("gs://"):
            if storage is None:  # pragma: no cover - depends on optional cloud deps
                raise FileNotFoundError(storage_path)
            bucket_name, blob_name = self._split_gs_path(storage_path)
            bucket = self._storage_client_or_raise().bucket(bucket_name)
            blob = bucket.blob(blob_name)
            data = blob.download_as_bytes()
            return data, blob.content_type or "image/jpeg"

        if storage_path.startswith("file://"):
            file_path = Path(storage_path.replace("file://", "", 1))
            data = file_path.read_bytes()
            return data, mimetypes.guess_type(file_path.name)[0] or "image/jpeg"

        raise FileNotFoundError(storage_path)

    def _download_bytes(self, source_url: str) -> tuple[bytes, str]:
        if source_url.startswith("file://"):
            file_path = Path(source_url.replace("file://", "", 1))
            payload = file_path.read_bytes()
            content_type = mimetypes.guess_type(file_path.name)[0] or "image/png"
            if not payload:
                raise ValueError("Imagen vacia")
            return payload, content_type
        request = Request(
            source_url,
            headers={
                "User-Agent": "VigilanteEvidenceBot/1.0",
                "Accept": "image/*,*/*;q=0.8",
            },
        )
        with urlopen(request, timeout=20) as response:  # noqa: S310 - controlled URL ingestion
            payload = response.read()
            content_type = response.headers.get_content_type() or "image/jpeg"
        if not payload:
            raise ValueError("Imagen vacia")
        return payload, content_type

    def _store_bytes(self, storage_key: str, payload: bytes, content_type: str) -> str:
        if self.bucket_name:
            if storage is None:  # pragma: no cover - depends on optional cloud deps
                raise RuntimeError("google-cloud-storage no esta disponible")
            bucket = self._storage_client_or_raise().bucket(self.bucket_name)
            blob = bucket.blob(storage_key)
            blob.upload_from_string(payload, content_type=content_type)
            return f"gs://{self.bucket_name}/{storage_key}"

        file_path = self.local_dir / storage_key
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_bytes(payload)
        return f"file://{file_path}"

    def _storage_client_or_raise(self):
        if self._storage_client is None:
            self._storage_client = storage.Client(project=settings.google_cloud_project)
        return self._storage_client

    @staticmethod
    def _split_gs_path(path: str) -> tuple[str, str]:
        without_scheme = path.replace("gs://", "", 1)
        bucket_name, _, blob_name = without_scheme.partition("/")
        return bucket_name, blob_name

    @staticmethod
    def _extension_for(content_type: str | None, source_url: str) -> str:
        if content_type:
            guessed = mimetypes.guess_extension(content_type.split(";")[0].strip())
            if guessed:
                return guessed
        parsed = urlparse(source_url)
        suffix = Path(parsed.path).suffix
        return suffix if suffix else ".jpg"
