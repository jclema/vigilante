from app.agents.forensic import ForensicAgent
from app.agents.scout import ScoutAgent
from app.models import SourceType
from app.services.multi_source_ingest import EvidenceIngestionRequest, MultiSourceEvidenceIngestService
from app.store import InMemoryRepository


class FakeEvidenceService:
    def capture_image(self, *, case_id: str, artifact_id: str, source_url: str | None):
        return type(
            "Captured",
            (),
            {
                "internal_url": "/api/evidence/image?path=file%3A%2F%2F%2Ftmp%2Fcollector.jpg",
                "storage_path": "file:///tmp/collector.jpg",
                "checksum": "collector-hash",
                "content_type": "image/jpeg",
                "size_bytes": 12,
                "download_status": "captured",
                "bytes_payload": b"fake-image",
            },
        )()


class FakeTextExtractor:
    def extract_text(self, *, image_bytes, content_type, raw_payload, fallback_text):
        return fallback_text or "Yamaha Bello 301 999 8888"


def test_multi_source_ingest_service_accepts_future_source():
    repo = InMemoryRepository()
    repo.seed()
    service = MultiSourceEvidenceIngestService(
        repository=repo,
        scout_agent=ScoutAgent(repo, ForensicAgent()),
        evidence_service=FakeEvidenceService(),
        text_extractor=FakeTextExtractor(),
    )

    case = service.ingest_request(
        EvidenceIngestionRequest(
            profile_id="profile-bello",
            source_type=SourceType.REVIEW_PHOTO,
            source_url="https://collector.example/fake.jpg",
            image_url="https://collector.example/fake.jpg",
            source_page_url="https://collector.example/source",
            ingestion_mode="collector_future_source",
            media_origin="future_source_x",
            review_text="Nuevo numero 301 999 8888",
            raw_payload={"collector_name": "future-source-x"},
        )
    )

    assert case is not None
    evidence = repo.list_evidence_for_case(case.id)
    assert len(evidence) == 1
    assert evidence[0].content["media_origin"] == "future_source_x"
    assert evidence[0].content["detected_phone_numbers"] == ["3019998888"]
    assert evidence[0].content["ingestion_mode"] == "collector_future_source"
