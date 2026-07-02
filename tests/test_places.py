from app.services.places import PlacesSearchService


def test_places_falls_back_to_demo_without_real_key():
    service = PlacesSearchService("pending-maps-key")
    results = service.search_text("yamaha medellin")
    assert results
    assert any("Yamaha" in place.name for place in results)

