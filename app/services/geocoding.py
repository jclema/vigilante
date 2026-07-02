from __future__ import annotations

import json
from dataclasses import dataclass
from urllib.parse import quote_plus
from urllib.request import urlopen


GEOCODING_URL = "https://maps.googleapis.com/maps/api/geocode/json"


@dataclass
class GeocodingService:
    api_key: str

    def is_configured(self) -> bool:
        return bool(self.api_key and not self.api_key.startswith("pending-"))

    def geocode_colombia_address(self, address: str) -> tuple[float | None, float | None]:
        if not self.is_configured():
            return None, None
        query = quote_plus(f"{address}, Antioquia, Colombia")
        with urlopen(f"{GEOCODING_URL}?address={query}&key={self.api_key}", timeout=20) as response:
            payload = json.loads(response.read().decode("utf-8"))
        results = payload.get("results", [])
        if not results:
            return None, None
        location = results[0].get("geometry", {}).get("location", {})
        return location.get("lat"), location.get("lng")

