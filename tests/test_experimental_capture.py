from pathlib import Path

from app.agents.forensic import ForensicAgent
from app.agents.scout import ScoutAgent
from app.services.experimental_capture import ExperimentalCaptureIngestService, ExperimentalCaptureRecord
from app.store import InMemoryRepository


class FakeEvidenceService:
    def capture_image(self, *, case_id: str, artifact_id: str, source_url: str | None):
        return type(
            "Captured",
            (),
            {
                "internal_url": "/api/evidence/image?path=file%3A%2F%2F%2Ftmp%2Fcapture.png",
                "storage_path": "file:///tmp/capture.png",
                "checksum": "hash-1",
                "content_type": "image/png",
                "size_bytes": 12,
                "download_status": "captured",
                "bytes_payload": b"fake-png",
            },
        )()


class FakeTextExtractor:
    def extract_text(self, *, image_bytes, content_type, raw_payload, fallback_text):
        return "Yamaha Bello 301 999 8888"


def test_experimental_capture_ingest_creates_review_photo_case(tmp_path: Path):
    screenshot = tmp_path / "capture.png"
    screenshot.write_bytes(b"not-real-but-enough")

    repo = InMemoryRepository()
    repo.seed()
    service = ExperimentalCaptureIngestService(
        repository=repo,
        scout_agent=ScoutAgent(repo, ForensicAgent()),
        evidence_service=FakeEvidenceService(),
        text_extractor=FakeTextExtractor(),
    )

    case = service.ingest_capture(
        ExperimentalCaptureRecord(
            profile_id="profile-bello",
            profile_name="Motoblu Bello",
            screenshot_path=str(screenshot),
            profile_url="https://maps.google.com/?cid=123",
            final_url="https://www.google.com/maps/place/Motoblu+Bello/photos",
            gallery_opened=True,
            gallery_open_method="see-photos-overlay",
            all_media_selected=True,
            media_filter="all-filter",
            gallery_hint="photos-and-videos",
            browser_surface="desktop",
            step_trace=[{"step": "profile_loaded", "status": "ok", "detail": "Perfil cargado."}],
            fallback_used=False,
            asset_fingerprint="fingerprint-1",
            navigation_confidence="high",
        )
    )

    assert case is not None
    evidence = repo.list_evidence_for_case(case.id)
    assert len(evidence) == 1
    assert evidence[0].content["ingestion_mode"] == "experimental_browser_capture"
    assert evidence[0].content["internal_image_url"].startswith("/api/evidence/image?")
    assert evidence[0].content["raw_payload"]["gallery_opened"] is True
    assert evidence[0].content["raw_payload"]["all_media_selected"] is True
    assert evidence[0].content["raw_payload"]["browser_surface"] == "desktop"
    assert evidence[0].content["raw_payload"]["asset_fingerprint"] == "fingerprint-1"
    assert evidence[0].content["raw_payload"]["navigation_confidence"] == "high"
