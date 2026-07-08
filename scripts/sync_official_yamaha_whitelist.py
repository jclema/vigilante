from __future__ import annotations

import argparse
import json

from app.config import settings
from app.models import DealerProfile, MonitoringMode
from app.services.whitelist import (
    fetch_official_yamaha_distributors,
    merge_official_yamaha_dealers,
    official_yamaha_dealers_from_distributors,
)
from app.store import get_repository


def main() -> int:
    parser = argparse.ArgumentParser(description="Sincroniza whitelist desde la fuente oficial de Incolmotos Yamaha.")
    parser.add_argument("--city", default="Medellín", help="Ciudad oficial a importar")
    parser.add_argument("--department-id", default="5", help="ID de departamento en la fuente oficial")
    parser.add_argument("--dry-run", action="store_true", help="No escribe en el repositorio")
    parser.add_argument("--dump-json", action="store_true", help="Imprime dealers resultantes")
    args = parser.parse_args()

    rows = fetch_official_yamaha_distributors()
    official_dealers = official_yamaha_dealers_from_distributors(
        rows,
        department_id=args.department_id,
        city=args.city,
        organization_id="org-yamaha-network",
    )

    repository = get_repository()
    existing_dealers = list(repository.dealers.values())
    existing_profiles = list(repository.profiles.values())
    profiled_dealer_ids = {profile.dealer_id for profile in existing_profiles}
    merged_dealers = merge_official_yamaha_dealers(existing_dealers, official_dealers)
    official_or_updated_ids = {dealer.id for dealer in official_dealers}
    existing_ids = {dealer.id for dealer in existing_dealers}
    existing_by_id = {dealer.id: dealer for dealer in existing_dealers}
    changed_dealers = [
        dealer
        for dealer in merged_dealers
        if dealer.id in official_or_updated_ids or dealer.model_dump() != existing_by_id.get(dealer.id, dealer).model_dump()
    ]
    new_profiles = [
        DealerProfile(
            id=f"profile-{dealer.id.removeprefix('dealer-')}",
            dealer_id=dealer.id,
            organization_id=dealer.organization_id,
            name=dealer.name,
            monitoring_mode=MonitoringMode.PUBLIC_SCAN,
        )
        for dealer in changed_dealers
        if dealer.id not in profiled_dealer_ids
    ]

    if args.dump_json:
        print(
            json.dumps(
                {
                    "dealers": [dealer.model_dump(mode="json") for dealer in changed_dealers],
                    "profiles": [profile.model_dump(mode="json") for profile in new_profiles],
                },
                ensure_ascii=False,
                indent=2,
            )
        )

    if args.dry_run:
        print(
            f"Dry run: {len(official_dealers)} punto(s) oficiales, "
            f"{len([dealer for dealer in changed_dealers if dealer.id in existing_ids])} actualizado(s), "
            f"{len([dealer for dealer in changed_dealers if dealer.id not in existing_ids])} nuevo(s), "
            f"{len(new_profiles)} perfil(es) nuevo(s)."
        )
        return 0

    repository.import_whitelist(changed_dealers)
    if new_profiles:
        repository.import_profiles(new_profiles)
    print(
        f"Sincronizados {len(changed_dealers)} dealer(s) y {len(new_profiles)} perfil(es) desde fuente oficial "
        f"para {args.city} con STORAGE_BACKEND={settings.storage_backend}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
