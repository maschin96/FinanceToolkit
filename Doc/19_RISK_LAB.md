# M2 – Risk Lab

## Portfolio-Exposures (#23)

`PortfolioSnapshot(time, instruments, quantities, spots, rate, cash)` beschreibt
einen post-event Zustand. Arrays sind eindimensionale Kopien, Spots je Asset,
Mengen je Position; signed Mengen und Optionsmultiplikatoren werden explizit
berücksichtigt. Keine Buchung erfolgt bei der Snapshot-Analyse.

`portfolio_exposures(snapshot)` liefert Positions-Delta/Gamma/Vega/Theta/Rho,
Anleihen-DV01 und Konvexität sowie Delta/Gamma je Asset. Portfolio-Vega bezeichnet
einen gemeinsamen absoluten Volatilitätsschock, Portfolio-Rho einen parallelen
Zinsschock. Cash bleibt unverändert. Fällige und mengenlose Positionen sind null;
aktive nichtglatte Optionen werden für Greeks abgelehnt.

`bond_sensitivity(bond, time, rate=...)`: Rho = −Summe(tau*CF*exp(−r*tau)),
zweite Ableitung = Summe(tau²*CF*exp(−r*tau)); DV01 = −Rho*1e-4,
Konvexität = zweite Ableitung / Dirty-Preis. Ex-Zahlungsbewertung wie in M1.

Red: `pytest tests/test_exposures.py` scheiterte am fehlenden risk-Modul.
Green: 71 betroffene Tests einschließlich Greeks, Bonds und Portfolio bestanden;
mypy und ruff grün. Nullkupon und unabhängig summierte Kupon-Cashflows dienen als
Referenz; Gegenpositionen, Asset-Zuordnung und Multiplikator werden geprüft.
Siehe [Verträge](18_M2_CONTRACTS.md) für Einheiten und Toleranzen.

## Stressszenarien (#24)

`stress_portfolio(snapshot, StressScenario(name, spot_shocks=..., volatility_shocks=...,
rate_shock=...))` liefert Positionswerte, Positions-P&L und Gesamtwerte bei
unverändertem Cash. Spot-Schocks relativ, Volatilitäts-/Zinsschocks absolute
Dezimaländerungen. Scalar-Volatilitätsschocks betreffen alle Optionen;
Positionsvektoren müssen bei Nichtoptionen null sein. Ungültige Schocks werden
abgelehnt. `stress_grid(snapshot, spot_axis, volatility_axis)` liefert P&L mit
Form (Volatilität, Spot), über identische vollständige Neubewertung.

Red: fehlender StressScenario-Import; zusätzlicher Regressionstest für
überlaufenden Zins bei Cash-only Snapshot zunächst rot. Green: Stress-Tests
prüfen Nullschock, Aktien-Handrechnung, ATM-Optionspreisreferenz, Nullkupon,
Fälligkeiten und schrumpfende Fehler der lokalen Delta/Gamma-Näherung.
Keine Wahrscheinlichkeiten, keine Interpretation als VaR/ES.

## Pfadabhängige Ausführung (#25)

`simulate_strategy(market, signal, initial_cash=..., initial_weights=...,
fixed_fee=0, proportional_fee=0, lending_rate=0)` hat eine eigene `StrategyPaths`-
Struktur mit Mengen/Trades/Gebühren/Umsatz (paths,times,assets). M1 bleibt erhalten.
Gebühren und Umsatz sind positiv; Trades signed Stückzahlen. `wealth` ist Cash
plus Aktienwerte; `weights` enthält Aktiengewichte, der Rest ist Cash.

Ein `signal(StrategyState)` erhält aktuelle Zeit, readonly Kopien von Kursen und
Mengen sowie Cash und Vermögen, liefert Zielstückzahlen oder None. Signale gelten
am nächsten Rasterpunkt. Anfangsallokation sofort mit denselben Kosten;
letzter Rasterpunkt löst keinen weiteren Signalaufruf aus. Built-in-Regeln sind
zustandslos; eigene Callbacks müssen ebenfalls ohne Pfad-übergreifenden Zustand
arbeiten. Verkaufs-/Kaufreihenfolge und Cashbegrenzung siehe Verträge.

Red: fehlendes strategies-Modul. Green: Ein-Pfad-Handrechnung, verzögerte Trades,
Prefix-Invarianz, Zustandskopien, Nullaufträge, Finanzierung, Cashknappheit,
unfinanzierbare Kleinstverkäufe und Cashflow-Bilanzen. Unabhängige Cashbilanz:
C(t)=C(0)+Summe(Finanzierung − Trade-Stückzahl*Preis − Gebühren).
Nur Rundungsreste aus der berechneten Kaufobergrenze werden bis 1e-12 relativ
auf null begrenzt, kein fachlich negatives Cash. Gewinne nicht vorausgesetzt.
