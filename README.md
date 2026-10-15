# FinanceToolkit

Python Toolbox für Simulation und Analyse von Aktien, europäischen Optionen,
festverzinslichen Anleihen und gemischten Portfolios. **M4 / Version 0.3.1**
stabilisiert dynamische Optionsbücher, Delta-Hedging, P&L-Attribution,
Strategievergleiche, optionale Yahoo-Marktdaten und eigene Aktienindizes.
Das Repository und seine Release-Artefakte sind öffentlich; keine PyPI-Veröffentlichung.

## Funktionen

- Exakte geometrische Brownsche Bewegung: konfigurierbare Drift, Volatilität,
  Laufzeit, Anzahl der Pfade/Schritte, Seed und korrelierte Aktien.
- Europäische Calls/Puts nach Black-Scholes-Merton mit stetigen Zinsen und
  Dividendenrendite; simulierte Käufe/Verkäufe und Long-/Short-Positionen.
- Festverzinsliche ausfallfreie Anleihen: Nennwert, Kupon, Laufzeit,
  Zahlungsfrequenz, Clean-/Dirty-Preis, Stückzinsen und variable Zinsszenarien.
- Gemeinsames Positionsbuch: Cash, Ausführungspreise, Gebühren, explizite
  Finanzierung, Kupons, Tilgung und einmalige Optionsabrechnung.
- Portfolioverläufe, P&L, Renditen, Drawdown, aggregierter VaR und Expected Shortfall.
- Offline-Beispiele, CSV/JSON-Exporte und optionale Diagramme.
- Analytische Options-Greeks, Portfolio-Exposures und Anleihen-DV01/Konvexität.
- Hypothetische Stressszenarien mit vollständiger Neubewertung und Heatmap.
- Pfadabhängige Aktien-/Cash-Strategien: Buy-and-Hold, Kalender- und Schwellen-
  Rebalancing mit verzögerter Ausführung, Gebühren und Cashbegrenzung.

## Installation und Beispiele

Python 3.11–3.13. Entwicklung mit uv 0.11.23 und eingecheckter uv.lock.
[uv installieren](https://docs.astral.sh/uv/getting-started/installation/), dann:

```sh
uv sync --locked --extra plots
uv run --no-sync python -m finance_toolkit.examples --seed 42 --paths 1000 --output outputs/m1-demo --plot
```

Das M2 Risk Lab:

```sh
uv run --no-sync python -m finance_toolkit.risk_lab --seed 42 --paths 1000 --output outputs/m2-demo --plot
```

[Risk-Lab-APIs und Grenzen](Doc/19_RISK_LAB.md). Ohne Diagramme: `uv sync --locked` und den Beispielaufruf ohne `--plot` ausführen.
Installation nur der Laufzeitbibliothek: `uv sync --locked --no-dev`.
`--locked` verhindert unbemerkte Dependency-Änderungen. Python-Patchversion und
Plattform können variieren; Reproduzierbarkeit gilt bei gleichem Abhängigkeitsstand.
[Beispiele und Parameter](examples/README.md) zeigen Änderungen an Zins, Laufzeit
und Kupon sowie Protective Put, Covered Call und Anleihen-Zinsvergleiche.

## M3 – Strategy & Hedging Lab

```sh
uv sync --locked --extra plots --extra yahoo
uv run --no-sync python -m finance_toolkit.hedge_lab --paths 100 --steps 32 --seed 314 --output outputs/m3-hedge --plot
uv run --no-sync python -m finance_toolkit.index_lab --config examples/m3_index_demo.json --demo --output outputs/m3-index --plot
```

Beide Beispiele sind offline. [Hedge-Lab](Doc/26_M3_HEDGE_LAB.md),
[Yahoo-Daten und Nutzungsgrenzen](Doc/25_M3_YAHOO.md),
[eigene Indizes](Doc/27_M3_CUSTOM_INDICES.md). Aktien-Shorts und Cashkredite
benötigen explizite Freigabe; keine Margin- oder Brokeranbindung.

M4 vereinheitlicht Fälligkeitsereignisse und endliche Ergebnisverträge, prüft
Yahoo-Sitzungsdaten und CLI-Eingaben und vermeidet wiederholte Exportberechnungen.
Attributionen liegen jetzt separat unter `hedge/<name>/attribution.{json,csv}`
und `strategy/<name>/attribution.{json,csv}`. `comparison.json` ordnet diese
Pfade über `kind`/`name` zu; bestehende Exportleser müssen die neuen Pfade
beachten. [M4-Verifikation](Doc/30_M4_VERIFICATION.md) und
[Profilnachweis](Doc/29_M4_EXPORT_PROFILE.md) dokumentieren die Korrekturen.

## M5 – Terminal-App (Releasekandidat v0.4.0)

M5 ergänzt die optionale **Textual-TUI**: Simulation und Portfolios konfigurieren,
Risiken/Stress prüfen, Strategien und Hedges vergleichen sowie eigene Indizes und
reproduzierbare Exporte bedienen. Die Pflichtpakete #74–#80 sind integriert.
**v0.4.0 ist noch nicht veröffentlicht**: Die manuellen Tastaturprüfungen unter
macOS/Linux stehen vor der Freigabe aus. Stabiles Release bleibt v0.3.1.
[Verifikationsstand](Doc/38_M5_TUI_VERIFICATION.md) ·
[manuelle Prüfanleitung](Doc/39_M5_MANUAL_SMOKE.md) ·
[GitHub-Milestone](https://github.com/maschin96/FinanceToolkit/milestone/6).

```sh
uv sync --locked --extra tui
uv run --no-sync finance-toolkit-tui
```

Alternativ: `python -m finance_toolkit.tui`. Die sichtbare Menüleiste lässt sich
per Tab fokussieren und mit Links/Rechts bedienen. F3…F8 wählt Ansichten direkt,
Ctrl+R rechnet die Offline-Demo, Escape bricht ab, F1 zeigt Hilfe,
F2 Fehlerdiagnosen und Ctrl+Q beendet. Tab/Shift+Tab wechselt den Fokus,
Enter aktiviert Buttons. Bei Mac-Tastaturen gegebenenfalls Fn+F3…F8 verwenden. Die [Portfolioansicht](Doc/33_M5_TUI_PORTFOLIO.md) bietet GBM-/Finanzierungsfelder,
editierbare Aktien-/Options-/Anleihentrades und Vermögens-/Positionsansichten
mit Pfad-/Zeitwahl. [Risiko/Stress](Doc/34_M5_TUI_RISK.md) ergänzt explizite
Snapshots, Greeks/DV01 und benannte Schocks mit terminalem Stressraster.
[Strategie-/Hedgevergleiche](Doc/35_M5_TUI_STRATEGIES.md) bieten editierbare
Rebalancing-/Optionsstrategien, dynamische Orders, eigene Hedgefälle und
Attribution. [Indizes/Daten](Doc/36_M5_TUI_INDICES.md) bietet eine Datenvorschau,
Offline-Demo, Cache-Replay und ausdrückliche Yahoo-Aktionen.
[Workspaces/Exporte](Doc/37_M5_TUI_WORKSPACES.md) speichern Konfigurationen
explizit und exportieren vollständige numerische Ergebnisse mit Herkunftsnachweisen.

## Eigene Portfolios

```python
from finance_toolkit.analytics import analyze_portfolio
from finance_toolkit.portfolio import EuropeanOption, Stock, Trade, value_portfolio
from finance_toolkit.simulation import simulate_gbm

market = simulate_gbm(
    100.0, drift=0.06, volatility=0.20, horizon=2.0, steps=24, paths=1000, seed=42
)
put = EuropeanOption(
    asset=0, strike=100, maturity=2, volatility=0.20, kind="put", multiplier=100
)
portfolio = value_portfolio(
    market,
    [Trade(0, Stock(), 100), Trade(0, put, 1)],
    initial_cash=20_000,
    rate=0.03,
)
analysis = analyze_portfolio(portfolio, confidence=0.95)
print(analysis.wealth.shape)  # (1000, 25)
print(analysis.risk)
```

Optionsquotes sind je Underlying-Einheit, Vertragswerte berücksichtigen den
Multiplikator. Trade-Menge positiv = Kauf, negativ = Verkauf/Short. Zeit in Jahren,
Raten annualisiert und dezimal, eine gemeinsame konfigurierbare Währung.
Modellvolatilität für Optionen und reale GBM-Szenariodrift sind getrennte Eingaben.
Portfolio-Raster müssen alle relevanten Transaktions-/Zahlungstermine enthalten.

## Entwicklung und Verifikation

```sh
uv sync --locked --all-extras
uv run --no-sync python -m pytest
uv run --no-sync python -m ruff check .
uv run --no-sync python -m ruff format --check .
uv run --no-sync python -m mypy src/finance_toolkit
git diff --check
uv build
```

Nach `uv sync` alternativ die virtuelle Umgebung aktivieren und `python -m ...`
verwenden. Das Basis-/Dev-Profil ohne Extras lässt sich separat prüfen:

```sh
UV_PROJECT_ENVIRONMENT=/tmp/finance-core uv sync --locked
UV_PROJECT_ENVIRONMENT=/tmp/finance-core uv run --no-sync python -m pytest
```

Die CI prüft drei Installationsprofile: Vollprofil mit `tui`/`plots`/`yahoo`
auf Python 3.11–3.13 ohne Auslassungen; Kern ohne Extras mit 14 benannten
UI- und sieben Diagramm-Skips; `tui` ohne `plots`/`yahoo` mit sieben benannten
Diagramm-Skips. Numerische Tests, Replay-/Provider-Fakes und Offline-CLIs laufen
in allen Profilen. Kernimporte benötigen weder Textual, Matplotlib noch
pandas/yfinance. Paketbau und frische Wheelinstallation außerhalb des Quellbaums
prüfen dieselbe Suite einschließlich Headless-Demo/Export sowie Modul-/
Konsolenhilfe und bisherige Offline-CLIs. [Installationsprofile](Doc/10_DEPENDENCIES.md).
[M1-Verifikationsbericht](Doc/16_M1_VERIFICATION.md),
[M2-Verifikationsbericht](Doc/20_M2_VERIFICATION.md) und
[M3-Verifikationsbericht](Doc/28_M3_VERIFICATION.md) sowie
[M4-Verifikationsbericht](Doc/30_M4_VERIFICATION.md) enthalten Referenzen und
Modellgrenzen. Updates: `uv lock --upgrade`, vollständige Matrix erneut prüfen.
[Abhängigkeiten und Lizenzen](Doc/10_DEPENDENCIES.md).

CLI-Fehlervertrag (#64) für `examples`, `risk_lab`, `hedge_lab`, `index_lab`
und `yahoo`: Erfolg = Exitcode 0; Parser-/Syntaxfehler (z.B. fehlende Pflicht-
argumente) = 2 mit Usage; fachlich ungültige Eingaben, Provider-/Dateifehler oder
fehlende optionale Importe = 1 mit knapper Fehlermeldung ohne Traceback.
Yahoo-Polling-Abbruch bleibt 130. Timeout-/Retryparameter und Index-JSON-Typen
werden vor Providerzugriff geprüft. Index-Symbole müssen eine nichtleere
Liste nichtleerer Strings sein, ohne stille Typumwandlung. `TypeError`/
`KeyError` aus interner Programmierlogik werden nicht pauschal verschluckt.
Bibliotheks-APIs behalten ihren Exception-Vertrag; gültige Exporte bleiben gleich.

## Modellgrenzen

GBM mit konstanter Drift/Volatilität; europäische Barausgleichsoptionen;
ausfallfreie feste Kupons, regelmäßige Zahlungen und flache stetige Zinskurven.
Aktien liefern Preisrenditen ohne Dividenden-Cashflows. Yahoo-Daten sind optional,
ohne garantierte Echtzeit. Keine
Kalibrierung, Steuern, FX, Brokeranbindung, Margin-Engine, amerikanische Optionen,
GUI oder externe Portfolio-Zu-/Abflüsse. Numerisch verifiziert, nicht empirisch
gegen reale Marktdaten validiert.

[Dokumentation](Doc/README.md) · [Roadmap](Doc/06_ROADMAP.md) ·
[Entwicklungsregeln](AGENTS.md) · [Änderungen](CHANGELOG.md)
