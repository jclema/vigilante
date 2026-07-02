from app.services.whitelist import parse_influence, parse_phone_candidates


def test_parse_influence_extracts_radius():
    label, radius = parse_influence("Sector Niquía y Bello Centro  7")
    assert label == "Sector Niquía y Bello Centro"
    assert radius == 7.0


def test_parse_phone_candidates_normalizes_values():
    phones = parse_phone_candidates("444 31 32", "316 921 7078")
    assert "6044443132" in phones
    assert "3169217078" in phones
