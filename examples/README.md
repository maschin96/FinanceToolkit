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
