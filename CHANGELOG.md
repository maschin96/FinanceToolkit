# Änderungen

## 0.3.0 – 2026-10-08

- Dynamisches Optionsbuch mit pfadabhängigen Orders, Settlement und Cashbilanz.
- Explizite Kredit-/Anlagezinsen, Aktien-Shorts und Aktienleihekosten.
- Verzögertes Kalender-/Schwellen-Delta-Hedging mit gekoppelter Rasterreferenz.
- Protective Put, Covered Call, Collar und vertikale Optionsspreads.
- Exakte P&L-Reconciliation und lokale Greek-Näherung mit Ereignis-/Restfehlern.
- Reproduzierbares Hedge-Lab mit gemeinsamen Pfaden, CSV/JSON und PNG.
- Optionaler Yahoo-Adapter mit Einheiten-/Zeit-Audit, Cache und Offline-Replay.
- Eigene Kurs-/Total-Return-Indizes mit verzögertem Rebalancing und Offline-Demo.
- Vollständige Python-3.11–3.13-CI mit allen vier Offline-CLIs und Wheel-Prüfung.

Keine empirische Validierung, keine garantierte Echtzeit oder Marktdatenrechte.

## 0.2.0 – 2026-10-08

- Analytische BSM-Greeks mit Broadcasting und expliziten Einheiten/Grenzen.
- Portfolio-Exposures je Position/Underlying; Anleihen-DV01 und Konvexität.
- Vollständige Snapshot-Neubewertung unter Spot-/Volatilitäts-/Zinsschocks.
- Pfadabhängige Long-only-Aktien-/Cash-Strategien mit verzögerter Ausführung,
  Cashbegrenzung, festen/proportionalen Gebühren und expliziter Finanzierung.
- Kalender- und Schwellen-Rebalancing einschließlich Cashrest.
- Reproduzierbares Offline-Risk-Lab mit CSV/JSON und optionalen PNGs.
- Bestehende M1-APIs und Arrayformen erhalten; keine neuen Pflichtabhängigkeiten.

## 0.1.0 – 2026-10-07

Erster vollständiger M1-Funktionsumfang:

- Korrelierte exakte GBM-Aktiensimulation mit reproduzierbaren Seeds/Generatoren.
- Europäische Calls/Puts, Black-Scholes-Merton, Payoffs und deterministische Grenzen.
- Kupon-/Nullkuponanleihen, Stückzinsen, Clean-/Dirty-Bewertung und Zinsszenarien.
- Long-/Short-Trades, Ausführungspreise, Gebühren, Finanzierung und einmalige Zahlungen.
- Portfolioverläufe, P&L, Rendite, Drawdown, aggregierter VaR/Expected Shortfall.
- Offline-Beispiele, CSV/JSON und optionale Matplotlib-Diagramme.
- Python 3.11–3.13, gelockte Abhängigkeiten, Tests, Lint/Format, strikte Typprüfung,
  Paketbau und frische Wheel-Prüfung in der CI-Matrix.

Numerisch verifiziert; keine empirische Marktvalidierung. Öffentliche GitHub-Artefakte,
keine PyPI-Veröffentlichung. Grenzen und Referenzen im M1-Verifikationsbericht.
