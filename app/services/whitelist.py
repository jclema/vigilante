from __future__ import annotations

import csv
import json
import re
import ssl
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.agents.forensic import haversine_km, normalize_phone, official_address_matches
from app.models import AuthorizedDealer
from app.services.geocoding import GeocodingService


OFFICIAL_YAMAHA_DISTRIBUTORS_URL = "https://www.incolmotos-yamaha.com.co/wp-json/v2/distributors/"


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


def _extract_phone_numbers(raw_value: str) -> list[str]:
    groups = re.findall(r"\d+", raw_value or "")
    compact_digits = "".join(groups)
    if len(compact_digits) in {7, 10}:
        normalized = normalize_phone(compact_digits)
        return [normalized] if normalized else []

    numbers: list[str] = []
    last_area_code: str | None = None
    index = 0
    while index < len(groups):
        group = groups[index]
        if len(group) == 3 and group.startswith("60") and index + 1 < len(groups) and len(groups[index + 1]) == 7:
            normalized = normalize_phone(group + groups[index + 1])
            last_area_code = group
            index += 2
        elif len(group) == 10:
            normalized = normalize_phone(group)
            if normalized.startswith("60"):
                last_area_code = normalized[:3]
            index += 1
        elif len(group) == 7:
            normalized = normalize_phone(f"{last_area_code or '604'}{group}")
            index += 1
        else:
            normalized = normalize_phone(group)
            index += 1

        if normalized and normalized not in numbers:
            numbers.append(normalized)
    return numbers


def parse_phone_candidates(fixed_phone: str, mobile_phone: str) -> list[str]:
    numbers: list[str] = []
    for value in [fixed_phone, mobile_phone]:
        cleaned = compact_spaces(value)
        if not cleaned or cleaned.upper() == "N/A":
            continue
        for normalized in _extract_phone_numbers(cleaned):
            if normalized not in numbers:
                numbers.append(normalized)
    return numbers


def fetch_official_yamaha_distributors(
    url: str = OFFICIAL_YAMAHA_DISTRIBUTORS_URL,
    *,
    timeout: int = 90,
) -> list[dict[str, Any]]:
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 Vigilante/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = response.read().decode("utf-8")
    except (ssl.SSLCertVerificationError, urllib.error.URLError) as exc:
        if isinstance(exc, urllib.error.URLError) and not isinstance(exc.reason, ssl.SSLCertVerificationError):
            raise
        context = ssl._create_unverified_context()  # noqa: S323
        with urllib.request.urlopen(request, timeout=timeout, context=context) as response:
            payload = response.read().decode("utf-8")
    data = json.loads(payload)
    if not isinstance(data, list):
        raise ValueError("Official Yamaha distributors endpoint did not return a list")
    return data


def official_yamaha_dealers_from_distributors(
    rows: list[dict[str, Any]],
    *,
    department_id: str = "5",
    city: str = "Medellín",
    organization_id: str | None = "org-yamaha-network",
) -> list[AuthorizedDealer]:
    dealers: list[AuthorizedDealer] = []
    normalized_city = compact_spaces(city).lower()
    for row in rows:
        if str(row.get("tienda", "")).upper() != "SI":
            continue
        if str(row.get("id_departamento", "")) != department_id:
            continue
        if compact_spaces(str(row.get("municipio", ""))).lower() != normalized_city:
            continue

        name = compact_spaces(str(row.get("nombre", "")))
        address = compact_spaces(str(row.get("direccion", "")))
        lat = _safe_float(row.get("lat"))
        lng = _safe_float(row.get("log"))
        if not name or not address or lat is None or lng is None:
            continue

        dealers.append(
            AuthorizedDealer(
                id=f"dealer-official-yamaha-{row.get('id')}",
                organization_id=organization_id,
                name=name,
                city=city,
                address=address,
                phone_numbers=parse_phone_candidates(str(row.get("telefono", "")), str(row.get("whatsapp", ""))),
                latitude=lat,
                longitude=lng,
                influence_label="Fuente oficial Incolmotos Yamaha",
            )
        )
    return dealers


def merge_official_yamaha_dealers(
    existing_dealers: list[AuthorizedDealer],
    official_dealers: list[AuthorizedDealer],
    *,
    max_merge_distance_km: float = 0.08,
) -> list[AuthorizedDealer]:
    merged_by_id = {dealer.id: dealer for dealer in existing_dealers}
    matched_existing_ids: set[str] = set()

    for official in official_dealers:
        existing = _find_existing_official_match(existing_dealers, official, matched_existing_ids, max_merge_distance_km)
        if existing is None:
            merged_by_id[official.id] = official
            continue

        matched_existing_ids.add(existing.id)
        merged_by_id[existing.id] = existing.model_copy(
            update={
                "address": official.address,
                "phone_numbers": _merge_phone_numbers(official.phone_numbers, existing.phone_numbers),
                "latitude": official.latitude,
                "longitude": official.longitude,
                "influence_label": official.influence_label or existing.influence_label,
                "influence_radius_km": existing.influence_radius_km,
            }
        )

    return list(merged_by_id.values())


def _find_existing_official_match(
    existing_dealers: list[AuthorizedDealer],
    official: AuthorizedDealer,
    matched_existing_ids: set[str],
    max_merge_distance_km: float,
) -> AuthorizedDealer | None:
    candidates: list[tuple[float, AuthorizedDealer]] = []
    for existing in existing_dealers:
        if existing.id in matched_existing_ids:
            continue
        if existing.latitude is None or existing.longitude is None:
            if official_address_matches(existing.address, official.address):
                candidates.append((0.0, existing))
            continue
        distance = haversine_km(existing.latitude, existing.longitude, official.latitude or 0, official.longitude or 0)
        if distance <= max_merge_distance_km or official_address_matches(existing.address, official.address):
            candidates.append((distance, existing))
    if not candidates:
        return None
    return sorted(candidates, key=lambda item: item[0])[0][1]


def _merge_phone_numbers(primary: list[str], secondary: list[str]) -> list[str]:
    merged: list[str] = []
    for number in [*primary, *secondary]:
        normalized = normalize_phone(number)
        if normalized and normalized not in merged:
            merged.append(normalized)
    return merged


def _safe_float(value: Any) -> float | None:
    try:
        return float(str(value).strip().strip(","))
    except (TypeError, ValueError):
        return None


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
