from __future__ import annotations

import argparse

from app.services.auth import AuthService
from app.store import repository


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Provision an explicitly approved network-wide, read-only WatchmanHub developer."
    )
    parser.add_argument("--email", required=True)
    parser.add_argument("--full-name", required=True)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Persist the user and membership. Without this flag the command is a dry run.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    email = args.email.strip().lower()
    full_name = args.full_name.strip()
    if not email or "@" not in email:
        raise SystemExit("Invalid --email")
    if not full_name:
        raise SystemExit("Invalid --full-name")
    if not args.apply:
        print(f"DRY RUN: provision developer_viewer for {full_name} <{email}>")
        return 0
    user, membership, created = AuthService(repository).provision_developer_viewer(
        email=email,
        full_name=full_name,
    )
    outcome = "created" if created else "already present"
    print(f"developer_viewer {outcome}: {user.full_name} <{user.email}> ({membership.id})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
