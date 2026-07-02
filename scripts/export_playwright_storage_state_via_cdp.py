from __future__ import annotations

import argparse
import json
from pathlib import Path


def try_import_playwright():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:  # pragma: no cover - runtime dependency optional
        raise SystemExit(
            "Falta Playwright. Instala con `python3 -m pip install playwright` y luego `playwright install chromium`."
        ) from exc
    return sync_playwright


def _pick_page(browser, target_url: str):
    normalized_target = target_url.rstrip("/")
    for context in browser.contexts:
        for page in context.pages:
            current_url = page.url.rstrip("/")
            if current_url == normalized_target or current_url.startswith(f"{normalized_target}?"):
                return context, page
    if not browser.contexts:
        raise SystemExit("Chrome no expuso ningun contexto por CDP.")
    context = browser.contexts[0]
    page = context.new_page()
    return context, page


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Exporta una storage_state conectandose a un Chrome real ya abierto por CDP."
    )
    parser.add_argument(
        "--cdp-url",
        default="http://127.0.0.1:9222",
        help="Endpoint HTTP del Chrome abierto con --remote-debugging-port.",
    )
    parser.add_argument(
        "--output",
        default="/tmp/vigilante-browser-capture-storage-state.json",
        help="Ruta donde se guardara la storage_state.",
    )
    parser.add_argument(
        "--maps-url",
        default="https://www.google.com/maps?hl=es-CO",
        help="URL a validar dentro del Chrome ya autenticado.",
    )
    args = parser.parse_args()

    output_path = Path(args.output).expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    sync_playwright = try_import_playwright()
    with sync_playwright() as playwright:
        browser = playwright.chromium.connect_over_cdp(args.cdp_url)
        context, page = _pick_page(browser, args.maps_url)
        if not page.url or page.url == "about:blank":
            page.goto(args.maps_url, wait_until="domcontentloaded", timeout=45000)

        print()
        print("Playwright se conecto a tu Chrome real via CDP.")
        print("1. En esa ventana confirma que Google Maps sigue autenticado.")
        print("2. Si hace falta, navega manualmente dentro de Maps antes de exportar.")
        print("3. Cuando lo veas bien, vuelve a esta terminal y presiona ENTER.")
        input()

        storage_state = context.storage_state()
        output_path.write_text(json.dumps(storage_state, indent=2), encoding="utf-8")
        browser.close()

    print(f"Storage state exportada en: {output_path}")


if __name__ == "__main__":
    main()
