"""Lazy Textual app factory; importing adapters keeps the core profile usable."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from typing import TYPE_CHECKING

from finance_toolkit.tui.config import Workspace
from finance_toolkit.tui.jobs import Jobs
from finance_toolkit.tui.services import run_portfolio

if TYPE_CHECKING:
    from textual.app import App


def create_app(*, work: Callable[[Workspace], object] = run_portfolio) -> App[None]:
    """Create an optional UI with a bounded worker and keyboard-only navigation."""
    from textual.app import App, ComposeResult
    from textual.containers import Container, VerticalScroll
    from textual.events import Resize
    from textual.screen import ModalScreen
    from textual.widgets import (
        Button,
        ContentSwitcher,
        Footer,
        Header,
        Input,
        Label,
        Static,
    )

    class Help(ModalScreen[None]):
        BINDINGS = [("escape", "dismiss", "Zurück")]

        def compose(self) -> ComposeResult:
            with VerticalScroll():
                yield Static(
                    "FinanceToolkit Tastaturhilfe\n\n"
                    "Ctrl+1…6: Ansichten; Tab/Shift+Tab: Fokus; Enter: Aktion.\n"
                    "Ctrl+R: Demo rechnen; Escape: Lauf abbrechen.\n"
                    "F1: Hilfe; Ctrl+Q: Beenden.\n\n"
                    "Abbruch verwirft das Ergebnis. Ein laufender Kernaufruf kann\n"
                    "weiterrechnen; bis zu seinem Ende bleibt ein neuer Lauf\n"
                    "gesperrt.\n"
                    "Keine Prozentanzeige ohne messbaren Fortschritt.\n\n"
                    "Navigation und Jobs sind verfügbar; Fachformulare folgen\n"
                    "in den Paketen C–G. Escape schließt diese Hilfe.",
                    markup=False,
                )
                yield Button("Zurück", id="close-help")

        def on_button_pressed(self, event: Button.Pressed) -> None:
            self.dismiss()

    class FinanceApp(App[None]):
        TITLE = "FinanceToolkit"
        CSS = """
        #size-warning { height: auto; background: $warning; color: $text; }
        #status { height: auto; padding: 0 1; background: $panel; }
        #pages { height: 1fr; }
        VerticalScroll { padding: 1; }
        Button { margin: 1 0; }
        Button:focus { border: heavy $accent; }
        Help, Diagnostics { align: center middle; }
        Help > VerticalScroll, Diagnostics > VerticalScroll {
            width: 90%; height: 85%; background: $panel;
        }
        """
        BINDINGS = [
            ("ctrl+1", "page('start')", "Start"),
            ("ctrl+2", "page('portfolio')", "Portfolio"),
            ("ctrl+3", "page('risk')", "Risiko"),
            ("ctrl+4", "page('strategy')", "Strategien"),
            ("ctrl+5", "page('index')", "Indizes"),
            ("ctrl+6", "page('workspace')", "Workspace"),
            ("ctrl+r", "calculate", "Rechnen"),
            ("escape", "cancel", "Abbruch"),
            ("f1", "help", "Hilfe"),
            ("f2", "diagnostics", "Diagnose"),
            ("ctrl+q", "quit", "Beenden"),
        ]

        def __init__(self) -> None:
            super().__init__()
            self.workspace = Workspace()
            self.jobs = Jobs(work)
            self.input_error = ""
            self.ready = False
            self.status_view = Static("idle – bereit", id="status", markup=False)

        def compose(self) -> ComposeResult:
            yield Header()
            yield Static(
                "Terminal mindestens 80×24; Ctrl+Q beendet.", id="size-warning"
            )
            yield self.status_view
            with ContentSwitcher(initial="start", id="pages"):
                with VerticalScroll(id="start"):
                    yield Static(
                        "Offline-Demo: 100 Aktien, Seed 42, 100 Pfade, 12 Schritte."
                    )
                    yield Label("Seed (nichtnegative ganze Zahl)")
                    yield Input("42", id="seed")
                    yield Button("Offline-Demo rechnen (Ctrl+R)", id="run")
                    yield Button("Hilfe (F1)", id="help-button")
                    yield Button("Beenden (Ctrl+Q)", id="quit-button")
                for page, label, issue in (
                    ("portfolio", "Simulation / Portfolio", 76),
                    ("risk", "Risiko / Stress", 77),
                    ("strategy", "Strategien / Hedging", 78),
                    ("index", "Indizes / Daten", 79),
                    ("workspace", "Workspace / Export", 80),
                ):
                    with VerticalScroll(id=page):
                        yield Static(f"{label}: Fachformulare folgen in #{issue}.")
                        yield Button("Zur Startansicht", id=f"back-{page}")
                with Container(id="result"):
                    yield Static(
                        "Noch kein Ergebnis", id="result-content", markup=False
                    )
            yield Footer()

        def on_mount(self) -> None:
            self.ready = True
            self.set_interval(0.05, self.poll_jobs)
            self.query_one("#run", Button).focus()
            self.check_size()

        def on_resize(self, event: Resize) -> None:
            if self.ready:
                self.query_one("#size-warning").display = (
                    event.size.width < 80 or event.size.height < 24
                )

        def check_size(self) -> None:
            self.query_one("#size-warning").display = (
                self.size.width < 80 or self.size.height < 24
            )

        def action_page(self, page: str) -> None:
            self.query_one("#pages", ContentSwitcher).current = page
            button = self.query_one(f"#{page}").query(Button).first()
            button.focus()

        def action_help(self) -> None:
            self.push_screen(Help(id="help"))

        def action_diagnostics(self) -> None:
            self.push_screen(
                Diagnostics(self.jobs.diagnostic or "Keine Fehlerdiagnose.")
            )

        def action_calculate(self) -> None:
            try:
                if self.input_error:
                    raise ValueError(self.input_error)
                self.jobs.start(self.workspace)
            except ValueError as error:
                self.status_view.update(str(error))
            else:
                self.poll_jobs()

        def action_cancel(self) -> None:
            self.jobs.cancel()
            self.poll_jobs()

        def poll_jobs(self) -> None:
            self.jobs.poll()
            suffix = " – veraltet: Eingaben geändert" if self.jobs.stale else ""
            if self.jobs.state == "running":
                suffix = " – Aktivität, kein messbarer Prozentfortschritt"
            if self.jobs.state == "cancelled" and self.jobs.busy:
                suffix = " – Kernaufruf läuft noch; Ergebnis wird verworfen"
            message = f"{self.jobs.state} – Lauf {self.jobs.run_id}{suffix}"
            if self.jobs.error:
                message += "\n" + self.jobs.error
            if self.input_error:
                message += "\nEingabe: " + self.input_error
            self.status_view.update(message)

        def on_input_changed(self, event: Input.Changed) -> None:
            self.jobs.changed()
            try:
                seed = int(event.value)
                self.workspace = replace(
                    self.workspace,
                    simulation=replace(self.workspace.simulation, seed=seed),
                )
            except ValueError:
                self.input_error = "Seed muss eine nichtnegative ganze Zahl sein."
            else:
                self.input_error = ""
            if self.ready:
                self.poll_jobs()

        async def on_button_pressed(self, event: Button.Pressed) -> None:
            if event.button.id == "run":
                self.action_calculate()
            elif event.button.id == "help-button":
                self.action_help()
            elif event.button.id == "quit-button":
                await self.action_quit()
            else:
                self.action_page("start")

        async def action_quit(self) -> None:
            self.jobs.close()
            await super().action_quit()

        def on_unmount(self) -> None:
            self.ready = False
            self.jobs.close()

    class Diagnostics(Help):
        def __init__(self, message: str) -> None:
            super().__init__(id="diagnostics")
            self.message = message

        def compose(self) -> ComposeResult:
            with VerticalScroll():
                yield Static(self.message, id="diagnostic", markup=False)
                yield Button("Zurück", id="close-diagnostic")

    return FinanceApp()
