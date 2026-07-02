from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import random
from pathlib import Path

from app.agents.forensic import ForensicAgent
from app.agents.scout import ScoutAgent
from app.config import settings
from app.services.evidence_media import EvidenceMediaService
from app.services.experimental_capture import ExperimentalCaptureIngestService, ExperimentalCaptureRecord
from app.services.gbp_media import ImageTextExtractor
from app.store import repository


def load_targets(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _filter_targets(targets: list[dict[str, str]]) -> list[dict[str, str]]:
    raw_filter = os.getenv("TARGET_PROFILE_IDS", "").strip()
    if not raw_filter:
        return targets
    allowed = {item.strip() for item in raw_filter.split(",") if item.strip()}
    if not allowed:
        return targets
    return [target for target in targets if (target.get("profile_id") or "").strip() in allowed]


def try_import_playwright():
    try:
        from playwright.sync_api import TimeoutError, sync_playwright
    except ImportError as exc:  # pragma: no cover - runtime dependency optional
        raise SystemExit(
            "Falta Playwright. Instala con `python3 -m pip install playwright` y luego `playwright install chromium`."
        ) from exc
    return sync_playwright, TimeoutError


PHOTO_OVERLAY_PATTERNS = [
    re.compile(r"^(see|ver)\s+photos?$", re.IGNORECASE),
    re.compile(r"^(see|ver)\s+all\s+photos?$", re.IGNORECASE),
]
PHOTOS_SECTION_PATTERNS = [
    re.compile(r"^(photos?|fotos?)(\s*&\s*videos|\s+y\s+videos)?$", re.IGNORECASE),
    re.compile(r"^(photos|fotos)(\s*&\s*videos|\s+y\s+videos)?$", re.IGNORECASE),
    re.compile(r"^(photos\s*&\s*videos|fotos\s+y\s+videos)$", re.IGNORECASE),
]
ALL_FILTER_PATTERNS = [
    re.compile(r"^(all|todos?)$", re.IGNORECASE),
    re.compile(r"^(all photos|todas las fotos)$", re.IGNORECASE),
    re.compile(r"^(all posts|todas)$", re.IGNORECASE),
]

STEALTH_SCRIPT = """
Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
Object.defineProperty(navigator, 'platform', {get: () => 'Linux x86_64'});
Object.defineProperty(navigator, 'languages', {get: () => ['es-CO', 'es', 'en-US', 'en']});
Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
window.chrome = window.chrome || { runtime: {} };
"""

MEDELLIN_GEO = {"latitude": 6.2442, "longitude": -75.5812}


def _load_storage_state():
    raw_json = os.getenv("PLAYWRIGHT_STORAGE_STATE_JSON", "").strip()
    if raw_json:
        try:
            return json.loads(raw_json)
        except json.JSONDecodeError:
            return None
    state_path = os.getenv("PLAYWRIGHT_STORAGE_STATE_PATH", "").strip()
    if state_path and Path(state_path).exists():
        return state_path
    return None


def _record_step(trace: list[dict[str, str]], step: str, status: str, detail: str) -> None:
    trace.append({"step": step, "status": status, "detail": detail})


def _normalize_text(value: str) -> str:
    lowered = value.lower()
    normalized = re.sub(r"[^a-z0-9]+", " ", lowered)
    return re.sub(r"\s+", " ", normalized).strip()


def _extract_place_id(url: str) -> str | None:
    patterns = [
        r"place_id:([A-Za-z0-9_\-]+)",
        r"query_place_id=([A-Za-z0-9_\-]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def _candidate_profile_urls(profile_url: str) -> list[str]:
    candidates = [profile_url]
    place_id = _extract_place_id(profile_url)
    if place_id:
        candidates.extend(
            [
                f"https://www.google.com/maps/place/?q=place_id:{place_id}&hl=es-CO",
                f"https://www.google.com/maps/search/?api=1&query=Google&query_place_id={place_id}",
            ]
        )
    seen: set[str] = set()
    deduped: list[str] = []
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        deduped.append(candidate)
    return deduped


def _is_generic_maps_landing(url: str) -> bool:
    lowered = (url or "").lower()
    return "google.com/maps/@" in lowered and "/maps/place/" not in lowered and "query_place_id=" not in lowered


def _page_text_snapshot(page) -> str:
    try:
        return page.locator("body").inner_text(timeout=4000) or ""
    except Exception:
        return ""


def _landing_matches_expected(page_text: str, profile_name: str) -> bool:
    normalized_name = _normalize_text(profile_name)
    normalized_body = _normalize_text(page_text)
    if not normalized_name or not normalized_body:
        return False
    if normalized_name in normalized_body:
        return True
    name_tokens = [token for token in normalized_name.split() if len(token) >= 4]
    if not name_tokens:
        return False
    matches = sum(1 for token in name_tokens if token in normalized_body)
    return matches >= max(2, min(3, len(name_tokens)))


def _validate_profile_landing(page, profile_name: str) -> tuple[bool, str]:
    final_url = page.url or ""
    if _looks_blocked(page):
        return False, "captcha_or_google_block"
    if _is_generic_maps_landing(final_url):
        return False, "generic_maps_redirect"
    page_text = _page_text_snapshot(page)
    if _landing_matches_expected(page_text, profile_name):
        return True, "profile_name_visible"
    return False, "expected_profile_name_not_visible"


def _navigate_to_expected_profile(page, profile_url: str, profile_name: str, trace: list[dict[str, str]], timeout_error) -> tuple[bool, str]:
    last_reason = "profile_not_loaded"
    for attempt_index, candidate_url in enumerate(_candidate_profile_urls(profile_url), start=1):
        try:
            page.goto(candidate_url, wait_until="domcontentloaded", timeout=45000)
        except timeout_error:
            last_reason = "profile_load_timeout"
            _record_step(trace, "profile_loaded", "failed", f"Timeout cargando intento {attempt_index}.")
            continue
        _dismiss_overlays(page)
        _human_pause(page, 1400, 2600)
        _humanize_page(page)
        landed_ok, landing_reason = _validate_profile_landing(page, profile_name)
        if landed_ok:
            _record_step(trace, "profile_loaded", "ok", f"Perfil confirmado en intento {attempt_index} ({landing_reason}).")
            return True, landing_reason
        last_reason = landing_reason
        _record_step(trace, "profile_loaded", "retry", f"Intento {attempt_index} no confirmo perfil ({landing_reason}).")
    return False, last_reason


class StagehandFallbackNavigator:
    def __init__(self, enabled: bool) -> None:
        self.enabled = enabled

    def open_photo_gallery(self, page, trace: list[dict[str, str]]) -> tuple[bool, str]:
        if not self.enabled:
            _record_step(trace, "stagehand_gallery_fallback", "skipped", "Fallback Stagehand deshabilitado.")
            return False, "stagehand-disabled"
        if _click_named(page, patterns=PHOTO_OVERLAY_PATTERNS, roles=("button", "link", "img")):
            _record_step(trace, "stagehand_gallery_fallback", "ok", "Fallback semántico abrió la galería.")
            return True, "stagehand-semantic-open"
        if _click_named(page, patterns=PHOTOS_SECTION_PATTERNS, roles=("tab", "link", "button")):
            _record_step(trace, "stagehand_gallery_fallback", "ok", "Fallback semántico abrió la sección de fotos.")
            return True, "stagehand-semantic-photos-tab"
        if _click_text_candidates(page, ["Ver fotos", "See photos", "Fotos", "Photos"], timeout=3000):
            _record_step(trace, "stagehand_gallery_fallback", "ok", "Fallback textual abrió la galería.")
            return True, "stagehand-text-open"
        _record_step(trace, "stagehand_gallery_fallback", "failed", "Fallback semántico no encontró la galería.")
        return False, "stagehand-gallery-not-found"

    def enter_all_media(self, page, trace: list[dict[str, str]]) -> tuple[bool, str]:
        if not self.enabled:
            _record_step(trace, "stagehand_all_media_fallback", "skipped", "Fallback Stagehand deshabilitado.")
            return False, "stagehand-disabled"
        if _click_text_candidates(page, ["Todas las fotos", "All photos", "Todos", "All"], timeout=3000):
            _record_step(trace, "stagehand_all_media_fallback", "ok", "Fallback semántico abrió el filtro Todas.")
            return True, "stagehand-text-all-filter"
        _record_step(trace, "stagehand_all_media_fallback", "failed", "Fallback semántico no encontró el filtro Todas.")
        return False, "stagehand-all-filter-missing"


def _looks_blocked(page, record: ExperimentalCaptureRecord | None = None) -> bool:
    final_url = ""
    gallery_hint = ""
    if record:
        final_url = record.final_url or ""
        gallery_hint = record.gallery_hint or ""
    else:
        try:
            final_url = page.url or ""
        except Exception:
            final_url = ""
        gallery_hint = _gallery_hint(page)
    lowered_url = final_url.lower()
    return "google.com/sorry" in lowered_url or gallery_hint == "captcha"


def _dismiss_overlays(page) -> None:
    for label in ["Aceptar todo", "Accept all", "No thanks", "Ahora no", "Not now"]:
        try:
            page.get_by_role("button", name=label).click(timeout=1500)
            page.wait_for_timeout(500)
        except Exception:
            continue


def _warmup_google_surface(page) -> None:
    warmup_urls = [
        "https://www.google.com/?hl=es-CO",
        "https://www.google.com/maps?hl=es-CO",
    ]
    for url in warmup_urls:
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=20000)
            _dismiss_overlays(page)
            _human_pause(page, 900, 1600)
        except Exception:
            continue
    _humanize_page(page)


def _click_named(page, *, patterns: list[re.Pattern[str]], roles: tuple[str, ...], timeout: int = 2500) -> bool:
    for role in roles:
        try:
            locator = page.get_by_role(role)
            count = min(locator.count(), 25)
        except Exception:
            count = 0
        for index in range(count):
            try:
                candidate = locator.nth(index)
                name = (candidate.get_attribute("aria-label") or candidate.inner_text(timeout=timeout) or "").strip()
                if any(pattern.search(name) for pattern in patterns):
                    candidate.click(timeout=timeout)
                    page.wait_for_timeout(1200)
                    return True
            except Exception:
                continue
    return False


def _click_text_candidates(page, labels: list[str], timeout: int = 2500) -> bool:
    for label in labels:
        for exact in (True, False):
            try:
                locator = page.get_by_text(label, exact=exact).first
                if locator.count() == 0:
                    continue
                locator.click(timeout=timeout)
                _human_pause(page, 900, 1500)
                return True
            except Exception:
                continue
    return False


def _human_pause(page, low_ms: int = 600, high_ms: int = 1500) -> None:
    page.wait_for_timeout(random.randint(low_ms, high_ms))


def _humanize_page(page) -> None:
    try:
        page.mouse.move(180, 240, steps=24)
        _human_pause(page, 400, 900)
        page.mouse.wheel(0, random.randint(200, 500))
        _human_pause(page, 400, 900)
        page.mouse.wheel(0, -random.randint(120, 260))
        _human_pause(page, 300, 700)
    except Exception:
        return


def _extra_humanize_page(page) -> None:
    try:
        page.mouse.move(random.randint(90, 220), random.randint(140, 280), steps=random.randint(18, 36))
        _human_pause(page, 700, 1600)
        page.mouse.wheel(0, random.randint(280, 620))
        _human_pause(page, 700, 1600)
        page.mouse.move(random.randint(240, 420), random.randint(260, 520), steps=random.randint(20, 40))
        _human_pause(page, 600, 1200)
        page.mouse.wheel(0, -random.randint(120, 240))
        _human_pause(page, 600, 1400)
    except Exception:
        return


def _try_hover_photo_overlay(page) -> bool:
    overlay_selectors = [
        '[aria-label*="See photos"]',
        '[aria-label*="Ver fotos"]',
        '[aria-label*="See all photos"]',
        '[aria-label*="Ver todas las fotos"]',
    ]
    hero_selectors = [
        'button[jsaction*="pane.heroHeaderImage.click"]',
        'button[jsaction*="pane.photoHeader"]',
        'img[src*="googleusercontent"]',
    ]
    for hero_selector in hero_selectors:
        try:
            hero = page.locator(hero_selector).first
            if hero.count() == 0:
                continue
            hero.hover(timeout=2000)
            _human_pause(page, 500, 1100)
            for overlay_selector in overlay_selectors:
                overlay = page.locator(overlay_selector).first
                if overlay.count() == 0:
                    continue
                overlay.click(timeout=2500)
                _human_pause(page, 1000, 1800)
                return True
        except Exception:
            continue
    return False


def _try_photo_section_thumbnail(page) -> bool:
    for pattern in PHOTOS_SECTION_PATTERNS:
        try:
            heading = page.get_by_text(pattern).first
            if heading.count() == 0:
                continue
            try:
                heading.scroll_into_view_if_needed(timeout=2500)
                _human_pause(page, 500, 900)
            except Exception:
                pass

            candidates = [
                heading.locator(
                    "xpath=ancestor::*[self::div or self::section][1]//*[self::button or self::a][.//img]"
                ),
                heading.locator("xpath=following::button[.//img][position()<=4]"),
                heading.locator("xpath=following::a[.//img][position()<=4]"),
                heading.locator("xpath=following::img[position()<=4]"),
            ]
            for candidate in candidates:
                count = min(candidate.count(), 4)
                for index in range(count):
                    target = candidate.nth(index)
                    try:
                        target.scroll_into_view_if_needed(timeout=2500)
                    except Exception:
                        pass
                    try:
                        target.click(timeout=2500)
                    except Exception:
                        try:
                            target.hover(timeout=1200)
                            _human_pause(page, 300, 700)
                            page.mouse.down()
                            page.mouse.up()
                        except Exception:
                            continue
                    _human_pause(page, 1000, 1800)
                    return True
        except Exception:
            continue

    section_selectors = [
        '[aria-label*="Photos"] button',
        '[aria-label*="Fotos"] button',
        '[data-section-id="apf"] button',
    ]
    for selector in section_selectors:
        try:
            locator = page.locator(selector).first
            if locator.count() == 0:
                continue
            locator.scroll_into_view_if_needed(timeout=2500)
            _human_pause(page, 400, 800)
            locator.click(timeout=2500)
            _human_pause(page, 1000, 1800)
            return True
        except Exception:
            continue
    return False


def _open_photo_gallery(page, trace: list[dict[str, str]], fallback: StagehandFallbackNavigator) -> tuple[bool, str, bool, str | None]:
    if _try_hover_photo_overlay(page):
        _record_step(trace, "gallery_opened", "ok", "Galería abierta con hover overlay.")
        return True, "hover-see-photos-overlay", False, None
    if _try_photo_section_thumbnail(page):
        _record_step(trace, "gallery_opened", "ok", "Galería abierta desde thumbnail de la sección.")
        return True, "photos-section-thumbnail", False, None
    opened, method = fallback.open_photo_gallery(page, trace)
    if opened:
        return True, method, True, None
    return False, "profile-only", False, "gallery_not_found"


def _enter_all_media(page, trace: list[dict[str, str]], fallback: StagehandFallbackNavigator) -> tuple[bool, str, bool]:
    if _click_named(page, patterns=PHOTOS_SECTION_PATTERNS, roles=("tab", "link", "button")):
        page.wait_for_timeout(1500)
    if _click_named(page, patterns=ALL_FILTER_PATTERNS, roles=("tab", "link", "button")):
        _record_step(trace, "all_media_selected", "ok", "Filtro Todas abierto por selector determinístico.")
        return True, "all-filter", False
    selector_candidates = [
        '[role="tab"][aria-label*="All"]',
        '[role="tab"][aria-label*="Todos"]',
        '[role="button"][aria-label*="All"]',
        '[role="button"][aria-label*="Todos"]',
        'button[aria-label*="All photos"]',
        'button[aria-label*="Todas las fotos"]',
    ]
    for selector in selector_candidates:
        try:
            locator = page.locator(selector).first
            if locator.count() == 0:
                continue
            locator.click(timeout=3000)
            _human_pause(page, 900, 1500)
            _record_step(trace, "all_media_selected", "ok", "Filtro Todas abierto por selector alternativo.")
            return True, "all-filter-selector", False
        except Exception:
            continue
    opened, method = fallback.enter_all_media(page, trace)
    if opened:
        return True, method, True
    _record_step(trace, "all_media_selected", "failed", "No se encontró el filtro Todas.")
    return False, "gallery-default", False


def _gallery_hint(page) -> str:
    text = page.locator("body").inner_text(timeout=3000)
    lowered = text.lower()
    if "no soy un robot" in lowered or "i'm not a robot" in lowered or "recaptcha" in lowered:
        return "captcha"
    if "photos & videos" in lowered or "fotos y videos" in lowered:
        return "photos-and-videos"
    if re.search(r"\ball\b", lowered) or re.search(r"\btodos?\b", lowered):
        return "all-media-visible"
    return "unknown"


def _capture_with_page(page, target: dict[str, str], output_dir: Path, timeout_error, capture_mode: str) -> ExperimentalCaptureRecord | None:
    profile_id = target["profile_id"]
    profile_url = target["public_profile_url"]
    profile_name = target.get("profile_name") or profile_id
    safe_name = f"{profile_id.replace('/', '-')}-{capture_mode}"
    screenshot_path = output_dir / f"{safe_name}.png"
    step_trace: list[dict[str, str]] = []
    fallback = StagehandFallbackNavigator(enabled=settings.enable_stagehand_fallback)
    fallback_used = False
    capture_failure_reason = None

    profile_landed, landing_reason = _navigate_to_expected_profile(page, profile_url, profile_name, step_trace, timeout_error)
    if not profile_landed:
        capture_failure_reason = "wrong_place_landing"
        _record_step(step_trace, "target_asset_located", "failed", f"No se confirmo la ficha esperada ({landing_reason}).")
        try:
            page.wait_for_timeout(1500)
            page.screenshot(path=str(screenshot_path), full_page=True)
            _record_step(step_trace, "capture_completed", "ok", "Screenshot de diagnostico capturado.")
        except Exception:
            _record_step(step_trace, "capture_completed", "failed", "No fue posible capturar screenshot de diagnostico.")
            return None
        fingerprint = hashlib.sha256(f"{profile_id}|{page.url}|{capture_mode}|wrong-place".encode("utf-8")).hexdigest()[:24]
        return ExperimentalCaptureRecord(
            profile_id=profile_id,
            profile_name=profile_name,
            screenshot_path=str(screenshot_path),
            profile_url=profile_url,
            review_text=target.get("review_text") or None,
            extracted_text=target.get("extracted_text") or None,
            captured_from=f"experimental_browser_capture_{capture_mode}",
            final_url=page.url,
            gallery_opened=False,
            gallery_open_method="profile-only",
            all_media_selected=False,
            media_filter="profile-only",
            gallery_hint=_gallery_hint(page),
            browser_surface=capture_mode,
            step_trace=step_trace,
            fallback_used=False,
            asset_fingerprint=fingerprint,
            navigation_confidence="low",
            capture_failure_reason=capture_failure_reason,
        )

    gallery_opened, open_method, gallery_fallback_used, gallery_failure_reason = _open_photo_gallery(page, step_trace, fallback)
    fallback_used = fallback_used or gallery_fallback_used
    all_media_selected = False
    media_filter = "profile-only"
    if gallery_opened:
        all_media_selected, media_filter, all_media_fallback_used = _enter_all_media(page, step_trace, fallback)
        fallback_used = fallback_used or all_media_fallback_used
    else:
        capture_failure_reason = gallery_failure_reason
    gallery_hint = _gallery_hint(page)
    if gallery_hint == "captcha":
        capture_failure_reason = "captcha_detected"
        _record_step(step_trace, "captcha_detected", "failed", "Google mostró una superficie tipo captcha.")
    elif gallery_opened and all_media_selected:
        _record_step(step_trace, "target_asset_located", "ok", "La navegación llegó a la galería completa del perfil.")
    elif gallery_opened:
        _record_step(step_trace, "target_asset_located", "partial", "La galería abrió, pero no se confirmó el filtro Todas.")
    else:
        _record_step(step_trace, "target_asset_located", "failed", "No fue posible abrir la galería del perfil.")

    try:
        page.wait_for_timeout(2500)
        page.screenshot(path=str(screenshot_path), full_page=True)
        _record_step(step_trace, "capture_completed", "ok", "Screenshot completo capturado.")
    except Exception:
        _record_step(step_trace, "capture_completed", "failed", "No fue posible capturar el screenshot final.")
        return None

    fingerprint = hashlib.sha256(f"{profile_id}|{page.url}|{capture_mode}|{open_method}|{media_filter}".encode("utf-8")).hexdigest()[:24]
    navigation_confidence = "high" if gallery_opened and all_media_selected and not fallback_used else (
        "medium" if gallery_opened else "low"
    )

    return ExperimentalCaptureRecord(
        profile_id=profile_id,
        profile_name=profile_name,
        screenshot_path=str(screenshot_path),
        profile_url=profile_url,
        review_text=target.get("review_text") or None,
        extracted_text=target.get("extracted_text") or None,
        captured_from=f"experimental_browser_capture_{capture_mode}",
        final_url=page.url,
        gallery_opened=gallery_opened,
        gallery_open_method=open_method,
        all_media_selected=all_media_selected,
        media_filter=media_filter,
        gallery_hint=gallery_hint,
        browser_surface=capture_mode,
        step_trace=step_trace,
        fallback_used=fallback_used,
        asset_fingerprint=fingerprint,
        navigation_confidence=navigation_confidence,
        capture_failure_reason=capture_failure_reason,
    )


def _capture_attempt(context, target: dict[str, str], output_dir: Path, timeout_error, capture_mode: str, humanize_retry: bool = False) -> ExperimentalCaptureRecord | None:
    page = context.new_page()
    try:
        try:
            _warmup_google_surface(page)
            if humanize_retry:
                _extra_humanize_page(page)
        except Exception:
            pass
        record = _capture_with_page(page, target, output_dir, timeout_error, capture_mode)
        return record
    finally:
        page.close()


def capture_target(browser, playwright_device, target: dict[str, str], output_dir: Path, timeout_error) -> ExperimentalCaptureRecord | None:
    attempts: list[tuple[str, bool]] = [
        ("desktop", False),
        ("mobile", False),
        ("desktop", True),
    ]
    best_record: ExperimentalCaptureRecord | None = None

    for capture_mode, humanize_retry in attempts:
        if capture_mode == "mobile":
            context = _build_mobile_context(browser, playwright_device)
        else:
            context = _build_desktop_context(browser)
        try:
            context.add_init_script(STEALTH_SCRIPT)
            record = _capture_attempt(
                context,
                target,
                output_dir,
                timeout_error,
                capture_mode,
                humanize_retry=humanize_retry,
            )
        finally:
            context.close()

        if not record:
            continue
        best_record = record
        if not _looks_blocked(None, record) and record.gallery_opened:
            return record
        if not _looks_blocked(None, record):
            return record

    return best_record


def _build_mobile_context(browser, device):
    storage_state = _load_storage_state()
    if device:
        mobile_device = dict(device)
        mobile_device["user_agent"] = (
            "Mozilla/5.0 (Linux; Android 14; Pixel 7) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/123.0.0.0 Mobile Safari/537.36"
        )
        return browser.new_context(
            **mobile_device,
            locale="es-CO",
            timezone_id="America/Bogota",
            geolocation=MEDELLIN_GEO,
            permissions=["geolocation"],
            storage_state=storage_state,
            extra_http_headers={"Accept-Language": "es-CO,es;q=0.9,en-US;q=0.8,en;q=0.7"},
        )
    return browser.new_context(
        viewport={"width": 412, "height": 915},
        is_mobile=True,
        has_touch=True,
        locale="es-CO",
        timezone_id="America/Bogota",
        geolocation=MEDELLIN_GEO,
        permissions=["geolocation"],
        storage_state=storage_state,
        user_agent=(
            "Mozilla/5.0 (Linux; Android 14; Pixel 7) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/123.0.0.0 Mobile Safari/537.36"
        ),
        extra_http_headers={"Accept-Language": "es-CO,es;q=0.9,en-US;q=0.8,en;q=0.7"},
    )


def _build_desktop_context(browser):
    storage_state = _load_storage_state()
    return browser.new_context(
        viewport={"width": 1440, "height": 2200},
        locale="es-CO",
        timezone_id="America/Bogota",
        geolocation=MEDELLIN_GEO,
        permissions=["geolocation"],
        storage_state=storage_state,
        color_scheme="light",
        user_agent=(
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
        ),
        extra_http_headers={"Accept-Language": "es-CO,es;q=0.9,en-US;q=0.8,en;q=0.7"},
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Captura experimental de fotos públicas de reviews en perfiles oficiales.")
    parser.add_argument("targets_csv", help="CSV con profile_id, profile_name y public_profile_url")
    parser.add_argument("--output-dir", default="/tmp/vigilante-browser-captures", help="Directorio para screenshots")
    parser.add_argument("--headed", action="store_true", help="Ejecutar con navegador visible")
    args = parser.parse_args()

    targets = _filter_targets(load_targets(Path(args.targets_csv)))
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    sync_playwright, timeout_error = try_import_playwright()
    records: list[ExperimentalCaptureRecord] = []
    with sync_playwright() as playwright:
        device = playwright.devices.get("Pixel 7")
        browser = playwright.chromium.launch(
            headless=not args.headed,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--disable-features=IsolateOrigins,site-per-process",
                "--disable-infobars",
                "--lang=es-CO",
            ],
        )
        for target in targets:
            record = capture_target(browser, device, target, output_dir, timeout_error)
            if record:
                print(
                    {
                        "profile_id": record.profile_id,
                        "captured_from": record.captured_from,
                        "browser_surface": record.browser_surface,
                        "gallery_opened": record.gallery_opened,
                        "gallery_open_method": record.gallery_open_method,
                        "all_media_selected": record.all_media_selected,
                        "media_filter": record.media_filter,
                        "gallery_hint": record.gallery_hint,
                        "fallback_used": record.fallback_used,
                        "asset_fingerprint": record.asset_fingerprint,
                        "navigation_confidence": record.navigation_confidence,
                        "capture_failure_reason": record.capture_failure_reason,
                        "final_url": record.final_url,
                    }
                )
                records.append(record)
        browser.close()

    service = ExperimentalCaptureIngestService(
        repository=repository,
        scout_agent=ScoutAgent(repository, ForensicAgent()),
        evidence_service=EvidenceMediaService(),
        text_extractor=ImageTextExtractor(),
    )
    result = service.run_batch(records)
    print(result)


if __name__ == "__main__":
    main()
