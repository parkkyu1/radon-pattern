from __future__ import annotations

import argparse
import getpass

import bcrypt


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a bcrypt reviewer access-code hash.")
    parser.add_argument("--code", help="Omit to enter without terminal echo.")
    args = parser.parse_args()
    code = args.code or getpass.getpass("Access code: ")
    if len(code) < 12:
        raise SystemExit("Use an access code with at least 12 characters.")
    print(bcrypt.hashpw(code.encode(), bcrypt.gensalt(rounds=12)).decode())


if __name__ == "__main__":
    main()

