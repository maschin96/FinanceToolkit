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
    # App navigation and workers follow in #75. This initial shell verifies
    # real module/console starts without pulling UI imports into core modules.
    from textual.app import App, ComposeResult
    from textual.widgets import Footer, Header, Static

    class ContractApp(App[None]):
        BINDINGS = [("q", "quit", "Beenden")]

        def compose(self) -> ComposeResult:
            yield Header()
            yield Static("FinanceToolkit – M5: Navigation folgt in Paket B (#75).")
            yield Footer()

    ContractApp().run()
