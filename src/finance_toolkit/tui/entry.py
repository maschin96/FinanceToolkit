"""Lazy terminal entry point; help also works in a core-only installation."""

import argparse
import sys


def main() -> None:
    """Start the optional UI; exit 2 with installation advice if absent."""
    parser = argparse.ArgumentParser(description="FinanceToolkit Terminal-App")
    parser.parse_args()
    try:
        import textual  # noqa: F401
    except ModuleNotFoundError as error:
        if error.name != "textual":
            raise
        print(
            "Bitte finance-toolkit[tui] installieren: uv sync --extra tui",
            file=sys.stderr,
        )
        raise SystemExit(2) from None
    from finance_toolkit.tui.app import create_app

    create_app().run()
