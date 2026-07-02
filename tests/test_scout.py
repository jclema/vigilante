from datetime import UTC, datetime, timedelta

from app.agents.forensic import ForensicAgent
from app.agents.scout import ScoutAgent
from app.models import CaseStatus, ObservedPlace, RiskBucket, SourceType
from app.store import InMemoryRepository


def test_public_scan_consolidates_same_place_across_queries_into_single_case():
    repo = InMemoryRepository()
    repo.seed()
    scout = ScoutAgent(repo, ForensicAgent())

    observed = [
        ObservedPlace(
            id="obs-1",
            place_id="clone-bello-123",
            name="Yamaha Principal Bello",
            address="Diagonal 50 45-12, Bello",
            phone_number="3019998888",
            category="motorcycle_dealer",
            latitude=6.3371,
            longitude=-75.5549,
            source_query="yamaha bello",
            query_rank=2,
            user_rating_count=2,
            rating=3.2,
            first_seen_at=datetime.now(UTC) - timedelta(days=1),
        ),
        ObservedPlace(
            id="obs-2",
            place_id="clone-bello-123",
            name="Yamaha Principal Bello",
            address="Diagonal 50 45-12, Bello",
            phone_number="3019998888",
            category="motorcycle_dealer",
            latitude=6.3371,
            longitude=-75.5549,
            source_query="yamaha principal bello",
            query_rank=1,
            user_rating_count=2,
            rating=3.2,
            first_seen_at=datetime.now(UTC) - timedelta(days=1),
        ),
    ]

    scan = scout.run_public_scan("yamaha bello", observed)

    assert scan.threats_found == 1
    cases = repo.list_cases()
    assert len(cases) == 1
    assert cases[0].source_type == SourceType.PLACE_CLONE
    evidence = repo.list_evidence_for_case(cases[0].id)
    assert len(evidence) == 1
    assert evidence[0].content["query_hits"] == ["yamaha bello", "yamaha principal bello"]


def test_public_scan_keeps_legit_non_official_workshop_out_of_cases():
    repo = InMemoryRepository()
    repo.seed()
    scout = ScoutAgent(repo, ForensicAgent())

    observed = [
        ObservedPlace(
            id="obs-legit-1",
            place_id="taller-bello-1",
            name="Taller Yamaha Bello",
            address="Carrera 54 51-33, Bello",
            phone_number="6045552233",
            category="motorcycle_repair_shop",
            latitude=6.3338,
            longitude=-75.5571,
            source_query="yamaha bello",
            query_rank=6,
            user_rating_count=47,
            rating=4.6,
            first_seen_at=datetime.now(UTC) - timedelta(days=420),
        )
    ]

    scan = scout.run_public_scan("yamaha bello", observed)

    assert scan.threats_found == 0
    assert scan.notes is not None
    assert "no oficiales" in scan.notes
    assert repo.list_cases() == []


def test_public_scan_creates_watchlist_case_for_high_risk_ambiguous_point():
    repo = InMemoryRepository()
    repo.seed()
    scout = ScoutAgent(repo, ForensicAgent())
    dealer = repo.dealers["dealer-itagui"]
    dealer.name = "Moto Medina"
    dealer.city = "Copacabana"
    dealer.address = "Cl. 52 #11-40, Copacabana"
    dealer.latitude = 6.3480
    dealer.longitude = -75.5101

    observed = [
        ObservedPlace(
            id="obs-watchlist-1",
            place_id="watchlist-copacabana-1",
            name="YAMAHA MOTOS COPACABANA",
            address="Cl. 52 #11 # 50a, Copacabana, Antioquia, Colombia",
            phone_number="6049992233",
            category="motorcycle_dealer",
            latitude=6.3481,
            longitude=-75.5100,
            source_query="yamaha oficial copacabana",
            query_rank=1,
            user_rating_count=23,
            rating=4.2,
        )
    ]

    scan = scout.run_public_scan("yamaha oficial copacabana", observed)

    assert scan.threats_found == 1
    cases = repo.list_cases()
    assert len(cases) == 1
    assert cases[0].risk_bucket == RiskBucket.HIGH_RISK_WATCHLIST
    assert "Watchlist" in cases[0].title


def test_public_scan_reclassifies_existing_new_case_into_watchlist_bucket():
    repo = InMemoryRepository()
    repo.seed()
    scout = ScoutAgent(repo, ForensicAgent())
    dealer = repo.dealers["dealer-itagui"]
    dealer.name = "Moto Medina"
    dealer.city = "Copacabana"
    dealer.address = "Cl. 52 #11-40, Copacabana"
    dealer.latitude = 6.3480
    dealer.longitude = -75.5101

    initial = scout.run_public_scan(
        "yamaha oficial copacabana",
        [
            ObservedPlace(
                id="obs-watchlist-initial",
                place_id="watchlist-copacabana-existing",
                name="YAMAHA MOTOS COPACABANA",
                address="Cl. 52 #11 # 50a, Copacabana, Antioquia, Colombia",
                phone_number="6049992233",
                category="motorcycle_dealer",
                latitude=6.3481,
                longitude=-75.5100,
                source_query="yamaha oficial copacabana",
                query_rank=1,
                user_rating_count=23,
                rating=4.2,
            )
        ],
    )

    assert initial.threats_found == 1
    case = repo.list_cases()[0]
    case.risk_bucket = RiskBucket.CLONE_RISK
    case.title = f"Posible clon de {dealer.name}"
    case.status = CaseStatus.NEW
    repo.save_case(case)

    rescan = scout.run_public_scan(
        "yamaha principal copacabana",
        [
            ObservedPlace(
                id="obs-watchlist-rescan",
                place_id="watchlist-copacabana-existing",
                name="YAMAHA MOTOS COPACABANA",
                address="Cl. 52 #11 # 50a, Copacabana, Antioquia, Colombia",
                phone_number="6049992233",
                category="motorcycle_dealer",
                latitude=6.3481,
                longitude=-75.5100,
                source_query="yamaha principal copacabana",
                query_rank=1,
                user_rating_count=23,
                rating=4.2,
            )
        ],
    )

    assert rescan.threats_found == 1
    updated = repo.get_case(case.id)
    assert updated is not None
    assert updated.risk_bucket == RiskBucket.HIGH_RISK_WATCHLIST
    assert updated.title == f"Watchlist de alto riesgo de {dealer.name}"
