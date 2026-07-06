from __future__ import annotations

import unicodedata
from collections.abc import Mapping

from app.models import AuthorizedDealer, ThreatCase


def normalize_lookup_text(value: str | None) -> str:
    if not value:
        return ""
    normalized = unicodedata.normalize("NFD", value.strip().lower())
    without_accents = "".join(char for char in normalized if unicodedata.category(char) != "Mn")
    return " ".join(without_accents.replace("-", " ").split())


def resolve_case_organization_id(
    case: ThreatCase,
    dealers: Mapping[str, AuthorizedDealer],
) -> str | None:
    if case.organization_id:
        return case.organization_id

    direct_dealer = dealers.get(case.dealer_id)
    if direct_dealer and direct_dealer.organization_id:
        return direct_dealer.organization_id

    case_dealer_name = normalize_lookup_text(case.dealer_name)
    case_city = normalize_lookup_text(case.city)
    if not case_dealer_name:
        return None

    candidates = [
        dealer
        for dealer in dealers.values()
        if dealer.organization_id and normalize_lookup_text(dealer.name) == case_dealer_name
    ]
    if case_city:
        city_match = next((dealer for dealer in candidates if normalize_lookup_text(dealer.city) == case_city), None)
        if city_match:
            return city_match.organization_id
    if len(candidates) == 1:
        return candidates[0].organization_id
    return None
