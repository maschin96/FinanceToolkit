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
