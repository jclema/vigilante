# Backend Standards

## Stack

- Python 3.11+
- FastAPI routes in `app/main.py`
- Domain models and enums in `app/models.py`
- In-memory and Firestore repository behavior in `app/store.py`
- Domain agents in `app/agents/`
- Application and integration services in `app/services/`

## Rules

- Validate external inputs before they enter domain workflows.
- Keep repository behavior consistent between memory and Firestore backends.
- Keep route handlers thin; put business behavior in services or agents.
- Use Pydantic models and explicit enums for structured domain data.
- Preserve production safety checks for insecure defaults.
- Add tests around authorization, organization scope, persistence, and external
  failure behavior when those areas change.

## Testing

- Unit and API-level tests live in `tests/`.
- Run `make test` for behavior changes and `make check` before final handoff.
- Use focused tests first, then broaden if a change touches shared behavior.
