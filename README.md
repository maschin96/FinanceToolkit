# FinanceToolkit

Python Toolbox für Simulation und Analyse von Aktien, europäischen Optionen,
festverzinslichen Anleihen und gemischten Portfolios. **M2 / Version 0.2.0**
auf dem Milestone-Branch erweitert den stabilen M1-Funktionsumfang. Die M2-Release-
Veröffentlichung erfolgt erst nach Integration und Zielcommit-CI gemäß Release-Prozess. Das Repository ist privat;
es erfolgt keine Veröffentlichung auf PyPI.

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
uv sync --locked --extra plots
uv run --no-sync python -m pytest
uv run --no-sync python -m ruff check .
uv run --no-sync python -m ruff format --check .
uv run --no-sync python -m mypy src/finance_toolkit
git diff --check
uv build
```

Nach `uv sync` alternativ die virtuelle Umgebung aktivieren und `python -m ...`
verwenden. Ohne `plots` sind ausschließlich die optionalen Diagrammtests sichtbar übersprungen;
Release-CI installiert `plots` und prüft alle Tests und Beispiele ohne Auslassungen.
CI prüft Python 3.11–3.13, Paketbau und frische Wheel-Installation außerhalb des
Quellbaums. [M1-Verifikationsbericht](Doc/16_M1_VERIFICATION.md) und
[M2-Verifikationsbericht](Doc/20_M2_VERIFICATION.md) enthält Referenzen und
Modellgrenzen. Updates: `uv lock --upgrade`, vollständige Matrix erneut prüfen.
[Abhängigkeiten und Lizenzen](Doc/10_DEPENDENCIES.md).

## Modellgrenzen

GBM mit konstanter Drift/Volatilität; europäische Barausgleichsoptionen;
ausfallfreie feste Kupons, regelmäßige Zahlungen und flache stetige Zinskurven.
Aktien liefern Preisrenditen ohne Dividenden-Cashflows. Keine Live-Daten,
Kalibrierung, Steuern, FX, Brokeranbindung, Margin-Engine, amerikanische Optionen,
GUI oder externe Portfolio-Zu-/Abflüsse. Numerisch verifiziert, nicht empirisch
gegen reale Marktdaten validiert.

[Dokumentation](Doc/README.md) · [Roadmap](Doc/06_ROADMAP.md) ·
[Entwicklungsregeln](AGENTS.md) · [Änderungen](CHANGELOG.md)
