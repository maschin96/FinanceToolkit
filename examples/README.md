# Reproduzierbare Portfolio-Beispiele

Installation aus dem Repository:

```sh
uv sync --locked
uv run --no-sync python -m finance_toolkit.examples --seed 42 --paths 1000 --output outputs/m1-demo
```

Mit Diagrammen:

```sh
uv sync --locked --extra plots
uv run --no-sync python -m finance_toolkit.examples --seed 42 --paths 1000 --output outputs/m1-demo --plot
```

Parameter: `--rate 0.03` (stetiger Jahreszins), `--maturity 2`
(Laufzeit in Jahren, volle Halbjahre), `--coupon 0.04` (nominaler Jahreskupon),
`--seed 42`, `--paths 1000`. Laufzeit verändert auch den Simulationshorizont;
Zeitpunkte sind monatlich. Alle Portfolios starten mit Cash 20.000.

- Aktie: 100 Aktien mit Anfangskurs 100, Drift 6%, Volatilität 20%.
- Protective Put: 100 Aktien plus ein europäischer Put (Strike 100,
  Multiplikator 100); die bezahlte Prämie reduziert Cash.
- Covered Call: 100 Aktien minus ein europäischer Call; der Verkauf erhält Prämie
  und begrenzt den Aktiengewinn oberhalb des Strikes.
- Anleihen: 100 Anleihen zu Nennwert 100, halbjährlicher Kupon; Tilgung am Ende.
- Anleihen mit steigenden/fallenden flachen Kurven: Zinsen verändern sich bis zum
  Ende linear um ±2 Prozentpunkte. Kupons werden nicht reinvestiert, Cash wird
  nicht verzinst. Zwischenwerte ändern sich; identische vertragliche Zahlungen
  führen am Ende zu gleichem Vermögen. Das ist eine bewusst isolierte Preissensitivität.

`summary.csv` enthält Zeit, Vermögensmittel/-median, 5-/95%-Quantile, Cash und
alle mittleren Cashflows. `*_wealth.csv` exportiert jeden einzelnen Pfad.
`risk.json` enthält aggregierten VaR/ES (95%); `parameters.json` den Parametersatz.
Optional: `wealth.png` und `bond_rates.png`. Ergebnisse werden nicht versioniert.

Die Beispiele benötigen offline keine Marktdaten. Reproduzierbar bei gleichem
Seed und Abhängigkeitsstand; keine empirische Marktvalidierung. Die 5–95%-Bänder
zeigen simulierte Szenarien, keine Prognose- oder Konfidenzintervalle für reale Kurse.

Zur eigenen Analyse ohne Dateiexport:

```python
from finance_toolkit.examples import build_examples
from finance_toolkit.analytics import analyze_portfolio

portfolios = build_examples(
    seed=42, paths=1000, rate=0.03, maturity=2, coupon_rate=0.04
)
analysis = analyze_portfolio(portfolios["protective_put"], confidence=0.95)
print(analysis.risk)
```

Eigene Trades werden mit `Stock`, `EuropeanOption`, `Bond` und `Trade` aufgebaut;
Zeitpunkte und Bewertungsregeln stehen in [Portfolio-Dokumentation](../Doc/14_PORTFOLIO.md).

## M2 – Portfolio Risk Lab

Auf dem M2-Branch nach Installation:

```sh
uv run --no-sync python -m finance_toolkit.risk_lab --seed 42 --paths 1000 --steps 12 --output outputs/m2-demo --plot
```

Ohne `--plot` bleiben alle numerischen Exporte verfügbar. Drei Aktien-/Cash-
Strategien (Buy-and-Hold, Kalender alle drei Rasterpunkte, Schwelle 5 pp) teilen
GBM-Pfade, Kapital, Eröffnungskosten und Finanzierung. Signale werden erst am
Folgepunkt ausgeführt. Der separate Aktien-/Protective-Put-Vergleich teilt
Aktienpfade, Kapital und Cashverzinsung; die Put-Prämie reduziert verfügbares Cash.
Kein empirisches Backtesting, keine implizite Überlegenheit einer Strategie.

- `summary.json`: sämtliche Parameter, Seed, Version, Einheiten, VaR/ES,
  End-P&L, Rendite, Drawdown und mittlere Strategie-Kosten/Umsätze.
- `wealth.csv`: jede Portfolio-/Pfad-/Zeit-Beobachtung mit P&L, Rendite,
  Drawdown soweit definiert, Cash und Finanzierung einmal pro Zeitpunkt.
- `strategy_ledger.csv`: Kurse, Bestände, signed Trades, positive Gebühren,
  Umsatz und tatsächliche Gewichte je Asset; Cashrest = 1 − Aktiengewichte.
- `exposures.csv`, `asset_exposures.csv`, `common_exposures.csv`: Positionen,
  Delta/Gamma je Asset und beschriftete gemeinsame Volatilitäts-/Zinsexposures.
- `stress.csv`: hypothetische Basis-/Crash-/Zinsschocks, Einzelpositionen, Cash,
  Gesamt-P&L am Anfangs-Snapshot. Nicht als VaR interpretieren.
- `stress_grid.csv`: vollständige Protective-Put-Neubewertung für die Heatmap.
- Optional `strategies.png`, `protective_put.png`, `stress.png`.

Handrechnung des Ausführungskerns: Kapital 100, Kurs 10, Ziel 50 %, ohne Kosten:
fünf Aktien und 50 Cash. Bei Kurs 20 Vermögen 150; ein 50-%-Signal fordert
3,75 Aktien. Am Folgepunkt bei Kurs 20 Verkauf 1,25 Aktien, Cash 75. Vermögen
bleibt 150; eine Verkaufsgebühr 1 reduziert es auf 149. Das Beispiel exportiert
wirklich ausgeführte Mengen, sodass Kosten- und Cashbegrenzungen sichtbar sind.
[API und Grenzen](../Doc/19_RISK_LAB.md), [Konventionen](../Doc/18_M2_CONTRACTS.md).
