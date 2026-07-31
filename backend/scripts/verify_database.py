"""Run the O-AI startup database compatibility check without starting the API."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main() -> int:
    script_backend = Path(__file__).resolve().parents[1]
    if str(script_backend) not in sys.path:
        sys.path.insert(0, str(script_backend))
    from app.db.verification import DatabaseVerificationError, verify_database

    parser = argparse.ArgumentParser(description="Verify an Alembic-managed O-AI SQLite database without modifying it.")
    parser.add_argument("--database", type=Path, required=True, help="Path to the SQLite database to verify.")
    arguments = parser.parse_args()
    database_url = f"sqlite:///{arguments.database.resolve().as_posix()}"
    try:
        result = verify_database(database_url)
    except DatabaseVerificationError as error:
        print(f"Database verification failed: {error}", file=sys.stderr)
        return 1
    print(f"Database is compatible at Alembic revision {result.revision}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
