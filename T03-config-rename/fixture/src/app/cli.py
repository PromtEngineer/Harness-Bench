"""Command-line entry point."""
from .config import SUPPORT_EMAIL, product_string

DESCRIPTION = "Orion command-line interface"


def banner():
    return f"{product_string()} — {DESCRIPTION}"


def main(argv=None):
    print(banner())
    print(f"Questions? Contact {SUPPORT_EMAIL}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
