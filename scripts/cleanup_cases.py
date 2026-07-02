from __future__ import annotations

import argparse

from app.models import CaseStatus, SourceType
from app.store import get_repository


def main() -> int:
    parser = argparse.ArgumentParser(description="Limpia casos historicos ruidosos de Vigilante.")
    parser.add_argument(
        "--keep",
        nargs="*",
        default=[],
        help="IDs de casos a preservar aunque cumplan criterio de limpieza.",
    )
    args = parser.parse_args()

    keep_ids = set(args.keep)
    repository = get_repository()
    updated = 0

    for case in repository.list_cases():
        if case.id in keep_ids:
            continue
        if case.source_type != SourceType.PLACE_CLONE:
            continue
        if case.status in {CaseStatus.CONFIRMED, CaseStatus.REPORTED}:
            continue
        case.status = CaseStatus.DISMISSED
        case.summary = f"{case.summary} Caso archivado como ruido historico tras afinacion del motor."
        repository.save_case(case)
        updated += 1

    print(f"Dismissed {updated} historical cases")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

