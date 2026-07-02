from __future__ import annotations

import json
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.config import settings
from app.models import ObservedPlace
from app.services.demo_data import suspicious_places


PLACES_SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"


@dataclass
class PlacesSearchService:
    api_key: str

    def is_configured(self) -> bool:
        return bool(self.api_key and not self.api_key.startswith("pending-"))

    def search_text(self, query: str) -> list[ObservedPlace]:
        if not self.is_configured():
            return suspicious_places()

        body = {
            "textQuery": query,
            "languageCode": "es",
            "maxResultCount": 10,
            "locationBias": {
                "rectangle": {
                    "low": {"latitude": 6.14, "longitude": -75.68},
                    "high": {"latitude": 6.39, "longitude": -75.52},
                }
            },
        }
        request = Request(
            PLACES_SEARCH_URL,
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "X-Goog-Api-Key": self.api_key,
                "X-Goog-FieldMask": (
                    "places.id,places.displayName,places.formattedAddress,"
                    "places.nationalPhoneNumber,places.location,places.primaryType,"
                    "places.rating,places.userRatingCount,places.businessStatus,"
                    "places.googleMapsUri"
                ),
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=20) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError):
            return suspicious_places()

        places: list[ObservedPlace] = []
        for index, item in enumerate(payload.get("places", []), start=1):
            location = item.get("location", {})
            places.append(
                ObservedPlace(
                    id=f"places-api-{index}",
                    place_id=item.get("id", f"unknown-{index}"),
                    name=item.get("displayName", {}).get("text", "Lugar sin nombre"),
                    address=item.get("formattedAddress", "Direccion no disponible"),
                    phone_number=item.get("nationalPhoneNumber"),
                    category=item.get("primaryType"),
                    latitude=location.get("latitude", 0.0),
                    longitude=location.get("longitude", 0.0),
                    source_query=query,
                    query_rank=index,
                    rating=item.get("rating"),
                    user_rating_count=item.get("userRatingCount"),
                    business_status=item.get("businessStatus"),
                    raw_payload=item,
                )
            )
        return places or suspicious_places()

    def search_clone_candidates(self, query: str) -> list[ObservedPlace]:
        variants = self._clone_query_variants(query)
        combined: list[ObservedPlace] = []
        for variant in variants:
            results = self.search_text(variant)
            for index, place in enumerate(results, start=1):
                place.source_query = variant
                place.query_rank = index
            combined.extend(results)
        return combined

    def _clone_query_variants(self, query: str) -> list[str]:
        cleaned = " ".join(query.split())
        lowered = cleaned.lower()
        if "yamaha" not in lowered:
            return [cleaned]
        suffix = cleaned.lower().replace("yamaha", "", 1).strip()
        if not suffix:
            return [cleaned]
        variants = [
            cleaned,
            f"yamaha principal {suffix}",
            f"yamaha oficial {suffix}",
            f"yamaha sede {suffix}",
        ]
        deduped: list[str] = []
        seen: set[str] = set()
        for item in variants:
            normalized = " ".join(item.split()).strip()
            if not normalized:
                continue
            key = normalized.lower()
            if key in seen:
                continue
            seen.add(key)
            deduped.append(normalized)
        return deduped


places_search_service = PlacesSearchService(settings.google_maps_api_key)
