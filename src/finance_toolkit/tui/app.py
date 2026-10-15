"""Lazy Textual app factory; importing adapters keeps the core profile usable."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict
from pathlib import Path
from typing import TYPE_CHECKING, Any

from finance_toolkit.tui.config import (
    HedgeCaseConfig,
    InstrumentConfig,
    ScenarioConfig,
    TradeConfig,
    Workspace,
    decode_workspace,
    encode_workspace,
)
from finance_toolkit.tui.forms import Field, form_fields, format_field, parse_field
from finance_toolkit.tui.index_service import (
    IndexData,
    IndexRunResult,
    QuoteResult,
    calculate_prepared_index,
    prepare_index,
    run_quotes,
)
from finance_toolkit.tui.jobs import Jobs
from finance_toolkit.tui.risk_service import RiskResult, run_risk
from finance_toolkit.tui.services import PortfolioResult, position_rows, run_portfolio
from finance_toolkit.tui.strategy_service import (
    StrategyResult,
    run_strategies,
    validate_strategies,
)
from finance_toolkit.tui.workspace import (
    RESULT_TYPES,
    ExportedResult,
    ExportToken,
    NumericResult,
    export_result,
    load_workspace,
    save_workspace,
    unwrap_result,
)

if TYPE_CHECKING:
    from textual.app import App

    from finance_toolkit.yahoo import YahooClient


def create_app(
    *,
    work: Callable[[Workspace], object] = run_portfolio,
    data_client: YahooClient | None = None,
) -> App[None]:
    """Create an optional UI with a bounded worker and keyboard-only navigation."""
    from textual.app import App, ComposeResult
    from textual.binding import Binding
    from textual.containers import Container, VerticalScroll
    from textual.events import Resize
    from textual.screen import ModalScreen
    from textual.widgets import (
        Button,
        Checkbox,
        ContentSwitcher,
        DataTable,
        Footer,
        Header,
        Input,
        Label,
        Sparkline,
        Static,
        Tab,
        Tabs,
    )

    def form_widgets(config: Any, prefix: str, exclude: set[str]) -> ComposeResult:
        for field in form_fields(type(config), exclude=exclude):
            yield Label(field.label)
            yield Input(
                format_field(getattr(config, field.name), percent=field.percent),
                id=f"{prefix}-{field.name}",
            )

    class TradeEditor(ModalScreen[TradeConfig | None]):
        BINDINGS = [("escape", "dismiss(None)", "Abbrechen")]

        def __init__(self, workspace: Workspace, trade: TradeConfig) -> None:
            super().__init__(id="trade-editor")
            self.workspace = workspace
            self.trade = trade

        def compose(self) -> ComposeResult:
            with VerticalScroll():
                yield Static("Trade: Kauf + / Verkauf −. Beträge in Workspace-Währung.")
                yield from form_widgets(self.trade, "trade", {"instrument"})
                yield from form_widgets(self.trade.instrument, "instrument", set())
                yield Static("", id="trade-error", markup=False)
                yield Button("Trade übernehmen", id="save-trade")
                yield Button("Abbrechen", id="cancel-trade")

        def on_input_changed(self, event: Input.Changed) -> None:
            event.stop()

        def on_button_pressed(self, event: Button.Pressed) -> None:
            event.stop()
            if event.button.id == "cancel-trade":
                self.dismiss(None)
                return
            try:
                payload: dict[str, Any] = {}
                for cls, prefix, excluded in (
                    (TradeConfig, "trade", {"instrument"}),
                    (InstrumentConfig, "instrument", set()),
                ):
                    data = {}
                    for field in form_fields(cls, exclude=excluded):
                        data[field.name] = parse_field(
                            self.query_one(f"#{prefix}-{field.name}", Input).value,
                            field.annotation,
                            percent=field.percent,
                        )
                    if prefix == "trade":
                        payload.update(data)
                    else:
                        payload["instrument"] = data
                workspace = encode_workspace(self.workspace)
                workspace["portfolio"]["trades"] = [payload]
                validated = decode_workspace(workspace).portfolio.trades[0]
            except ValueError as error:
                self.query_one("#trade-error", Static).update(str(error))
            else:
                self.dismiss(validated)

    class Help(ModalScreen[None]):
        BINDINGS = [("escape", "dismiss", "Zurück")]

        def compose(self) -> ComposeResult:
            with VerticalScroll():
                yield Static(
                    "FinanceToolkit Tastaturhilfe\n\n"
                    "F3…F8: Ansichten. Menüleiste per Tab fokussieren, "
                    "mit Links/Rechts wechseln.\n"
                    "Tab/Shift+Tab: Fokus; Enter: Aktion.\n"
                    "Ctrl+R: Demo rechnen; Escape: Lauf abbrechen.\n"
                    "F1: Hilfe; Ctrl+Q: Beenden.\n\n"
                    "Abbruch verwirft das Ergebnis. Ein laufender Kernaufruf kann\n"
                    "weiterrechnen; bis zu seinem Ende bleibt ein neuer Lauf\n"
                    "gesperrt.\n"
                    "Keine Prozentanzeige ohne messbaren Fortschritt.\n\n"
                    "Portfolio/Risiko/Strategien/Indizes sind verfügbar;\n"
                    "Dateiexporte folgen in G. Escape schließt die Hilfe.",
                    markup=False,
                )
                yield Button("Zurück", id="close-help")

        def on_button_pressed(self, event: Button.Pressed) -> None:
            self.dismiss()

    class CaseEditor(ModalScreen[HedgeCaseConfig | None]):
        BINDINGS = [("escape", "dismiss(None)", "Abbrechen")]

        def __init__(self, case: HedgeCaseConfig) -> None:
            super().__init__(id="case-editor")
            self.case = case

        def compose(self) -> ComposeResult:
            with VerticalScroll():
                yield from form_widgets(self.case, "case", set())
                yield Static("", id="case-error", markup=False)
                yield Button("Fall übernehmen", id="save-case")
                yield Button("Abbrechen", id="cancel-case")

        def on_input_changed(self, event: Input.Changed) -> None:
            event.stop()

        def on_button_pressed(self, event: Button.Pressed) -> None:
            event.stop()
            if event.button.id == "cancel-case":
                self.dismiss(None)
                return
            try:
                payload = {
                    field.name: parse_field(
                        self.query_one(f"#case-{field.name}", Input).value,
                        field.annotation,
                        percent=field.percent,
                    )
                    for field in form_fields(HedgeCaseConfig)
                }
                case = decode_workspace({"hedge": {"cases": [payload]}}).hedge.cases[0]
            except ValueError as error:
                self.query_one("#case-error", Static).update(str(error))
            else:
                self.dismiss(case)

    class ScenarioEditor(ModalScreen[ScenarioConfig | None]):
        BINDINGS = [("escape", "dismiss(None)", "Abbrechen")]

        def __init__(self, workspace: Workspace) -> None:
            super().__init__(id="scenario-editor")
            self.workspace = workspace

        def compose(self) -> ComposeResult:
            with VerticalScroll():
                yield from form_widgets(ScenarioConfig(), "scenario", set())
                yield Static("", id="scenario-error", markup=False)
                yield Button("Szenario übernehmen", id="save-scenario")
                yield Button("Abbrechen", id="cancel-scenario")

        def on_input_changed(self, event: Input.Changed) -> None:
            event.stop()

        def on_button_pressed(self, event: Button.Pressed) -> None:
            event.stop()
            if event.button.id == "cancel-scenario":
                self.dismiss(None)
                return
            try:
                payload = encode_workspace(self.workspace)
                payload["risk"]["scenarios"] = [
                    {
                        field.name: parse_field(
                            self.query_one(f"#scenario-{field.name}", Input).value,
                            field.annotation,
                            percent=field.percent,
                        )
                        for field in form_fields(ScenarioConfig)
                    }
                ]
                scenario = decode_workspace(payload).risk.scenarios[0]
            except ValueError as error:
                self.query_one("#scenario-error", Static).update(str(error))
            else:
                self.dismiss(scenario)

    class FinanceApp(App[None]):
        TITLE = "FinanceToolkit"
        CSS = """
        #size-warning { height: auto; background: $warning; color: $text; }
        #status { height: auto; padding: 0 1; background: $panel; }
        #pages { height: 1fr; }
        VerticalScroll { padding: 1; }
        Button { margin: 1 0; }
        Button:focus { border: heavy $accent; }
        Help, Diagnostics, TradeEditor { align: center middle; }
        ModalScreen > VerticalScroll {
            width: 90%; height: 85%; background: $panel;
        }
        DataTable { height: 12; }
        Sparkline { height: 3; }
        """
        BINDINGS = [
            ("f3", "page('start')", "Start"),
            ("f4", "page('portfolio')", "Portfolio"),
            ("f5", "page('risk')", "Risiko"),
            ("f6", "page('strategy')", "Strategien"),
            ("f7", "page('index')", "Indizes"),
            ("f8", "page('workspace')", "Workspace"),
            Binding("ctrl+1", "page('start')", show=False),
            Binding("ctrl+2", "page('portfolio')", show=False),
            Binding("ctrl+3", "page('risk')", show=False),
            Binding("ctrl+4", "page('strategy')", show=False),
            Binding("ctrl+5", "page('index')", show=False),
            Binding("ctrl+6", "page('workspace')", show=False),
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
            self.injected_work = work if work is not run_portfolio else None
            self.input_error = ""
            self.ready = False
            self.status_view = Static("idle – bereit", id="status", markup=False)
            self.draft = encode_workspace(self.workspace)
            self.field_errors: dict[str, str] = {}
            self.schema_error = ""
            self.field_map: dict[str, tuple[str, Field]] = {}
            self.selected_path = self.selected_time = 0
            self.rendered_run = 0
            self.numeric_source: NumericResult | None = None
            self.numeric_revision = -1
            self.export_token: ExportToken | None = None

        def compose(self) -> ComposeResult:
            yield Header()
            yield Static(
                "Terminal mindestens 80×24; Ctrl+Q beendet.", id="size-warning"
            )
            yield self.status_view
            yield Tabs(
                Tab("Start", id="nav-start"),
                Tab("Portfolio", id="nav-portfolio"),
                Tab("Risiko", id="nav-risk"),
                Tab("Strategien", id="nav-strategy"),
                Tab("Indizes", id="nav-index"),
                Tab("Workspace", id="nav-workspace"),
                id="navigation",
                active="nav-start",
            )
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
                with VerticalScroll(id="portfolio"):
                    yield Label("Gemeinsame Währung (drei Großbuchstaben, kein FX)")
                    yield Input(self.workspace.currency, id="currency")
                    yield Static(
                        "GBM: Seed in Startansicht; Vektoren in Assetreihenfolge."
                    )
                    for section, config, excluded in (
                        ("simulation", self.workspace.simulation, {"seed"}),
                        ("portfolio", self.workspace.portfolio, {"trades"}),
                    ):
                        for field in form_fields(type(config), exclude=excluded):
                            self.field_map[f"{section}-{field.name}"] = (section, field)
                        yield from form_widgets(config, section, excluded)
                    yield Static(
                        "Leere Quote=Modellpreis. Shorts/Kredit im statischen "
                        "Buch erlaubt; keine Margin."
                    )
                    yield DataTable(id="trades", cursor_type="row")
                    yield Button("Trade hinzufügen", id="add-trade")
                    yield Button("Ausgewählten Trade ändern", id="edit-trade")
                    yield Button("Ausgewählten Trade löschen", id="delete-trade")
                    yield Button("Portfolio rechnen (Ctrl+R)", id="run-portfolio")
                    yield Label("Ergebnispfad (ab 0; reine Anzeigeauswahl)")
                    yield Input("0", id="view-path")
                    yield Label("Ergebniszeitindex (ab 0; reine Anzeigeauswahl)")
                    yield Input("0", id="view-time")
                    yield Static(
                        "Noch kein Ergebnis", id="portfolio-summary", markup=False
                    )
                    yield Static(
                        "Gewählter Pfad: Vermögen (Währung), Zeit 0 bis Horizont"
                    )
                    yield Sparkline([], id="wealth-line")
                    yield DataTable(id="positions")
                    yield Static(
                        "Verlauf: höchstens 50 Zeitpunkte ab Auswahl. "
                        "Vollständige Arrays bleiben im Ergebnis."
                    )
                    yield DataTable(id="wealth-table")
                with VerticalScroll(id="risk"):
                    yield Static(
                        "Risiko: expliziter Snapshot, gleiche Trades/Cashflows."
                    )
                    for field in form_fields(
                        type(self.workspace.risk), exclude={"scenarios"}
                    ):
                        self.field_map[f"risk-{field.name}"] = ("risk", field)
                    yield from form_widgets(self.workspace.risk, "risk", {"scenarios"})
                    yield Static(
                        "Ohne eigene Namen: Spot×Zins-Kombinationen; "
                        "eigene Szenarien ersetzen diese Liste."
                    )
                    yield DataTable(id="scenario-list", cursor_type="row")
                    yield Button("Benanntes Szenario hinzufügen", id="add-scenario")
                    yield Button("Ausgewähltes Szenario löschen", id="delete-scenario")
                    yield Button("Risiko/Stress rechnen", id="run-risk")
                    yield Static(
                        "Noch kein Risikoergebnis", id="risk-summary", markup=False
                    )
                    yield Static("", id="exposure-error", markup=False)
                    yield DataTable(id="asset-greeks")
                    yield DataTable(id="position-greeks")
                    yield Static("Hypothetische Neubewertung ohne Wahrscheinlichkeit.")
                    yield DataTable(id="stress-results")
                    yield Static(
                        "Stressraster: Zeilen ΔVol (Prozentpunkte), "
                        "Spalten ΔSpot (%), P&L (Währung); maximal 50×50 Zellen."
                    )
                    yield DataTable(id="stress-grid")
                with VerticalScroll(id="strategy"):
                    yield Static(
                        "Gleicher Markt/Kapital; getrennte Openingannahmen. "
                        "Finanzierung/Zins in Portfolio; kein Gewinnranking."
                    )
                    for section, comparison_config, excluded in (
                        ("strategy", self.workspace.strategy, {"orders"}),
                        ("hedge", self.workspace.hedge, {"option", "cases"}),
                        ("hedge.option", self.workspace.hedge.option, set()),
                    ):
                        prefix = section.replace(".", "-")
                        for field in form_fields(
                            type(comparison_config), exclude=excluded
                        ):
                            self.field_map[f"{prefix}-{field.name}"] = (section, field)
                        yield from form_widgets(comparison_config, prefix, excluded)
                    yield Static(
                        "Eigene Hedgefälle ersetzen gemeinsame "
                        "Stride-/Regel-/Kostenfelder; leer = gemeinsame Felder."
                    )
                    yield DataTable(id="hedge-cases", cursor_type="row")
                    yield Button("Hedgefall hinzufügen", id="add-case")
                    yield Button("Hedgefall ändern", id="edit-case")
                    yield Button("Hedgefall löschen", id="delete-case")
                    yield Static(
                        "Dynamische Orders: Zeit ist der Ausführungszeitpunkt; "
                        "Signal am vorherigen Punkt, t=0 sofort."
                    )
                    yield DataTable(id="strategy-orders", cursor_type="row")
                    yield Button("Order hinzufügen", id="add-order")
                    yield Button("Order ändern", id="edit-order")
                    yield Button("Order löschen", id="delete-order")
                    yield Button("Strategien/Hedges rechnen", id="run-strategy")
                    yield Static(
                        "Noch kein Vergleich", id="strategy-summary", markup=False
                    )
                    yield DataTable(id="rebalancing-results")
                    yield Static(
                        "Buch mit Pfeiltasten auswählen; Details: Pfad 0, "
                        "maximal 50 Zeitpunkte, vollständige Daten im Ergebnis."
                    )
                    yield DataTable(id="strategy-books", cursor_type="row")
                    yield DataTable(id="book-ledger")
                    yield DataTable(id="book-attribution")
                with VerticalScroll(id="index"):
                    yield Static(
                        "1. Daten/fehlende Sitzungen prüfen. "
                        "2. Index mit angezeigten Daten rechnen. Keine FX-Konversion."
                    )
                    for field in form_fields(type(self.workspace.index)):
                        self.field_map[f"index-{field.name}"] = ("index", field)
                    yield from form_widgets(self.workspace.index, "index", set())
                    yield Button("Demo/Cache-Daten prüfen (Ctrl+R)", id="prepare-index")
                    yield Button(
                        "Yahoo-Historien jetzt online abrufen", id="fetch-index"
                    )
                    yield Button("Yahoo-Quotes jetzt online abrufen", id="fetch-quotes")
                    yield Static(
                        "Noch keine Daten geprüft", id="index-preview", markup=False
                    )
                    yield DataTable(id="index-sources")
                    yield Button(
                        "Index mit angezeigten Sitzungen rechnen", id="calculate-index"
                    )
                    yield Static("Noch kein Index", id="index-summary", markup=False)
                    yield DataTable(id="index-levels")
                    yield Static(
                        "Driftgewichte und Intervallbeiträge (Dezimalanteile); "
                        "maximal 50 Datenpunkte je Ansicht."
                    )
                    yield DataTable(id="index-contributions")
                    yield DataTable(id="quotes")
                with VerticalScroll(id="workspace"):
                    yield Label("Konfigurationsdatei (JSON)")
                    yield Input("outputs/workspace.json", id="workspace-path")
                    yield Checkbox(
                        "Vorhandene Dateien ausdrücklich überschreiben", id="overwrite"
                    )
                    yield Button("Konfiguration speichern", id="save-workspace")
                    yield Button(
                        "Konfiguration laden (ohne Berechnung)", id="load-workspace"
                    )
                    yield Label("Exportverzeichnis")
                    yield Input("outputs/tui-export", id="export-path")
                    yield Checkbox("Optionale Diagramme exportieren", id="export-plots")
                    yield Button("Aktuelles Ergebnis exportieren", id="export-result")
                    yield Static(
                        "Konfigurationen werden nur auf Anforderung gespeichert.",
                        id="workspace-status",
                        markup=False,
                    )
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
            self.refresh_trades()
            self.refresh_scenarios()
            self.refresh_orders()
            self.refresh_cases()

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
            self.query_one("#navigation", Tabs).active = f"nav-{page}"
            focus = self.query_one(f"#{page}").query("Input, Button, DataTable").first()
            focus.focus()

        def on_tabs_tab_activated(self, event: Tabs.TabActivated) -> None:
            if event.tabs.id == "navigation" and event.tab.id is not None:
                # Keep focus on the menu so repeated arrow presses still work.
                self.query_one(
                    "#pages", ContentSwitcher
                ).current = event.tab.id.removeprefix("nav-")

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
                page = self.query_one("#pages", ContentSwitcher).current
                if page == "index" and self.injected_work is None:
                    self.action_prepare_index()
                    return
                if page == "strategy" and self.injected_work is None:
                    validate_strategies(self.workspace)
                service = (
                    run_strategies
                    if page == "strategy"
                    else run_risk
                    if page == "risk"
                    else run_portfolio
                )
                self.begin_job(self.injected_work or service)
            except ValueError as error:
                self.status_view.update(str(error))

        def begin_job(
            self,
            service: Callable[[Workspace], object],
            *,
            export_token: ExportToken | None = None,
        ) -> None:
            try:
                if self.input_error:
                    raise ValueError(self.input_error)
                self.jobs.work = service
                self.jobs.start(
                    self.workspace,
                    cancel_guard=export_token.request_cancel if export_token else None,
                )
            except ValueError as error:
                self.status_view.update(str(error))
            else:
                self.export_token = export_token
                if export_token is None:
                    self.numeric_source = None
                self.query_one("#portfolio-summary", Static).update(
                    f"Lauf {self.jobs.run_id} gestartet – noch kein aktuelles Ergebnis."
                )
                for selector in (
                    "#positions",
                    "#wealth-table",
                    "#asset-greeks",
                    "#position-greeks",
                    "#stress-results",
                    "#stress-grid",
                    "#strategy-books",
                    "#rebalancing-results",
                    "#book-ledger",
                    "#book-attribution",
                    "#index-sources",
                    "#index-levels",
                    "#index-contributions",
                    "#quotes",
                ):
                    self.query_one(selector, DataTable).clear()
                self.query_one("#risk-summary", Static).update(
                    "Noch kein aktuelles Risikoergebnis."
                )
                self.query_one("#strategy-summary", Static).update(
                    "Noch kein aktueller Vergleich."
                )
                self.query_one("#wealth-line", Sparkline).data = []
                self.query_one("#index-preview", Static).update(
                    "Noch keine aktuellen Daten."
                )
                self.query_one("#index-summary", Static).update(
                    "Noch kein aktueller Index."
                )
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
            if isinstance(self.jobs.result, ExportedResult):
                message += f"\nExport geschrieben: {self.jobs.result.directory}"
            if self.input_error:
                message += "\nEingabe: " + self.input_error
            self.status_view.update(message)
            if self.jobs.state == "succeeded" and self.rendered_run != self.jobs.run_id:
                self.rendered_run = self.jobs.run_id
                numeric = unwrap_result(self.jobs.result)
                if isinstance(numeric, RESULT_TYPES) and not self.jobs.stale:
                    self.numeric_source = numeric
                    self.numeric_revision = self.jobs.run_revision
                self.render_portfolio()
                self.render_risk()
                self.render_strategies()
                self.render_index()

        def action_prepare_index(self, *, online: bool = False) -> None:
            if self.input_error:
                self.status_view.update(self.input_error)
                return
            if online:
                self.draft["index"]["source"] = "yahoo"
                self.workspace = decode_workspace(self.draft)
                self.query_one("#index-source", Input).value = "yahoo"
                self.jobs.changed()
            elif self.workspace.index.source == "yahoo":
                self.status_view.update(
                    "Online-Historien nur über den Yahoo-Abrufbutton."
                )
                return
            self.begin_job(
                lambda snapshot: prepare_index(
                    snapshot, client=data_client, online_authorized=online
                )
            )

        def action_index_calculate(self) -> None:
            data = self.jobs.result
            if not isinstance(data, IndexData) or self.jobs.state != "succeeded":
                self.status_view.update("Zuerst Daten und Sitzungen prüfen.")
                return
            self.begin_job(lambda snapshot: calculate_prepared_index(data, snapshot))

        def render_index(self) -> None:
            result = unwrap_result(self.jobs.result)
            data = result.data if isinstance(result, IndexRunResult) else result
            if isinstance(data, IndexData):
                config = data.config.index
                self.query_one("#index-preview", Static).update(
                    f"Sitzungen geprüft: {config.source}, {config.start} bis "
                    f"exklusiv {config.end}; Repair={config.repair}.\n"
                    f"Ausgeschlossene Sitzungen: {data.excluded_sessions}\n"
                    f"Fehlende Sitzungen je Ticker: {data.missing_sessions}\n"
                    "Die Indexrechnung verwendet erst nach Ihrer Aktion diese Daten."
                )
                table = self.query_one("#index-sources", DataTable)
                table.clear(columns=True)
                table.add_columns(
                    "Ticker",
                    "Quelle/Modus",
                    "Abrufzeit",
                    "Währung",
                    "Einheitenfaktor",
                    "Adjustierung",
                    "Zeitzone",
                    "Datenhash",
                )
                for ticker, history in data.histories.items():
                    table.add_row(
                        ticker,
                        history.source + " / " + history.source_mode,
                        history.fetched_at.isoformat(),
                        history.currency,
                        str(history.unit_scale),
                        history.adjustment,
                        history.timezone,
                        history.data_hash,
                    )
            if isinstance(result, IndexRunResult):
                index = result.index
                self.query_one("#index-summary", Static).update(
                    f"Preis-/Total-Return-Index in Punkten; Datenwährung "
                    f"{index.metadata['currency']}. Keine FX-Konversion.\n"
                    f"Preis: {index.metadata['price_model']}\n"
                    f"Total Return: {index.metadata['total_return_model']}"
                )
                table = self.query_one("#index-levels", DataTable)
                table.clear(columns=True)
                table.add_columns(
                    "Datum",
                    "Preisindex (Punkte)",
                    "Total Return (Punkte)",
                    "Preisrendite",
                    "Total-Return-Rendite",
                )
                for i, day in enumerate(index.price.dates[:50]):
                    table.add_row(
                        *(
                            str(x)
                            for x in (
                                day,
                                index.price.levels[i],
                                index.total_return.levels[i],
                                index.price.returns[i],
                                index.total_return.returns[i],
                            )
                        )
                    )
                table = self.query_one("#index-contributions", DataTable)
                table.clear(columns=True)
                table.add_columns(
                    "Art", "Datum", "Ticker", "Driftgewicht", "Intervallbeitrag"
                )
                for kind, values in (
                    ("Preis", index.price),
                    ("Total Return", index.total_return),
                ):
                    for i, day in enumerate(values.dates[:50]):
                        for j, ticker in enumerate(values.tickers[:50]):
                            table.add_row(
                                kind,
                                day,
                                ticker,
                                str(values.weights[i, j]),
                                str(values.contributions[i, j]),
                            )
            if isinstance(result, QuoteResult):
                self.query_one("#index-preview", Static).update(
                    "Expliziter Quoteabruf: regulärer Marktpreis, "
                    "keine Echtzeitzusage. "
                    "Börsenverzögerung kann unbekannt sein."
                )
                table = self.query_one("#quotes", DataTable)
                table.clear(columns=True)
                table.add_columns(
                    "Ticker",
                    "Preis",
                    "Währung",
                    "Quelle/Modus",
                    "Marktzeit",
                    "Abrufzeit",
                    "Börse",
                    "Zeitzone",
                    "Verzögerung (s)",
                    "Session",
                )
                for ticker, quote in result.quotes.items():
                    table.add_row(
                        *(
                            str(x)
                            for x in (
                                ticker,
                                quote.price,
                                quote.currency,
                                quote.source + " / " + quote.source_mode,
                                quote.market_time.isoformat(),
                                quote.fetched_at.isoformat(),
                                quote.exchange,
                                quote.timezone,
                                quote.delay_seconds
                                if quote.delay_seconds is not None
                                else "unbekannt",
                                quote.session,
                            )
                        )
                    )

        def on_input_changed(self, event: Input.Changed) -> None:
            key = event.input.id or ""
            if key in ("view-path", "view-time"):
                try:
                    value = int(event.value)
                    if key == "view-path":
                        self.selected_path = value
                    else:
                        self.selected_time = value
                    self.render_portfolio()
                except ValueError as error:
                    self.query_one("#portfolio-summary", Static).update(str(error))
                return
            if key not in self.field_map and key not in ("seed", "currency"):
                return
            if key in self.field_map:
                section, field = self.field_map[key]
                draft_section = self.draft
                for part in section.split("."):
                    draft_section = draft_section[part]
                if key not in self.field_errors and event.value == format_field(
                    draft_section[field.name], percent=field.percent
                ):
                    return
            self.jobs.changed()
            try:
                if key == "seed":
                    self.draft["simulation"]["seed"] = parse_field(event.value, int)
                elif key == "currency":
                    self.draft["currency"] = event.value
                else:
                    section, field = self.field_map[key]
                    draft_section = self.draft
                    for part in section.split("."):
                        draft_section = draft_section[part]
                    draft_section[field.name] = parse_field(
                        event.value, field.annotation, percent=field.percent
                    )
            except ValueError as error:
                self.field_errors[key] = str(error)
            else:
                self.field_errors.pop(key, None)
            try:
                self.workspace = decode_workspace(self.draft)
            except ValueError as error:
                self.schema_error = str(error)
            else:
                self.schema_error = ""
            self.input_error = "; ".join(
                [f"{k.capitalize()}: {v}" for k, v in self.field_errors.items()]
                + ([self.schema_error] if self.schema_error else [])
            )
            if self.ready:
                self.poll_jobs()

        def refresh_trades(self) -> None:
            table = self.query_one("#trades", DataTable)
            table.clear(columns=True)
            table.add_columns(
                "Nr.", "Zeit (Jahre)", "Instrument", "Menge", "Quote", "Gebühr"
            )
            for index, trade in enumerate(self.workspace.portfolio.trades):
                table.add_row(
                    str(index),
                    str(trade.time),
                    trade.instrument.kind,
                    str(trade.quantity),
                    str(trade.price),
                    str(trade.fee),
                )

        def edit_trade(self, *, add: bool, section: str = "portfolio") -> None:
            if self.input_error:
                self.status_view.update(self.input_error)
                return
            table_id = "trades" if section == "portfolio" else "strategy-orders"
            key = "trades" if section == "portfolio" else "orders"
            index = self.query_one(f"#{table_id}", DataTable).cursor_row
            trades = (
                self.workspace.portfolio.trades
                if section == "portfolio"
                else self.workspace.strategy.orders
            )
            if not add and not trades:
                self.status_view.update("Kein Trade ausgewählt.")
                return

            def saved(trade: TradeConfig | None) -> None:
                if trade is None:
                    return
                data = self.draft[section][key]
                if add:
                    data.append(asdict(trade))
                else:
                    data[index] = asdict(trade)
                self.workspace = decode_workspace(self.draft)
                self.jobs.changed()
                if section == "portfolio":
                    self.refresh_trades()
                else:
                    self.refresh_orders()
                self.query_one(f"#{table_id}", DataTable).move_cursor(
                    row=len(data) - 1 if add else index
                )
                self.poll_jobs()

            self.push_screen(
                TradeEditor(self.workspace, TradeConfig() if add else trades[index]),
                saved,
            )

        def refresh_orders(self) -> None:
            table = self.query_one("#strategy-orders", DataTable)
            table.clear(columns=True)
            table.add_columns(
                "Nr.", "Ausführung (Jahre)", "Instrument", "Menge", "Quote", "Gebühr"
            )
            for index, trade in enumerate(self.workspace.strategy.orders):
                table.add_row(
                    *(
                        str(x)
                        for x in (
                            index,
                            trade.time,
                            trade.instrument.kind,
                            trade.quantity,
                            trade.price,
                            trade.fee,
                        )
                    )
                )

        def refresh_cases(self) -> None:
            table = self.query_one("#hedge-cases", DataTable)
            table.clear(columns=True)
            table.add_columns(
                "Name",
                "Stride",
                "Kalender",
                "Delta-Schwelle",
                "Fixkosten",
                "Kostenanteil",
            )
            for case in self.workspace.hedge.cases:
                table.add_row(
                    *(
                        str(x)
                        for x in (
                            case.name,
                            case.stride,
                            case.calendar_every,
                            case.threshold,
                            case.fixed_fee,
                            case.proportional_fee,
                        )
                    )
                )

        def edit_case(self, *, add: bool) -> None:
            if self.input_error:
                self.status_view.update(self.input_error)
                return
            index = self.query_one("#hedge-cases", DataTable).cursor_row
            cases = self.workspace.hedge.cases
            if not add and not cases:
                return

            def saved(case: HedgeCaseConfig | None) -> None:
                if case is None:
                    return
                candidate = encode_workspace(self.workspace)
                if add:
                    candidate["hedge"]["cases"].append(asdict(case))
                else:
                    candidate["hedge"]["cases"][index] = asdict(case)
                try:
                    workspace = decode_workspace(candidate)
                    if workspace.hedge.enabled:
                        validate_strategies(workspace)
                except ValueError as error:
                    self.status_view.update(str(error))
                    return
                self.workspace, self.draft = workspace, candidate
                self.jobs.changed()
                self.refresh_cases()
                self.query_one("#hedge-cases", DataTable).move_cursor(
                    row=len(workspace.hedge.cases) - 1 if add else index
                )
                self.poll_jobs()

            self.push_screen(
                CaseEditor(HedgeCaseConfig() if add else cases[index]), saved
            )

        def render_strategies(self) -> None:
            result = unwrap_result(self.jobs.result)
            if not isinstance(result, StrategyResult):
                return
            self.query_one("#strategy-summary", Static).update(
                f"Opening: gleicher Markt/Seed {result.config.simulation.seed}, "
                f"Kapital {result.config.portfolio.initial_cash} "
                f"{result.config.currency}.\n"
                "Rebalancing: Zielgewichte; Optionen: konfigurierte Legs; "
                "Hedges: gleiche Openingoption, gekoppelte Raster.\n"
                "Lab-Strategiekontrollen: 0.9/1.1×Hedgestrike, keine Tradegebühr. "
                "Signale lesen nur gegenwärtige Beobachtungen; kein Gewinnranking."
            )
            table = self.query_one("#rebalancing-results", DataTable)
            table.clear(columns=True)
            table.add_columns(
                "Rebalancing",
                "Endvermögen (Mittel)",
                "Gebühren (alle Pfade)",
                "Umsatz (alle Pfade)",
            )
            for name, book in result.rebalancing.items():
                table.add_row(
                    name,
                    str(book.wealth[:, -1].mean()),
                    str(book.fees.sum()),
                    str(book.turnover.sum()),
                )
            table = self.query_one("#strategy-books", DataTable)
            table.clear(columns=True)
            table.add_columns("Kategorie/Name", "Endvermögen (Mittel)", "P&L (Mittel)")
            for name, ledger in result.books.items():
                wealth = ledger.wealth
                table.add_row(
                    name,
                    str(wealth[:, -1].mean()),
                    str((wealth[:, -1] - ledger.initial_cash).mean()),
                )
            for name, strategy_paths in result.rebalancing.items():
                wealth = strategy_paths.wealth
                table.add_row(
                    f"rebalancing/{name}",
                    str(wealth[:, -1].mean()),
                    str((wealth[:, -1] - strategy_paths.initial_cash).mean()),
                )
            self.render_book()

        def on_data_table_row_highlighted(
            self, event: DataTable.RowHighlighted
        ) -> None:
            if event.data_table.id == "strategy-books":
                self.render_book()

        def render_book(self) -> None:
            result = unwrap_result(self.jobs.result)
            if not isinstance(result, StrategyResult) or not result.books:
                return
            index = self.query_one("#strategy-books", DataTable).cursor_row
            if index >= len(result.books):
                rebalance_name = tuple(result.rebalancing)[
                    min(index - len(result.books), len(result.rebalancing) - 1)
                ]
                paths = result.rebalancing[rebalance_name]
                wealth = paths.wealth
                table = self.query_one("#book-ledger", DataTable)
                table.clear(columns=True)
                table.add_columns(
                    "Buch",
                    "Signalzeit (Jahre)",
                    "Ausführung (Jahre)",
                    "Cash",
                    "Vermögen",
                    "P&L",
                    "Trades",
                    "Gebühr",
                    "Umsatz",
                    "Finanzierung",
                )
                for i in range(min(50, len(paths.times))):
                    signal_time = (
                        paths.times[i - 1]
                        if i and paths.trades[0, i].any()
                        else "Opening"
                        if i == 0
                        else "kein Trade"
                    )
                    table.add_row(
                        *(
                            str(x)
                            for x in (
                                f"rebalancing/{rebalance_name}",
                                signal_time,
                                paths.times[i],
                                paths.cash[0, i],
                                wealth[0, i],
                                wealth[0, i] - paths.initial_cash,
                                paths.trades[0, i].tolist(),
                                paths.fees[0, i].sum(),
                                paths.turnover[0, i].sum(),
                                paths.financing[0, i],
                            )
                        )
                    )
                table = self.query_one("#book-attribution", DataTable)
                table.clear(columns=True)
                table.add_column(
                    "Rebalancing: Aktien-/Cash-Ledger, keine Options-Greek-Attribution"
                )
                return
            name = tuple(result.books)[min(index, len(result.books) - 1)]
            book = result.books[name]
            wealth = book.wealth
            hedge = result.hedges.get(name)
            table = self.query_one("#book-ledger", DataTable)
            table.clear(columns=True)
            table.add_columns(
                "Buch",
                "Signalzeit (Jahre)",
                "Zeit (Jahre)",
                "Cash",
                "Vermögen",
                "P&L",
                "Trades",
                "Gebühr",
                "Umsatz",
                "Finanzierung",
                "Leihkosten",
                "Restdelta (Aktien)",
            )
            for i in range(min(50, len(book.times))):
                table.add_row(
                    *(
                        str(x)
                        for x in (
                            name,
                            "Fälligkeit"
                            if hedge is not None
                            and i == len(book.times) - 1
                            and book.trades[0, i].any()
                            else book.times[i - 1]
                            if i and book.trades[0, i].any()
                            else "Opening"
                            if i == 0
                            else "kein Trade",
                            book.times[i],
                            book.cash[0, i],
                            wealth[0, i],
                            wealth[0, i] - book.initial_cash,
                            book.trades[0, i].tolist(),
                            book.fees[0, i].sum(),
                            book.turnover[0, i].sum(),
                            book.financing[0, i],
                            book.stock_borrow_costs[0, i].sum(),
                            hedge.residual_delta[0, i].tolist()
                            if hedge is not None
                            else "nicht Hedge",
                        )
                    )
                )
            attribution = result.attributions[name]
            reconciled = attribution.reconciled
            table = self.query_one("#book-attribution", DataTable)
            table.clear(columns=True)
            table.add_columns(
                "Intervall",
                "P&L",
                "Delta",
                "Gamma",
                "Theta",
                "Vega",
                "Rho",
                "Residuum",
                "Kosten",
                "Leihe",
                "Finanzierung",
                "Bilanz",
            )
            for i in range(min(50, len(book.times) - 1)):
                table.add_row(
                    *(
                        str(x)
                        for x in (
                            i,
                            wealth[0, i + 1] - wealth[0, i],
                            attribution.delta[0, i].sum(),
                            attribution.gamma[0, i].sum(),
                            attribution.theta[0, i].sum(),
                            attribution.vega[0, i].sum(),
                            attribution.rho[0, i].sum(),
                            attribution.residual[0, i].sum(),
                            attribution.fees[0, i].sum(),
                            attribution.borrow[0, i].sum(),
                            attribution.financing[0, i],
                            reconciled[0, i],
                        )
                    )
                )

        def render_portfolio(self) -> None:
            result = unwrap_result(self.jobs.result)
            if isinstance(result, RiskResult):
                result = result.base
            if not isinstance(result, PortfolioResult):
                return
            path, step = self.selected_path, self.selected_time
            try:
                rows = position_rows(result, path, step)
            except ValueError as error:
                self.query_one("#portfolio-summary", Static).update(str(error))
                return
            currency = result.config.currency
            analysis = result.analysis
            relative = (
                "Rendite undefiniert: Anfangskapital ≤0"
                if analysis.returns is None
                else f"Rendite {analysis.returns[path, step]:.6%}"
            )
            drawdown = (
                "Drawdown undefiniert: nichtpositives Vermögen"
                if analysis.drawdowns is None
                else f"Drawdown {analysis.drawdowns[path, step]:.6%}"
            )
            self.query_one("#portfolio-summary", Static).update(
                f"Lauf {self.jobs.run_id}; Pfad {path}, "
                f"Zeit {result.market.times[step]:.6g} Jahre; {currency}\n"
                f"Cash {result.portfolio.cash[path, step]:.8g}; "
                f"Vermögen {analysis.wealth[path, step]:.8g}; "
                f"P&L {analysis.pnl[path, step]:.8g}\n"
                f"{relative}; {drawdown}\n"
                "Alle Pfade: mittleres Endvermögen "
                f"{analysis.wealth[:, -1].mean():.8g} {currency}\n"
                f"Aggregierter terminaler VaR {analysis.risk.confidence:.1%}: "
                f"{analysis.risk.value_at_risk:.8g}; "
                f"ES {analysis.risk.expected_shortfall:.8g} {currency}"
            )
            positions = self.query_one("#positions", DataTable)
            positions.clear(columns=True)
            positions.add_columns(
                "Instrument",
                "Menge",
                f"Quote ({currency}/Einheit)",
                f"Wert ({currency})",
                "Dirty",
                "Clean",
                "Stückzins",
            )
            for row in rows:
                positions.add_row(
                    *(
                        str(row.get(key, "—"))
                        for key in (
                            "instrument",
                            "quantity",
                            "quote",
                            "value",
                            "dirty",
                            "clean",
                            "accrued",
                        )
                    )
                )
            self.query_one("#wealth-line", Sparkline).data = analysis.wealth[
                path, :: max(1, len(result.market.times) // 80)
            ].tolist()
            table = self.query_one("#wealth-table", DataTable)
            table.clear(columns=True)
            table.add_columns(
                "Zeit (Jahre)",
                f"Cash ({currency})",
                f"Vermögen ({currency})",
                f"P&L ({currency})",
            )
            for i in range(step, min(step + 50, len(result.market.times))):
                table.add_row(
                    *(
                        str(x)
                        for x in (
                            result.market.times[i],
                            result.portfolio.cash[path, i],
                            analysis.wealth[path, i],
                            analysis.pnl[path, i],
                        )
                    )
                )

        def refresh_scenarios(self) -> None:
            table = self.query_one("#scenario-list", DataTable)
            table.clear(columns=True)
            table.add_columns(
                "Name", "ΔSpot (dezimal)", "ΔVol (dezimal)", "ΔZins (dezimal)"
            )
            for scenario in self.workspace.risk.scenarios:
                table.add_row(
                    scenario.name,
                    str(scenario.spot_shocks),
                    str(scenario.volatility_shocks),
                    str(scenario.rate_shock),
                )

        def add_scenario(self) -> None:
            if self.input_error:
                self.status_view.update(self.input_error)
                return

            def saved(scenario: ScenarioConfig | None) -> None:
                if scenario is None:
                    return
                candidate = encode_workspace(self.workspace)
                candidate["risk"]["scenarios"].append(asdict(scenario))
                try:
                    workspace = decode_workspace(candidate)
                except ValueError as error:
                    self.status_view.update(str(error))
                    return
                self.draft = candidate
                self.workspace = workspace
                self.jobs.changed()
                self.refresh_scenarios()
                self.poll_jobs()

            self.push_screen(ScenarioEditor(self.workspace), saved)

        def render_risk(self) -> None:
            result = unwrap_result(self.jobs.result)
            if not isinstance(result, RiskResult):
                return
            risk = result.base.analysis.risk
            currency = result.base.config.currency
            self.query_one("#risk-summary", Static).update(
                f"Snapshot: Pfad {result.base.config.risk.path}, "
                f"t={result.snapshot.time:.8g} Jahre; "
                f"Cash {result.snapshot.cash:.8g} {currency}\n"
                f"Terminaler aggregierter Verlust: VaR {risk.confidence:.1%} "
                f"{risk.value_at_risk:.8g}; "
                f"ES {risk.expected_shortfall:.8g} {currency}\n"
                "Stress-P&L ist hypothetisch und besitzt keine Konfidenz."
            )
            self.query_one("#exposure-error", Static).update(
                "Greeks undefiniert: " + result.exposure_error
                if result.exposure_error
                else ""
            )
            assets = self.query_one("#asset-greeks", DataTable)
            assets.clear(columns=True)
            assets.add_columns(
                "Asset", "Delta (Underlying)", "Gamma (Underlying/Währung)"
            )
            positions = self.query_one("#position-greeks", DataTable)
            positions.clear(columns=True)
            positions.add_columns(
                "Position",
                "Menge",
                "Multiplikator",
                "Delta",
                "Gamma",
                f"Vega {currency}/Vol-pp",
                f"Rho {currency}/Zins-pp",
                f"Theta {currency}/Jahr",
                f"DV01 {currency}/bp",
                "Konvexität Jahre²",
            )
            exposures = result.exposures
            if exposures is not None:
                for asset, (delta, gamma) in enumerate(
                    zip(exposures.asset_delta, exposures.asset_gamma, strict=True)
                ):
                    assets.add_row(str(asset), str(delta), str(gamma))
                for index, instrument in enumerate(result.snapshot.instruments):
                    positions.add_row(
                        *(
                            str(x)
                            for x in (
                                index,
                                result.base.portfolio.quantities[
                                    result.base.config.risk.time_index, index
                                ],
                                getattr(instrument, "multiplier", 1),
                                exposures.position_delta[index],
                                exposures.position_gamma[index],
                                exposures.position_vega[index] * 0.01,
                                exposures.position_rho[index] * 0.01,
                                exposures.position_theta[index],
                                exposures.position_dv01[index],
                                exposures.bond_convexity[index],
                            )
                        )
                    )
            scenarios = self.query_one("#stress-results", DataTable)
            scenarios.clear(columns=True)
            scenarios.add_columns(
                "Szenario",
                f"Basis {currency}",
                f"Stress {currency}",
                f"P&L {currency}",
                f"Cash {currency}",
                "Positions-P&L",
            )
            for scenario in result.scenarios:
                scenarios.add_row(
                    scenario.name,
                    str(scenario.base_value),
                    str(scenario.stressed_value),
                    str(scenario.total_pnl),
                    str(scenario.cash),
                    str(scenario.position_pnl.tolist()),
                )
            grid = self.query_one("#stress-grid", DataTable)
            grid.clear(columns=True)
            grid.add_columns(
                "ΔVol (pp)",
                *(
                    f"ΔSpot {shock:.1%}"
                    for shock in result.base.config.risk.spot_shocks[:50]
                ),
            )
            for shock, row in zip(
                result.base.config.risk.grid_volatility_shocks[:50],
                result.grid[:50],
                strict=True,
            ):
                grid.add_row(str(shock * 100), *(str(value) for value in row[:50]))

        def action_save_workspace(self) -> None:
            try:
                if self.input_error:
                    raise ValueError(self.input_error)
                path = Path(self.query_one("#workspace-path", Input).value)
                save_workspace(
                    self.workspace,
                    path,
                    overwrite=self.query_one("#overwrite", Checkbox).value,
                )
            except (ValueError, OSError) as error:
                self.query_one("#workspace-status", Static).update(str(error))
            else:
                self.query_one("#workspace-status", Static).update(
                    f"Konfiguration gespeichert: {path}"
                )

        def action_load_workspace(self) -> None:
            try:
                path = Path(self.query_one("#workspace-path", Input).value)
                workspace = load_workspace(path)
            except (ValueError, OSError) as error:
                self.query_one("#workspace-status", Static).update(str(error))
                return
            self.workspace = workspace
            self.draft = encode_workspace(workspace)
            self.field_errors.clear()
            self.input_error = self.schema_error = ""
            self.jobs.changed()
            for key, (section, field) in self.field_map.items():
                values = self.draft
                for part in section.split("."):
                    values = values[part]
                self.query_one(f"#{key}", Input).value = format_field(
                    values[field.name], percent=field.percent
                )
            self.query_one("#seed", Input).value = str(workspace.simulation.seed)
            self.query_one("#currency", Input).value = workspace.currency
            self.refresh_trades()
            self.refresh_orders()
            self.refresh_cases()
            self.refresh_scenarios()
            self.query_one("#workspace-status", Static).update(
                f"Konfiguration geladen: {path}. "
                "Keine Berechnung oder Netzabfrage gestartet."
            )
            self.poll_jobs()

        def action_export_result(self) -> None:
            if (
                self.numeric_source is None
                or self.numeric_revision != self.jobs.revision
            ):
                self.status_view.update(
                    "Zuerst ein aktuelles numerisches Ergebnis berechnen."
                )
                return
            result = self.numeric_source
            target = Path(self.query_one("#export-path", Input).value)
            overwrite = self.query_one("#overwrite", Checkbox).value
            plots = self.query_one("#export-plots", Checkbox).value
            token = ExportToken()
            self.begin_job(
                lambda snapshot: export_result(
                    result, target, overwrite=overwrite, plot=plots, token=token
                ),
                export_token=token,
            )

        async def on_button_pressed(self, event: Button.Pressed) -> None:
            if event.button.id == "save-workspace":
                self.action_save_workspace()
            elif event.button.id == "load-workspace":
                self.action_load_workspace()
            elif event.button.id == "export-result":
                self.action_export_result()
            elif event.button.id in (
                "run",
                "run-portfolio",
                "run-risk",
                "run-strategy",
            ):
                self.action_calculate()
            elif event.button.id == "prepare-index":
                self.action_prepare_index()
            elif event.button.id == "fetch-index":
                self.action_prepare_index(online=True)
            elif event.button.id == "calculate-index":
                self.action_index_calculate()
            elif event.button.id == "fetch-quotes":
                self.begin_job(
                    lambda snapshot: run_quotes(
                        snapshot, client=data_client, online_authorized=True
                    )
                )
            elif event.button.id in ("add-order", "edit-order"):
                self.edit_trade(add=event.button.id == "add-order", section="strategy")
            elif event.button.id in ("add-case", "edit-case"):
                self.edit_case(add=event.button.id == "add-case")
            elif event.button.id == "delete-case":
                if not self.input_error and self.workspace.hedge.cases:
                    index = self.query_one("#hedge-cases", DataTable).cursor_row
                    del self.draft["hedge"]["cases"][index]
                    self.workspace = decode_workspace(self.draft)
                    self.jobs.changed()
                    self.refresh_cases()
                    self.poll_jobs()
            elif event.button.id == "delete-order":
                if not self.input_error and self.workspace.strategy.orders:
                    index = self.query_one("#strategy-orders", DataTable).cursor_row
                    del self.draft["strategy"]["orders"][index]
                    self.workspace = decode_workspace(self.draft)
                    self.jobs.changed()
                    self.refresh_orders()
                    self.poll_jobs()
            elif event.button.id == "add-scenario":
                self.add_scenario()
            elif event.button.id == "delete-scenario":
                if not self.input_error and self.workspace.risk.scenarios:
                    index = self.query_one("#scenario-list", DataTable).cursor_row
                    del self.draft["risk"]["scenarios"][index]
                    self.workspace = decode_workspace(self.draft)
                    self.jobs.changed()
                    self.refresh_scenarios()
                    self.poll_jobs()
            elif event.button.id in ("add-trade", "edit-trade"):
                self.edit_trade(add=event.button.id == "add-trade")
            elif event.button.id == "delete-trade":
                if self.input_error:
                    self.status_view.update(self.input_error)
                    return
                if self.workspace.portfolio.trades:
                    index = self.query_one("#trades", DataTable).cursor_row
                    del self.draft["portfolio"]["trades"][index]
                    self.workspace = decode_workspace(self.draft)
                    self.jobs.changed()
                    self.refresh_trades()
                    self.poll_jobs()
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
