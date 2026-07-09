from app.models import AuthorizedDealer
from app.services.whitelist import (
    merge_official_yamaha_dealers,
    official_yamaha_dealers_from_distributors,
    parse_influence,
    parse_phone_candidates,
)


def test_parse_influence_extracts_radius():
    label, radius = parse_influence("Sector Niquía y Bello Centro  7")
    assert label == "Sector Niquía y Bello Centro"
    assert radius == 7.0


def test_parse_phone_candidates_normalizes_values():
    phones = parse_phone_candidates("444 31 32", "316 921 7078")
    assert "6044443132" in phones
    assert "3169217078" in phones


def test_parse_phone_candidates_extracts_multiple_official_numbers():
    phones = parse_phone_candidates("(604) 2321316-2326006 - 3104424205", "")
    assert phones == ["6042321316", "6042326006", "3104424205"]


def test_parse_phone_candidates_uses_context_area_code_for_bogota():
    phones = parse_phone_candidates("3904947 - 3183999475", "", default_area_code="601")
    assert phones == ["6013904947", "3183999475"]


def test_official_yamaha_dealers_filters_medellin_tienda_rows():
    rows = [
        {
            "id": "261",
            "id_departamento": "5",
            "municipio": "Medellín",
            "nombre": "INCOLMOTOS YAMAHA",
            "direccion": "CL 37 # 45-65",
            "telefono": "(604) 2321316-2326006 - 3104424205",
            "tienda": "SI",
            "lat": "6.23732",
            "log": "-75.571001",
        },
        {
            "id": "2449",
            "id_departamento": "5",
            "municipio": "Medellín",
            "nombre": "MUNDO YAMAHA",
            "direccion": "CRA 73 44 10",
            "telefono": "(604) 4443132 4128488",
            "tienda": "SI",
            "lat": "6.249831",
            "log": "-75.592213",
        },
        {
            "id": "999",
            "id_departamento": "5",
            "municipio": "Bello",
            "nombre": "MUNDO YAMAHA BELLO",
            "direccion": "CRA 50 33 73",
            "telefono": "3189248193",
            "tienda": "SI",
            "lat": "6.3223266",
            "log": "-75.5575552",
        },
    ]
    dealers = official_yamaha_dealers_from_distributors(rows)
    assert [dealer.id for dealer in dealers] == ["dealer-official-yamaha-261", "dealer-official-yamaha-2449"]
    assert dealers[0].phone_numbers == ["6042321316", "6042326006", "3104424205"]
    assert dealers[1].phone_numbers == ["6044443132", "6044128488"]


def test_official_yamaha_dealers_filters_bogota_aliases_and_uses_601_area_code():
    rows = [
        {
            "id": "3093",
            "id_departamento": "11",
            "municipio": "Bogotá D.C.",
            "nombre": "MOTOAUTO STORE S.A.S",
            "direccion": "AUT NORTE 127 A 09",
            "telefono": "3904947",
            "whatsapp": "3183999475",
            "tienda": "SI",
            "lat": "4.709237128962763",
            "log": "-74.05418157694143",
        },
        {
            "id": "3053",
            "id_departamento": "11",
            "municipio": "Bogotá. D.C.",
            "nombre": "MOTOR UNO",
            "direccion": "CRA 80 42A 55 SUR",
            "telefono": "7465390 - 7465391",
            "whatsapp": "",
            "tienda": "SI",
            "lat": "4.6226381",
            "log": "-74.1668833",
        },
        {
            "id": "999",
            "id_departamento": "11",
            "municipio": "Bogotá D.C.",
            "nombre": "SERVICIO NO TIENDA",
            "direccion": "CRA 1 2 3",
            "telefono": "1234567",
            "tienda": "NO",
            "lat": "4.60",
            "log": "-74.10",
        },
    ]

    dealers = official_yamaha_dealers_from_distributors(
        rows,
        department_id="11",
        city="Bogotá D.C.",
        city_aliases=["Bogotá. D.C."],
    )

    assert [dealer.id for dealer in dealers] == ["dealer-official-yamaha-3093", "dealer-official-yamaha-3053"]
    assert dealers[0].phone_numbers == ["6013904947", "3183999475"]
    assert dealers[1].phone_numbers == ["6017465390", "6017465391"]
    assert {dealer.city for dealer in dealers} == {"Bogotá D.C."}


def test_merge_official_yamaha_dealers_updates_near_existing_dealer_without_changing_identity():
    existing = AuthorizedDealer(
        id="dealer-mundo-yamaha-san-juan",
        organization_id="org-mundo-yamaha",
        name="Mundo Yamaha San Juan",
        city="Medellin",
        address="Carrera 73 # 44 - 10 1",
        phone_numbers=["6044443132", "3169217078"],
        latitude=6.2499727,
        longitude=-75.5921427,
    )
    official = AuthorizedDealer(
        id="dealer-official-yamaha-2449",
        organization_id="org-yamaha-network",
        name="MUNDO YAMAHA",
        city="Medellín",
        address="CRA 73 44 10",
        phone_numbers=["6044443132", "6044128488"],
        latitude=6.249831,
        longitude=-75.592213,
    )
    merged = merge_official_yamaha_dealers([existing], [official])
    assert len(merged) == 1
    assert merged[0].id == "dealer-mundo-yamaha-san-juan"
    assert merged[0].organization_id == "org-mundo-yamaha"
    assert merged[0].name == "Mundo Yamaha San Juan"
    assert merged[0].address == "CRA 73 44 10"
    assert merged[0].phone_numbers == ["6044443132", "6044128488", "3169217078"]
