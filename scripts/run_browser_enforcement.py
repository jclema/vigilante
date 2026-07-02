from __future__ import annotations

import argparse
import json

from app.models import BrowserExecutionMode
from app.services.browser_ops import BrowserEnforcementService
from app.store import repository


def main() -> None:
    parser = argparse.ArgumentParser(description="Ejecuta browser enforcement para un caso.")
    parser.add_argument("case_id", help="ID del caso")
    parser.add_argument(
        "--mode",
        default=BrowserExecutionMode.SEMI_AUTO_SUBMIT.value,
        choices=[item.value for item in BrowserExecutionMode],
        help="Modo de ejecución del browser enforcement",
    )
    args = parser.parse_args()

    service = BrowserEnforcementService(repository)
    if args.mode == BrowserExecutionMode.MANUAL_PREPARE.value:
        run = service.prepare_case(args.case_id)
    elif args.mode == BrowserExecutionMode.AUTO_SUBMIT.value:
        run = service.run_auto(args.case_id)
    else:
        run = service.submit_case(args.case_id, execution_mode=BrowserExecutionMode.SEMI_AUTO_SUBMIT)
    print(json.dumps(run.model_dump(mode="json"), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
