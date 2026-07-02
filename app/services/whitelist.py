from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path

from app.agents.forensic import normalize_phone
from app.models import AuthorizedDealer
from app.services.geocoding import GeocodingService


def slugify(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return normalized


def compact_spaces(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def parse_influence(raw_value: str) -> tuple[str | None, float | None]:
    value = compact_spaces(raw_value)
    if not value or value.upper() == "N/A":
        return None, None
    match = re.search(r"(.+?)\s+(\d+(?:[.,]\d+)?)$", value)
    if not match:
        return value, None
    label = compact_spaces(match.group(1))
    radius = float(match.group(2).replace(",", "."))
    return label, radius


def parse_phone_candidates(fixed_phone: str, mobile_phone: str) -> list[str]:
    numbers: list[str] = []
    for value in [fixed_phone, mobile_phone]:
        cleaned = compact_spaces(value)
        if not cleaned or cleaned.upper() == "N/A":
            continue
        normalized = normalize_phone(cleaned)
        if normalized and normalized not in numbers:
            numbers.append(normalized)
    return numbers


@dataclass
class WhitelistImporter:
    geocoding: GeocodingService

    def import_csv(self, csv_path: str | Path) -> list[AuthorizedDealer]:
        path = Path(csv_path)
        dealers: list[AuthorizedDealer] = []
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                name = compact_spaces(row["Concesionario / Sede"])
                city = compact_spaces(row["Municipio"])
                address = compact_spaces(row["Dirección Oficial"])
                influence_label, influence_radius_km = parse_influence(row["Radio Geográfico (Influencia)"])
                lat, lng = self.geocoding.geocode_colombia_address(f"{address}, {city}")
                dealers.append(
                    AuthorizedDealer(
                        id=f"dealer-{slugify(name)}",
                        name=name,
                        city=city,
                        address=address,
                        phone_numbers=parse_phone_candidates(row["Fijo (604)"], row["Móvil / WhatsApp"]),
                        latitude=lat,
                        longitude=lng,
                        influence_label=influence_label,
                        influence_radius_km=influence_radius_km,
                    )
                )
        return dealers
