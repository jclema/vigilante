from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
from pathlib import Path


def try_import_playwright():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:  # pragma: no cover - runtime dependency optional
        raise SystemExit(
            "Falta Playwright. Instala con `python3 -m pip install playwright` y luego `playwright install chromium`."
        ) from exc
    return sync_playwright


def _default_chrome_profile_dir() -> Path:
    if sys.platform == "darwin":
        return Path.home() / "Library/Application Support/Google/Chrome/Default"
    if sys.platform.startswith("linux"):
        return Path.home() / ".config/google-chrome/Default"
    if sys.platform == "win32":
        return Path.home() / "AppData/Local/Google/Chrome/User Data/Default"
    raise SystemExit("No se pudo resolver la ruta por defecto del perfil de Chrome en este sistema.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Exporta una storage_state de Playwright reutilizando una sesión ya iniciada en Chrome."
    )
    parser.add_argument(
        "--chrome-profile",
        default=str(_default_chrome_profile_dir()),
        help="Ruta del perfil local de Chrome que ya tiene sesión iniciada.",
    )
    parser.add_argument(
        "--output",
        default="/tmp/vigilante-browser-capture-storage-state.json",
        help="Ruta donde se guardará la storage_state.",
    )
    parser.add_argument(
        "--maps-url",
        default="https://www.google.com/maps?hl=es-CO",
        help="URL a abrir para validar que Maps sigue autenticado.",
    )
    args = parser.parse_args()

    source_profile = Path(args.chrome_profile).expanduser().resolve()
    if not source_profile.exists():
        raise SystemExit(f"No existe el perfil de Chrome: {source_profile}")

    output_path = Path(args.output).expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    temp_root = Path(tempfile.mkdtemp(prefix="vigilante-chrome-profile-"))
    temp_profile = temp_root / "profile"
    shutil.copytree(source_profile, temp_profile, dirs_exist_ok=True)

    sync_playwright = try_import_playwright()
    with sync_playwright() as playwright:
        context = playwright.chromium.launch_persistent_context(
            user_data_dir=str(temp_profile),
            headless=False,
            channel="chrome",
            locale="es-CO",
            timezone_id="America/Bogota",
            viewport={"width": 1440, "height": 1100},
        )
        page = context.new_page()
        page.goto(args.maps_url, wait_until="domcontentloaded", timeout=45000)
        print()
        print("Se abrió una sesión derivada de tu perfil local de Chrome.")
        print("1. Verifica que Google Maps siga autenticado.")
        print("2. Si hace falta, completa cualquier validación adicional.")
        print("3. Cuando lo veas bien, vuelve a esta terminal y presiona ENTER para exportar la storage_state.")
        input()
        storage_state = context.storage_state()
        output_path.write_text(json.dumps(storage_state, indent=2), encoding="utf-8")
        context.close()

    print(f"Storage state exportada en: {output_path}")


if __name__ == "__main__":
    main()
