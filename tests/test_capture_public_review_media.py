from scripts.capture_public_review_media import (
    _candidate_profile_urls,
    _extract_place_id,
    _is_generic_maps_landing,
    _landing_matches_expected,
)


def test_extract_place_id_from_supported_url_formats():
    assert _extract_place_id("https://www.google.com/maps/place/?q=place_id:ChIJ123abc") == "ChIJ123abc"
    assert _extract_place_id("https://www.google.com/maps/search/?api=1&query=Google&query_place_id=ChIJxyz789") == "ChIJxyz789"


def test_candidate_profile_urls_prioritize_alternatives_for_place_id():
    urls = _candidate_profile_urls("https://www.google.com/maps/place/?q=place_id:ChIJ123abc")
    assert urls[0] == "https://www.google.com/maps/place/?q=place_id:ChIJ123abc"
    assert "https://www.google.com/maps/search/?api=1&query=Google&query_place_id=ChIJ123abc" in urls


def test_is_generic_maps_landing_detects_map_view_without_place():
    assert _is_generic_maps_landing("https://www.google.com/maps/@41.2288,-95.839574,11z?entry=ttu")
    assert not _is_generic_maps_landing("https://www.google.com/maps/place/Motoblu+Bello/")


def test_landing_matches_expected_by_full_name_or_tokens():
    assert _landing_matches_expected("Motoblu Bello Calle 33 Itagui Fotos", "Motoblu Bello")
    assert _landing_matches_expected("Mundo Yamaha Guayabal abierto ahora", "Mundo Yamaha Guayabal")
    assert not _landing_matches_expected("Google Maps Omaha Nebraska", "Motoblu Bello")
