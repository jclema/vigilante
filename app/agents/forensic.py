from __future__ import annotations

import math
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from difflib import SequenceMatcher

from app.models import AuthorizedDealer, ObservedAsset, ObservedPlace, SourceType


PHONE_PATTERN = re.compile(r"(?:\+?57)?\D*(\d{3})\D*(\d{3})\D*(\d{4})")
AUTHORITY_KEYWORDS = {
    "principal",
    "oficial",
    "sede",
    "centro",
    "entregas",
}
GENERIC_DEALER_TERMS = {"yamaha", "moto", "motos", "motor", "motors", "oficial", "principal"}
LEGIT_NON_OFFICIAL_CATEGORIES = {
    "motorcycle_repair_shop",
    "store",
    "auto_parts_store",
    "motorcycle_parts_store",
}


@dataclass(slots=True)
class CloneAssessment:
    classification: str
    score: int
    should_open_case: bool
    subscores: dict[str, int]
    reasons: list[str]


def normalize_name(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9\s]", " ", value.lower())
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def normalize_phone(value: str) -> str:
    digits = re.sub(r"\D", "", value)
    if digits.startswith("57") and len(digits) > 10:
        digits = digits[-10:]
    if len(digits) == 7:
        return f"604{digits}"
    return digits


def is_likely_colombian_phone(value: str) -> bool:
    if len(value) != 10:
        return False
    return value.startswith("3") or value.startswith("60")


def extract_phone_numbers(text: str | None) -> list[str]:
    if not text:
        return []
    matches = PHONE_PATTERN.findall(text)
    normalized = [normalize_phone("".join(parts)) for parts in matches]
    deduped: list[str] = []
    seen: set[str] = set()
    for number in normalized:
        if not is_likely_colombian_phone(number):
            continue
        if number in seen:
            continue
        seen.add(number)
        deduped.append(number)
    return deduped


def name_similarity(a: str, b: str) -> float:
    return SequenceMatcher(a=normalize_name(a), b=normalize_name(b)).ratio()


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return radius * c


class ForensicAgent:
    def official_match_score(self, dealer: AuthorizedDealer, place: ObservedPlace) -> int:
        score = 0
        place_name = normalize_name(place.name)
        dealer_name = normalize_name(dealer.name)
        place_address = normalize_name(place.address)
        dealer_address = normalize_name(dealer.address)
        place_phone = normalize_phone(place.phone_number or "")
        known_numbers = {normalize_phone(number) for number in dealer.phone_numbers}
        similarity = name_similarity(dealer.name, place.name)
        address_match = bool(dealer_address and dealer_address in place_address)
        distance: float | None = None

        if similarity >= 0.86:
            score += 35
        elif similarity >= 0.72:
            score += 20

        if address_match:
            score += 35

        if place_phone and place_phone in known_numbers:
            score += 35

        if dealer.latitude is not None and dealer.longitude is not None:
            distance = haversine_km(dealer.latitude, dealer.longitude, place.latitude, place.longitude)
            if distance <= 0.15:
                score += 20
            elif distance <= 0.4:
                score += 10

        if dealer.city and normalize_name(dealer.city) in place_address:
            score += 5

        if "yamaha" in place_name and "yamaha" in dealer_name:
            score += 5

        if (
            address_match
            and distance is not None
            and distance <= 0.05
            and self._has_strong_suspicious_branding(place)
            and self._has_official_brand_overlap(dealer, place)
        ):
            score += 10

        return score

    def dealer_relevance_score(self, dealer: AuthorizedDealer, place: ObservedPlace) -> int:
        score = 0
        similarity = name_similarity(dealer.name, place.name)
        place_address = normalize_name(place.address)
        keywords = self._matched_authority_keywords(place, dealer)

        if similarity >= 0.55:
            score += int(similarity * 40)
        if keywords:
            score += 20 + min(10, len(keywords) * 5)

        if dealer.city and normalize_name(dealer.city) in place_address:
            score += 25

        if dealer.latitude is not None and dealer.longitude is not None:
            distance = haversine_km(dealer.latitude, dealer.longitude, place.latitude, place.longitude)
            influence_radius_km = dealer.influence_radius_km or 3.0
            if distance <= 0.75:
                score += 30
            elif distance <= influence_radius_km:
                score += 18

        place_phone = normalize_phone(place.phone_number or "")
        known_numbers = {normalize_phone(number) for number in dealer.phone_numbers}
        if place_phone and place_phone in known_numbers:
            score += 25

        return score

    def looks_like_official_place(self, dealer: AuthorizedDealer, place: ObservedPlace) -> bool:
        return self.official_match_score(dealer, place) >= 70

    def score_place(self, dealer: AuthorizedDealer, place: ObservedPlace) -> tuple[int, list[str]]:
        assessment = self.classify_place(dealer, place)
        return assessment.score, assessment.reasons

    def classify_place(self, dealer: AuthorizedDealer, place: ObservedPlace) -> CloneAssessment:
        if self.looks_like_official_place(dealer, place):
            return CloneAssessment(
                classification="official_match",
                score=0,
                should_open_case=False,
                subscores={},
                reasons=["El punto coincide con los datos oficiales autorizados."],
            )

        subscores = {
            "authority_keyword_misuse": self._authority_keyword_subscore(dealer, place),
            "whitelist_mismatch": self._whitelist_mismatch_subscore(dealer, place),
            "geo_takeover": self._geo_takeover_subscore(dealer, place),
            "findability": self._findability_subscore(place),
            "trust_deficit": self._trust_deficit_subscore(place),
            "non_official_legitimacy": self._non_official_legitimacy_subscore(dealer, place),
            "official_mismatch": self._official_mismatch_subscore(dealer, place),
        }

        clone_score = min(
            100,
            subscores["authority_keyword_misuse"]
            + subscores["whitelist_mismatch"]
            + subscores["geo_takeover"]
            + subscores["findability"]
            + subscores["trust_deficit"]
            + subscores["official_mismatch"]
            - subscores["non_official_legitimacy"],
        )
        clone_score = max(0, clone_score)

        review_count = place.user_rating_count or 0
        strong_branding = self._has_strong_suspicious_branding(place)
        co_located_alias = self._looks_like_colocated_alias(dealer, place)
        dealer_name_similarity = name_similarity(dealer.name, place.name)
        dealer_brand_overlap = self._has_dealer_distinctive_overlap(dealer, place)
        strong_clone_pattern = (
            subscores["authority_keyword_misuse"] >= 22
            and subscores["geo_takeover"] >= 24
            and subscores["findability"] >= 18
        )
        urban_hijack_pattern = (
            strong_branding
            and subscores["whitelist_mismatch"] >= 12
            and subscores["findability"] >= 24
            and subscores["official_mismatch"] >= 20
            and subscores["trust_deficit"] >= 8
            and subscores["geo_takeover"] >= 8
        )
        legitimacy_high = subscores["non_official_legitimacy"] >= 24 and subscores["trust_deficit"] <= 10
        watchlist_pattern = (
            not strong_branding
            and subscores["geo_takeover"] >= 24
            and subscores["findability"] >= 18
            and subscores["official_mismatch"] >= 20
            and legitimacy_high
            and review_count >= 20
            and dealer_name_similarity < 0.45
            and not dealer_brand_overlap
        )
        legitimacy_override = (
            subscores["non_official_legitimacy"] >= 28
            and subscores["trust_deficit"] == 0
            and review_count >= 300
            and not strong_branding
        )
        suspicious_total = sum(
            1
            for key in ("authority_keyword_misuse", "whitelist_mismatch", "geo_takeover", "findability", "official_mismatch")
            if subscores[key] >= 10
        )

        if legitimacy_override:
            classification = "non_official_legit"
            should_open = False
        elif co_located_alias:
            classification = "non_official_legit"
            should_open = False
        elif clone_score >= 68 and watchlist_pattern and suspicious_total >= 3:
            classification = "high_risk_watchlist"
            should_open = True
        elif legitimacy_high and not strong_clone_pattern and clone_score < 68:
            classification = "non_official_legit"
            should_open = False
        elif clone_score >= 68 and (strong_clone_pattern or urban_hijack_pattern) and suspicious_total >= 3:
            classification = "clone_risk"
            should_open = True
        else:
            classification = "non_official_legit"
            should_open = False

        reasons = self._build_place_reasons(dealer, place, subscores, classification)
        return CloneAssessment(
            classification=classification,
            score=clone_score,
            should_open_case=should_open,
            subscores=subscores,
            reasons=reasons,
        )

    def _matched_authority_keywords(self, place: ObservedPlace, dealer: AuthorizedDealer) -> list[str]:
        text = " ".join(
            part
            for part in [normalize_name(place.name), normalize_name(place.address), normalize_name(dealer.city)]
            if part
        )
        matched = [keyword for keyword in AUTHORITY_KEYWORDS if keyword in text]
        if normalize_name(dealer.city) and normalize_name(dealer.city) in normalize_name(place.name):
            matched.append(normalize_name(dealer.city))
        return sorted(set(matched))

    def _has_strong_suspicious_branding(self, place: ObservedPlace) -> bool:
        place_name = normalize_name(place.name)
        return any(keyword in place_name for keyword in {"principal", "oficial"})

    def _has_dealer_distinctive_overlap(self, dealer: AuthorizedDealer, place: ObservedPlace) -> bool:
        dealer_terms = {
            term
            for term in normalize_name(dealer.name).split()
            if len(term) >= 4 and term not in GENERIC_DEALER_TERMS and term != normalize_name(dealer.city)
        }
        place_terms = set(normalize_name(place.name).split())
        return bool(dealer_terms.intersection(place_terms))

    def _has_official_brand_overlap(self, dealer: AuthorizedDealer, place: ObservedPlace) -> bool:
        dealer_terms = set(normalize_name(dealer.name).split())
        place_terms = set(normalize_name(place.name).split())
        return "yamaha" in dealer_terms and "yamaha" in place_terms

    def _looks_like_colocated_alias(self, dealer: AuthorizedDealer, place: ObservedPlace) -> bool:
        place_name = normalize_name(place.name)
        dealer_city = normalize_name(dealer.city)
        review_count = place.user_rating_count or 0
        return (
            "yamaha" in place_name
            and not self._has_strong_suspicious_branding(place)
            and review_count <= 20
            and self._geo_takeover_subscore(dealer, place) >= 24
            and dealer_city not in place_name
        )

    def _authority_keyword_subscore(self, dealer: AuthorizedDealer, place: ObservedPlace) -> int:
        place_name = normalize_name(place.name)
        if "yamaha" not in place_name:
            return 0
        matched_keywords = self._matched_authority_keywords(place, dealer)
        review_count = place.user_rating_count or 0
        score = 12
        if any(keyword in matched_keywords for keyword in {"principal", "oficial"}):
            score += 18
        if normalize_name(dealer.city) in place_name or normalize_name(dealer.city) in normalize_name(place.address):
            score += 10
            if review_count and review_count <= 150:
                score += 4
        if name_similarity(dealer.name, place.name) >= 0.6:
            score += 8
        return min(score, 38)

    def _whitelist_mismatch_subscore(self, dealer: AuthorizedDealer, place: ObservedPlace) -> int:
        similarity = name_similarity(dealer.name, place.name)
        exact_name = normalize_name(dealer.name) == normalize_name(place.name)
        if exact_name:
            return 0
        if similarity >= 0.7:
            return 18
        if "yamaha" in normalize_name(place.name):
            return 12
        return 0

    def _geo_takeover_subscore(self, dealer: AuthorizedDealer, place: ObservedPlace) -> int:
        if dealer.latitude is None or dealer.longitude is None:
            return 6 if normalize_name(dealer.city) in normalize_name(place.address) else 0
        distance = haversine_km(dealer.latitude, dealer.longitude, place.latitude, place.longitude)
        influence_radius_km = dealer.influence_radius_km or 2.0
        if distance <= 0.05:
            return 30
        if distance <= 0.15:
            return 24
        if distance <= min(influence_radius_km, 0.5):
            return 18
        if distance <= max(1.0, influence_radius_km):
            return 8
        return 0

    def _findability_subscore(self, place: ObservedPlace) -> int:
        query = normalize_name(place.source_query)
        place_name = normalize_name(place.name)
        score = 0
        if place.query_rank and place.query_rank <= 3:
            score += 12
        elif place.query_rank and place.query_rank <= 5:
            score += 8
        if "yamaha" in query and any(keyword in query for keyword in AUTHORITY_KEYWORDS):
            score += 10
        if "yamaha" in place_name and any(keyword in place_name for keyword in AUTHORITY_KEYWORDS):
            score += 6
        query_hits = int(place.raw_payload.get("query_hit_count", 1) or 1)
        if query_hits >= 2:
            score += 8
        return min(score, 28)

    def _trust_deficit_subscore(self, place: ObservedPlace) -> int:
        score = 0
        review_count = place.user_rating_count or 0
        rating = place.rating or 0.0
        if review_count <= 3:
            score += 16
        elif review_count <= 10:
            score += 9
        if place.first_seen_at:
            age_days = max(0, (datetime.now(UTC) - place.first_seen_at.astimezone(UTC)).days)
            if age_days <= 14:
                score += 16
            elif age_days <= 90:
                score += 8
        if rating and rating < 3.5 and review_count > 0:
            score += 4
        return min(score, 28)

    def _non_official_legitimacy_subscore(self, dealer: AuthorizedDealer, place: ObservedPlace) -> int:
        score = 0
        review_count = place.user_rating_count or 0
        rating = place.rating or 0.0
        place_name = normalize_name(place.name)
        if review_count >= 20:
            score += 14
        elif review_count >= 8:
            score += 8
        if rating >= 4.2 and review_count >= 5:
            score += 6
        if place.category in LEGIT_NON_OFFICIAL_CATEGORIES:
            score += 12
        if "principal" not in place_name and "oficial" not in place_name:
            score += 4
        if normalize_name(dealer.city) not in place_name and normalize_name(dealer.address) not in normalize_name(place.address):
            score += 2
        return min(score, 34)

    def _official_mismatch_subscore(self, dealer: AuthorizedDealer, place: ObservedPlace) -> int:
        score = 0
        place_phone = normalize_phone(place.phone_number or "")
        known_numbers = {normalize_phone(number) for number in dealer.phone_numbers}
        if place_phone and place_phone not in known_numbers:
            score += 20
        if normalize_name(dealer.address) not in normalize_name(place.address):
            score += 8
        if place.category and place.category != "motorcycle_dealer":
            score += 6
        return min(score, 28)

    def _build_place_reasons(
        self,
        dealer: AuthorizedDealer,
        place: ObservedPlace,
        subscores: dict[str, int],
        classification: str,
    ) -> list[str]:
        reasons: list[str] = []
        matched_keywords = self._matched_authority_keywords(place, dealer)
        if subscores["authority_keyword_misuse"] >= 22:
            reasons.append(
                "Usa Yamaha junto con keywords de autoridad/ubicacion para parecer una sede oficial."
            )
        elif subscores["authority_keyword_misuse"] > 0:
            reasons.append("Usa la marca Yamaha con naming cercano a una sede oficial.")
        if matched_keywords:
            reasons.append(f"Keywords detectados: {', '.join(matched_keywords[:4])}.")
        if subscores["geo_takeover"] >= 24:
            reasons.append("Aparece extremadamente cerca o encima de una sede oficial.")
        elif subscores["geo_takeover"] >= 18:
            reasons.append("Aparece sospechosamente cerca de un concesionario real.")
        elif subscores["geo_takeover"] > 0:
            reasons.append("Aparece dentro del radio de influencia del concesionario.")
        if subscores["findability"] >= 12:
            reasons.append("Tiene findability competitiva en búsquedas de marca y sede.")
        if subscores["official_mismatch"] >= 20:
            reasons.append("Publica un telefono o datos operativos que no coinciden con la whitelist oficial.")
        elif subscores["whitelist_mismatch"] > 0:
            reasons.append("El nombre observado no coincide con los nombres autorizados de la red.")
        if subscores["trust_deficit"] >= 16:
            reasons.append("El punto parece nuevo o con muy poca tracción legítima.")
        elif subscores["trust_deficit"] > 0:
            reasons.append("Tiene señales débiles de confianza para el nivel de visibilidad que muestra.")
        if classification == "non_official_legit" and subscores["non_official_legitimacy"] >= 20:
            reasons.append("También muestra señales de negocio no oficial pero estable, por lo que no escala como clon.")
        return reasons[:6]

    def score_asset(self, dealer: AuthorizedDealer, asset: ObservedAsset) -> tuple[int, list[str]]:
        reasons: list[str] = []
        score = 0

        extracted_numbers = extract_phone_numbers(asset.extracted_text or asset.review_text)
        known_numbers = {normalize_phone(number) for number in dealer.phone_numbers}
        non_official_numbers = [number for number in extracted_numbers if number not in known_numbers]

        if extracted_numbers:
            score += 20
            reasons.append("La foto o review contiene un telefono visible.")

        if non_official_numbers:
            score += 45
            reasons.append("Se detecto un telefono distinto al oficial en contenido del perfil real.")

        text_blob = " ".join(
            part
            for part in [
                asset.extracted_text or "",
                asset.review_text or "",
                str(asset.raw_payload.get("description", "")),
            ]
            if part
        ).lower()

        if "yamaha" in text_blob:
            score += 8
            reasons.append("La marca Yamaha aparece dentro del contenido observado.")

        if any(word in text_blob for word in ["fachada", "sede", "punto", "local", "concesionario"]):
            score += 10
            reasons.append("La evidencia parece mostrar o describir una sede física.")

        capture_mode = str(asset.raw_payload.get("capture_mode", "")).lower()
        gallery_opened = bool(asset.raw_payload.get("gallery_opened"))
        all_media_selected = bool(asset.raw_payload.get("all_media_selected"))
        if asset.source_type == SourceType.REVIEW_PHOTO and gallery_opened:
            score += 8
            reasons.append("La captura proviene de la galeria publica del perfil oficial.")
        if asset.source_type == SourceType.REVIEW_PHOTO and all_media_selected:
            score += 6
            reasons.append("La evidencia fue tomada desde la vista completa de fotos publicas.")
        if "experimental_browser_capture" in capture_mode and non_official_numbers and "yamaha" in text_blob:
            score += 15
            reasons.append("La fachada capturada mezcla marca Yamaha con un telefono no oficial visible.")

        if asset.review_text and any(word in asset.review_text.lower() for word in ["nuevo numero", "whatsapp", "separa"]):
            score += 18
            reasons.append("El texto de la review contiene lenguaje tipico de desvio o preventa.")

        if asset.raw_payload.get("uploader", "").startswith("local-guide"):
            score += 7
            reasons.append("El cambio proviene de un tercero sin relacion aparente con el concesionario.")

        if asset.download_status == "captured":
            score += 5
            reasons.append("La evidencia visual fue preservada para validacion humana.")
        elif asset.download_status == "download_failed":
            reasons.append("No se pudo descargar la foto original y conviene reintentar la captura.")

        if asset.source_type == SourceType.REVIEW_PHOTO and not extracted_numbers and not asset.extracted_text:
            score = max(0, score - 10)
            reasons.append("La foto no aporta texto legible y necesita contexto adicional para escalarse.")

        return min(score, 100), reasons
