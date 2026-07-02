from __future__ import annotations

import argparse
import json

from app.config import settings
from app.services.geocoding import GeocodingService
from app.services.whitelist import WhitelistImporter
from app.store import get_repository


def main() -> int:
    parser = argparse.ArgumentParser(description="Importa whitelist CSV a Vigilante.")
    parser.add_argument("csv_path", help="Ruta al CSV de whitelist")
    parser.add_argument("--dump-json", action="store_true", help="Imprime el resultado importado")
    args = parser.parse_args()

    repository = get_repository()
    importer = WhitelistImporter(GeocodingService(settings.google_maps_api_key))
    dealers = importer.import_csv(args.csv_path)
    repository.import_whitelist(dealers)

    if args.dump_json:
        print(json.dumps([dealer.model_dump(mode="json") for dealer in dealers], ensure_ascii=False, indent=2))
    else:
        print(f"Imported {len(dealers)} dealers")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

