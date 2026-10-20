from __future__ import annotations

import getpass
import sqlite3

from app.database import initialize_database
from app.services.team_auth import provision_team_user


def main() -> None:
    initialize_database()
    email = input("Approved staff work email: ").strip()
    password = getpass.getpass("Initial password (12+ characters): ")
    confirmation = getpass.getpass("Confirm password: ")
    if password != confirmation:
        raise SystemExit("Passwords do not match.")
    try:
        created_email = provision_team_user(email, password)
    except ValueError as exception:
        raise SystemExit(str(exception)) from exception
    except sqlite3.IntegrityError as exception:
        raise SystemExit("A team account already exists for that email.") from exception
    print(f"Team access provisioned for {created_email}.")


if __name__ == "__main__":
    main()