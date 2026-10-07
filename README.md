# FinanceToolkit

Python Toolbox für Simulation und Analyse von Aktien, europäischen Optionen,
festverzinslichen Anleihen und daraus zusammengesetzten Portfolios.

**Stand:** Projektauftrag und GitHub-Backlog vorhanden. Numerische APIs, Installation,
Beispiele und CI werden erst mit den folgenden Issues implementiert.
Das Repository ist privat; es gibt noch kein veröffentlichtes Python-Paket.

## Geplanter erster Funktionsumfang

- Aktienpfade aus geometrischer Brownscher Bewegung mit konfigurierbarer Drift,
  Volatilität, Horizont, Seed und Korrelation mehrerer Aktien.
- Europäische Calls und Puts: analytische Bewertung, Long-/Short-Positionen,
  Käufe und Verkäufe, Prämien und Barausgleich bei Verfall.
- Ausfallfreie festverzinsliche Anleihen mit variierbarem Zins, Nennwert,
  Kupon, Laufzeit und Zahlungsfrequenz; Zins-Szenarien und Anleihenportfolios.
- Gemischte Portfolios mit Cashkonto, Gebühren, Neubewertung, Vermögensverläufen,
  P&L, Rendite, Drawdown sowie Value at Risk und Expected Shortfall.

Die erste Version verwendet eine einzige konfigurierbare Währung, Zeit in Jahren,
Jahresraten als Dezimalzahlen und europäische Optionsausübung.
Brokerhandel, Live-Marktdaten, Steuern, Kreditrisiken, amerikanische Optionen und
GUI sind nicht Bestandteil von M1. Kaufen und Verkaufen bezeichnet simulierte
Portfolio-Transaktionen.

## Entwicklung

Zielplattform: Python 3.11–3.13. Paketstruktur: `src/finance_toolkit/`.
NumPy und SciPy bilden den numerischen Kern; pytest, ruff und mypy die Prüfwerkzeuge.
Die reproduzierbare Installation und CI sind Gegenstand von
[Issue #2](https://github.com/maschin96/FinanceToolkit/issues/2) und noch nicht eingerichtet.

[Roadmap und Issues](Doc/06_ROADMAP.md) · [Dokumentation](Doc/README.md) ·
[Entwicklungsrichtlinien](AGENTS.md)
