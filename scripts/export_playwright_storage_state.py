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


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Exporta una storage_state de Playwright después de iniciar sesión manualmente en Google Maps."
    )
    parser.add_argument(
        "--output",
        default="/tmp/vigilante-browser-capture-storage-state.json",
        help="Ruta donde se guardará la storage_state.",
    )
    parser.add_argument(
        "--url",
        default="https://www.google.com/maps?hl=es-CO",
        help="URL inicial para abrir antes de iniciar sesión.",
    )
    args = parser.parse_args()

    output_path = Path(args.output).expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    sync_playwright = try_import_playwright()
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=False)
        context = browser.new_context(
            locale="es-CO",
            timezone_id="America/Bogota",
            viewport={"width": 1440, "height": 1100},
        )
        page = context.new_page()
        page.goto(args.url, wait_until="domcontentloaded", timeout=45000)
        print()
        print("1. Inicia sesión manualmente en Google si hace falta.")
        print("2. Abre Google Maps y valida que la sesión quedó activa.")
        print("3. Cuando termines, vuelve a esta terminal y presiona ENTER para exportar la storage_state.")
        input()
        storage_state = context.storage_state()
        output_path.write_text(json.dumps(storage_state, indent=2), encoding="utf-8")
        context.close()
        browser.close()

    print(f"Storage state exportada en: {output_path}")


if __name__ == "__main__":
    main()
