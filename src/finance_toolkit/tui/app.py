"""Lazy Textual app factory; importing adapters keeps the core profile usable."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict
from typing import TYPE_CHECKING, Any

from finance_toolkit.tui.config import (
    InstrumentConfig,
    ScenarioConfig,
    TradeConfig,
    Workspace,
    decode_workspace,
    encode_workspace,
)
from finance_toolkit.tui.forms import Field, form_fields, format_field, parse_field
from finance_toolkit.tui.jobs import Jobs
from finance_toolkit.tui.risk_service import RiskResult, run_risk
from finance_toolkit.tui.services import PortfolioResult, position_rows, run_portfolio

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
        DataTable,
        Footer,
        Header,
        Input,
        Label,
        Sparkline,
        Static,
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
                    "Ctrl+1…6: Ansichten; Tab/Shift+Tab: Fokus; Enter: Aktion.\n"
                    "Ctrl+R: Demo rechnen; Escape: Lauf abbrechen.\n"
                    "F1: Hilfe; Ctrl+Q: Beenden.\n\n"
                    "Abbruch verwirft das Ergebnis. Ein laufender Kernaufruf kann\n"
                    "weiterrechnen; bis zu seinem Ende bleibt ein neuer Lauf\n"
                    "gesperrt.\n"
                    "Keine Prozentanzeige ohne messbaren Fortschritt.\n\n"
                    "Portfolio/Risiko sind verfügbar; weitere Fachansichten\n"
                    "folgen in E–G. Escape schließt diese Hilfe.",
                    markup=False,
                )
                yield Button("Zurück", id="close-help")

        def on_button_pressed(self, event: Button.Pressed) -> None:
            self.dismiss()

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
                for page, label, issue in (
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
            self.refresh_trades()
            self.refresh_scenarios()

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
            focus = self.query_one(f"#{page}").query("Input, Button, DataTable").first()
            focus.focus()

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
                self.jobs.work = self.injected_work or (
                    run_risk if page == "risk" else run_portfolio
                )
                self.jobs.start(self.workspace)
            except ValueError as error:
                self.status_view.update(str(error))
            else:
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
                ):
                    self.query_one(selector, DataTable).clear()
                self.query_one("#risk-summary", Static).update(
                    "Noch kein aktuelles Risikoergebnis."
                )
                self.query_one("#wealth-line", Sparkline).data = []
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
            if self.jobs.state == "succeeded" and self.rendered_run != self.jobs.run_id:
                self.rendered_run = self.jobs.run_id
                self.render_portfolio()
                self.render_risk()

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
                if key not in self.field_errors and event.value == format_field(
                    self.draft[section][field.name], percent=field.percent
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
                    self.draft[section][field.name] = parse_field(
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

        def edit_trade(self, *, add: bool) -> None:
            if self.input_error:
                self.status_view.update(self.input_error)
                return
            index = self.query_one("#trades", DataTable).cursor_row
            trades = self.workspace.portfolio.trades
            if not add and not trades:
                self.status_view.update("Kein Trade ausgewählt.")
                return

            def saved(trade: TradeConfig | None) -> None:
                if trade is None:
                    return
                data = self.draft["portfolio"]["trades"]
                if add:
                    data.append(asdict(trade))
                else:
                    data[index] = asdict(trade)
                self.workspace = decode_workspace(self.draft)
                self.jobs.changed()
                self.refresh_trades()
                self.query_one("#trades", DataTable).move_cursor(
                    row=len(data) - 1 if add else index
                )
                self.poll_jobs()

            self.push_screen(
                TradeEditor(self.workspace, TradeConfig() if add else trades[index]),
                saved,
            )

        def render_portfolio(self) -> None:
            result = self.jobs.result
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
            result = self.jobs.result
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

        async def on_button_pressed(self, event: Button.Pressed) -> None:
            if event.button.id in ("run", "run-portfolio", "run-risk"):
                self.action_calculate()
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
