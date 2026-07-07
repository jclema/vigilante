from datetime import UTC, datetime, timedelta

from app.agents.forensic import (
    ForensicAgent,
    extract_phone_numbers,
    haversine_km,
    normalize_name,
    normalize_phone,
)
from app.models import AuthorizedDealer, ObservedAsset, ObservedPlace, SourceType
from app.services.demo_data import demo_dealers


def test_normalize_name():
    assert normalize_name("YAMAHA BELLO S.A.S.") == "yamaha bello s a s"


def test_normalize_phone():
    assert normalize_phone("+57 301 444 0101") == "3014440101"


def test_extract_phone_numbers():
    assert extract_phone_numbers("Escribenos al 301 999 8888 hoy") == ["3019998888"]


def test_extract_phone_numbers_filters_ocr_noise():
    text = "YAMAHA 311 8575327 CRA 52 #10-161 GUAYABAL 0263118575"
    assert extract_phone_numbers(text) == ["3118575327"]


def test_haversine_is_small_for_nearby_points():
    distance = haversine_km(6.3364, -75.5552, 6.3371, -75.5549)
    assert distance < 0.1


def test_score_place_detects_clone():
    dealer = demo_dealers()[0]
    place = ObservedPlace(
        id="p1",
        place_id="clone1",
        name="Yamaha Bello Principal",
        address="Diagonal 50 45-12, Bello",
        phone_number="3019998888",
        category="motorcycle_repair_shop",
        latitude=6.3371,
        longitude=-75.5549,
        source_query="yamaha bello",
        query_rank=1,
        user_rating_count=2,
        rating=3.2,
        first_seen_at=datetime.now(UTC) - timedelta(days=2),
    )
    assessment = ForensicAgent().classify_place(dealer, place)
    score, reasons = assessment.score, assessment.reasons
    assert assessment.classification == "clone_risk"
    assert assessment.should_open_case is True
    assert score >= 70
    assert any("telefono" in reason.lower() or "datos operativos" in reason.lower() for reason in reasons)


def test_official_match_detects_real_dealer():
    dealer = demo_dealers()[2]
    place = ObservedPlace(
        id="p-official",
        place_id="official1",
        name="Mundo Yamaha Guayabal",
        address="Calle 10 55-87, Medellin",
        phone_number="6044440303",
        category="motorcycle_dealer",
        latitude=6.2157,
        longitude=-75.5918,
        source_query="yamaha guayabal",
    )
    forensic = ForensicAgent()
    assert forensic.looks_like_official_place(dealer, place) is True
    score, _ = forensic.score_place(dealer, place)
    assert score < 40


def test_official_match_accepts_incolmotos_yamaha_alias_at_exact_official_site():
    dealer = AuthorizedDealer(
        id="dealer-incolmotos-pdv-centro",
        organization_id="org-incolmotos",
        name="Incolmotos Yamaha",
        city="Medellin",
        address="CL 37 # 45-65",
        phone_numbers=["6042321316", "6042326006", "3104424205"],
        latitude=6.2372118,
        longitude=-75.5709811,
    )
    place = ObservedPlace(
        id="p-incolmotos-official",
        place_id="ChIJuW-GbQApRI4RgonrTqEC5Os",
        name="YAMAHA PRINCIPAL SAN DIEGO LA CANDELARIA",
        address="Cl. 37 #45-65, La Candelaria, Medellin, Antioquia, Colombia",
        phone_number="300 1154464",
        category="store",
        latitude=6.2372118,
        longitude=-75.5709811,
        source_query="yamaha principal medellin",
        query_rank=2,
    )
    assessment = ForensicAgent().classify_place(dealer, place)
    assert assessment.classification == "official_match"
    assert assessment.should_open_case is False


def test_score_place_works_without_coordinates():
    dealer = demo_dealers()[0]
    dealer.latitude = None
    dealer.longitude = None
    place = ObservedPlace(
        id="p2",
        place_id="clone2",
        name="Yamaha Bello Principal",
        address="Bello Antioquia",
        phone_number="3019998888",
        category="motorcycle_repair_shop",
        latitude=6.3371,
        longitude=-75.5549,
        source_query="yamaha bello",
    )
    score, _ = ForensicAgent().score_place(dealer, place)
    assert score >= 50


def test_classify_place_marks_legit_non_official_workshop_without_case():
    dealer = demo_dealers()[0]
    place = ObservedPlace(
        id="p-legit",
        place_id="legit1",
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
    assessment = ForensicAgent().classify_place(dealer, place)
    assert assessment.classification == "non_official_legit"
    assert assessment.should_open_case is False
    assert assessment.score < 72
    assert assessment.subscores["non_official_legitimacy"] >= 20


def test_classify_place_keeps_consolidated_non_official_dealer_out_of_clone_risk():
    dealer = demo_dealers()[2]
    place = ObservedPlace(
        id="p-legit-dealer",
        place_id="legit-dealer-1",
        name="Yamaha San Diego Medellin",
        address="Cl. 37 #45-65, La Candelaria, Medellin, Antioquia, Colombia",
        phone_number="6045552233",
        category="motorcycle_dealer",
        latitude=6.2475,
        longitude=-75.5680,
        source_query="yamaha oficial medellin",
        query_rank=2,
        user_rating_count=1912,
        rating=4.5,
    )
    assessment = ForensicAgent().classify_place(dealer, place)
    assert assessment.classification == "non_official_legit"
    assert assessment.should_open_case is False
    assert assessment.subscores["trust_deficit"] == 0


def test_classify_place_keeps_high_visibility_clone_risk_when_near_official():
    dealer = demo_dealers()[1]
    dealer.name = "GP Bikes Envigado"
    dealer.city = "Envigado"
    dealer.address = "Cra. 42 #38a sur 30, Envigado"
    dealer.latitude = 6.1700
    dealer.longitude = -75.5800
    place = ObservedPlace(
        id="p-clone-gpbikes",
        place_id="clone-gpbikes-1",
        name="YAMAHA ENVIGADO GP BIKES",
        address="Cra. 42 #38a sur 34, Envigado, Antioquia, Colombia",
        phone_number="3019998888",
        category="motorcycle_dealer",
        latitude=dealer.latitude + 0.0002,
        longitude=dealer.longitude + 0.0002,
        source_query="yamaha oficial envigado",
        query_rank=1,
        user_rating_count=172,
        rating=4.1,
    )
    assessment = ForensicAgent().classify_place(dealer, place)
    assert assessment.classification == "clone_risk"
    assert assessment.should_open_case is True
    assert assessment.score >= 68


def test_classify_place_flags_city_borrowing_clone_with_mid_review_volume():
    dealer = demo_dealers()[1]
    dealer.name = "GP Bikes Sabaneta"
    dealer.city = "Sabaneta"
    dealer.address = "Cra. 43C #67 sur 05, Sabaneta"
    dealer.latitude = 6.1518
    dealer.longitude = -75.6167
    place = ObservedPlace(
        id="p-clone-sabaneta",
        place_id="clone-sabaneta-1",
        name="YAMAHA SABANETA GP BIKES",
        address="Cra. 43C #67 sur 07, Sabaneta, Antioquia, Colombia",
        phone_number="3019997777",
        category="motorcycle_dealer",
        latitude=dealer.latitude + 0.0002,
        longitude=dealer.longitude + 0.0002,
        source_query="yamaha oficial sabaneta",
        query_rank=1,
        user_rating_count=101,
        rating=4.3,
    )
    assessment = ForensicAgent().classify_place(dealer, place)
    assert assessment.classification == "clone_risk"
    assert assessment.should_open_case is True


def test_classify_place_keeps_colocated_low_review_alias_as_context():
    dealer = demo_dealers()[2]
    dealer.name = "Yamaha Sports Colombia"
    dealer.city = "Medellin"
    dealer.address = "C. 50 #64C-53, Laureles - Estadio, Medellin"
    dealer.latitude = 6.2512
    dealer.longitude = -75.5903
    place = ObservedPlace(
        id="p-sports-alias",
        place_id="sports-alias-1",
        name="YAMAHA SPORTS AV LAURELES",
        address="C. 50 #64C-53, Laureles - Estadio, Medellin, Antioquia, Colombia",
        phone_number="6049992233",
        category="motorcycle_dealer",
        latitude=dealer.latitude + 0.0001,
        longitude=dealer.longitude + 0.0001,
        source_query="yamaha oficial medellin",
        query_rank=8,
        user_rating_count=3,
        rating=5.0,
    )
    assessment = ForensicAgent().classify_place(dealer, place)
    assert assessment.classification == "non_official_legit"
    assert assessment.should_open_case is False


def test_classify_place_flags_high_risk_urban_brand_hijack():
    dealer = demo_dealers()[1]
    place = ObservedPlace(
        id="p-urban-hijack",
        place_id="urban-hijack-1",
        name="YAMAHA PRINCIPAL MEDELLIN",
        address="Cl. 52 #49-10, Los Naranjos, Itagui, Medellin, Antioquia, Colombia",
        phone_number="6049992233",
        category="motorcycle_dealer",
        latitude=6.1719,
        longitude=-75.6114,
        source_query="yamaha principal medellin",
        query_rank=1,
        user_rating_count=5,
        rating=5.0,
        first_seen_at=datetime.now(UTC) - timedelta(days=45),
    )
    assessment = ForensicAgent().classify_place(dealer, place)
    assert assessment.classification == "clone_risk"
    assert assessment.should_open_case is True
    assert assessment.subscores["geo_takeover"] >= 8
    assert assessment.subscores["official_mismatch"] >= 20


def test_classify_place_routes_generic_city_borrowing_point_to_watchlist():
    dealer = demo_dealers()[1]
    dealer.name = "Moto Medina"
    dealer.city = "Copacabana"
    dealer.address = "Cl. 52 #11-40, Copacabana"
    dealer.latitude = 6.3480
    dealer.longitude = -75.5101
    place = ObservedPlace(
        id="p-watchlist-copacabana",
        place_id="watchlist-copacabana-1",
        name="YAMAHA MOTOS COPACABANA",
        address="Cl. 52 #11 # 50a, Copacabana, Antioquia, Colombia",
        phone_number="6049992233",
        category="motorcycle_dealer",
        latitude=dealer.latitude + 0.0001,
        longitude=dealer.longitude + 0.0001,
        source_query="yamaha oficial copacabana",
        query_rank=1,
        user_rating_count=23,
        rating=4.2,
    )
    assessment = ForensicAgent().classify_place(dealer, place)
    assert assessment.classification == "high_risk_watchlist"
    assert assessment.should_open_case is True



def test_score_asset_detects_fake_phone():
    dealer = demo_dealers()[0]
    asset = ObservedAsset(
        id="a1",
        profile_id="profile-bello",
        source_type=SourceType.OFFICIAL_PROFILE_UPDATE,
        review_text="Escribenos al nuevo numero 301 999 8888",
        extracted_text="301 999 8888",
    )
    score, reasons = ForensicAgent().score_asset(dealer, asset)
    assert score >= 60
    assert any("telefono distinto" in reason.lower() for reason in reasons)


def test_score_asset_escalates_gallery_facade_with_fake_phone():
    dealer = demo_dealers()[2]
    asset = ObservedAsset(
        id="a2",
        profile_id="profile-guayabal",
        source_type=SourceType.REVIEW_PHOTO,
        extracted_text="Mundo Yamaha Guayabal 311 857 5327",
        raw_payload={
            "capture_mode": "experimental_browser_capture_desktop",
            "gallery_opened": True,
            "all_media_selected": True,
        },
    )
    score, reasons = ForensicAgent().score_asset(dealer, asset)
    assert score >= 85
    assert any("galeria publica" in reason.lower() for reason in reasons)
    assert any("fachada capturada" in reason.lower() for reason in reasons)
