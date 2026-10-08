# Änderungen

## 0.2.0 – M2 vorbereitet, noch nicht veröffentlicht

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

Numerisch verifiziert; keine empirische Marktvalidierung. Private GitHub-Artefakte,
keine PyPI-Veröffentlichung. Grenzen und Referenzen im M1-Verifikationsbericht.
