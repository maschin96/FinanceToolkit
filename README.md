# FinanceToolkit

Python Toolbox für Simulation und Analyse von Aktien, europäischen Optionen,
festverzinslichen Anleihen und daraus zusammengesetzten Portfolios.

**Stand:** Installierbare Paketbasis mit reproduzierbarer Entwicklungsumgebung und
CI für Python 3.11–3.13. Numerische APIs und Beispiele folgen in M1.
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
Die Entwicklung verwendet uv 0.11.23 und die eingecheckte `uv.lock`.
[uv installieren](https://docs.astral.sh/uv/getting-started/installation/), dann:

```sh
uv sync --locked --python 3.13
uv run --no-sync python -m pytest
uv run --no-sync python -m ruff check .
uv run --no-sync python -m ruff format --check .
uv run --no-sync python -m mypy src/finance_toolkit
git diff --check
```

Alternativ nach `uv sync`: Umgebung aktivieren (`source .venv/bin/activate`) und
Prüfungen mit `python -m ...` ausführen. Der Lock legt Paketversionen und
Artefakt-Hashes fest; `--locked` verhindert unbemerkte Änderungen. Python-Patchversion
und Plattform können variieren. CI prüft alle drei unterstützten Minorversionen.

Paket bauen: `uv build`. Installation ohne Entwicklungswerkzeuge:
`uv sync --locked --no-dev`. Das Paket stellt zunächst nur Versionsmetadaten bereit.
CI testet auch das gebaute Wheel in einer frischen Umgebung außerhalb des Quellbaums.
Dependency-Updates werden bewusst mit `uv lock --upgrade` vorgenommen und erneut
in der vollständigen CI-Matrix geprüft. [Abhängigkeiten](Doc/10_DEPENDENCIES.md).

[Roadmap und Issues](Doc/06_ROADMAP.md) · [Dokumentation](Doc/README.md) ·
[Entwicklungsrichtlinien](AGENTS.md)
