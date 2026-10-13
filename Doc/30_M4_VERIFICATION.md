# M4-Gesamtverifikation – 0.3.1 (#66)

## Audit und Pflichtumfang

Ausgangspunkt ist M3/v0.3.0, main `7e4230b`, mit 295 erfolgreichen Tests.
M4 behebt die acht Audit-Befunde ohne neue Finanzmodelle, Pflichtabhängigkeiten
oder geänderte fachliche Toleranzen. Alle Funktionsissues sind nach aktueller
grüner CI und eigenem Diff-Review in `codex/milestone-m4` integriert und
explizit geschlossen. Ein unabhängiger Reviewer war nicht verfügbar;
eine externe Freigabe wird nicht behauptet.

| Issue | Korrektur / Nachweis | Issue-PR |
| --- | --- | --- |
| #58 | Einheitliche Fälligkeitstoleranz und einmaliges Settlement | [#67](https://github.com/maschin96/FinanceToolkit/pull/67) |
| #59 | Separate verlustfreie Hedge-/Strategieattributionen | [#68](https://github.com/maschin96/FinanceToolkit/pull/68) |
| #60 | Endliche Ergebnisse und robuste Nettoaggregation | [#69](https://github.com/maschin96/FinanceToolkit/pull/69) |
| #61 | Ausschließlich benötigte BSM-Grenzzweige | [#70](https://github.com/maschin96/FinanceToolkit/pull/70) |
| #62 | Lokale Yahoo-Sitzungsdaten im Requestintervall | [#71](https://github.com/maschin96/FinanceToolkit/pull/71) |
| #63 | Basisprofil ohne Extras und vollständiges Releaseprofil | [#72](https://github.com/maschin96/FinanceToolkit/pull/72) |
| #64 | Erwartete CLI-Eingabefehler ohne Traceback | [#83](https://github.com/maschin96/FinanceToolkit/pull/83) |
| #65 | Profilgestützte lokale Ergebniswiederverwendung | [#84](https://github.com/maschin96/FinanceToolkit/pull/84) |

Die PRs #67–#72 und #83 dokumentieren Regressionstests vor der Korrektur
(Red wegen des fehlenden Verhaltens) und anschließend erfolgreiche gezielte/
betroffene Prüfungen. #84 ist verhaltensneutrales Refactoring: 38 vorhandene
Tests vor Umbau grün, zwei zusätzliche Verhaltenstests ebenfalls vorher grün,
danach alle 40 grün. Das Abschlussarbeitspaket aktualisiert ausschließlich
Paketversion/Lockfile und Dokumentation; kein künstlicher Red-Test nötig.

## Wissenschaftliche Referenzen und Grenzfälle

- `tests/test_attribution.py::test_tolerant_expiry_reconciles_and_exports_once`:
  S=100, K=100, T=1 Jahr; zwei Pfade haben bei Fälligkeit S=120/80. Call-Payoff 20/0,
  Put-Payoff 0/20, signed Menge/Multiplikator (2,1) und (-3,10). Zeitoffsets
  -5e-11/0/+5e-11 Jahre liegen in der unveränderten 1e-10-Jahre-Zuordnung.
  Settlement/Mengen/Events exakt, keine zweite Zahlung; Cash = 1000 minus
  Openingprämie plus signed Payoff. Vermögen/Reconciliation 1e-10 Währung
  absolut und 1e-12 relativ bei Kapital um 1000; Ereignisrest 1e-10 Währung.
  Preise, Zahlungszeitpunkt und Toleranzkonvention: ADR-012 und
  [Attributionsvertrag](24_M3_ATTRIBUTION.md).
- `tests/test_numerical_limits.py`: unabhängige Long-/Short-/Cash-Summen mit
  großen Bruttowerten und endlichem Netto, echte Nettoüberläufe, kleine Reste
  nach exakter Gegenbuchung, Nullmengen, signed Strategie-Payoffs und
  nicht darstellbare Attributions-/Vergleichskennzahlen. Für Netto um 1e308
  ist rtol=2e-15, atol=0 eine relative Float64-Rundungsgrenze; kein riesiges
  absolutes Fehlerbudget. Exakte kleine Handreste bleiben erhalten. NumPy-
  Warnungen und nichtendliche Ergebnisse gelten als Fehler, nicht als Nachweis.
  [ADR-013](07_RISKS_AND_DECISIONS.md) beschreibt den lokalen Fraction-Fallback.
- `tests/test_options.py`: Verfall, Null-Spot/-Volatilität und gemischtes
  Broadcasting mit extremen endlichen, im Grenzfall irrelevanten Parametern.
  Aktive nicht darstellbare Berechnungen bleiben ungültig. Unabhängiges
  diskontiertes Payoff-Integral, Put-Call-Parität, bekannte BSM-Preise und
  Preisgrenzen bleiben unverändert Teil der Suite; [Optionsvertrag](12_OPTIONS.md).
- `tests/test_options_book.py`, `test_book_finance.py`, `test_hedging.py`:
  Cash-/Mengenbilanzen, Teilverkauf, Short-Settlement, Gebühren, Guthaben-/
  Kreditzinsen und Leihe weiterhin grün. Gekoppelter Hedge-Konvergenztest:
  1000 risikoneutrale Pfade, Seed 314, S=K=100, sigma=.2, T=1, Nullkosten/
  Nullzinsen; RMS bei 128 Schritten unter 70% des 16-Schritt-RMS auf denselben
  Pfaden. [M3-Referenzen und Toleranzen](28_M3_VERIFICATION.md) unverändert.
- `tests/test_hedge_lab.py`: alle fünf Strategienamen auch als Hedge-Namen,
  zwei Handpfade 100/110/120 und 100/90/80; jede CSV-/JSON-Attribution getrennt
  gegen Kernresultate und Bilanz geprüft (1e-10 Währung, 1e-12 relativ).
  Wiederholung byteidentisch. [Exportvertrag](26_M3_HEDGE_LAB.md).

[M1](16_M1_VERIFICATION.md) und [M2](20_M2_VERIFICATION.md) bleiben vollständig
in der Gesamtsuite: GBM-Momente/Korrelation, Anleihencashflows, analytische
Greeks, Stress-/Rebalancing- und Index-Handreferenzen. Keine Erwartungen
abgeschwächt oder Toleranzen zum Erzwingen grüner Tests aufgeweitet.

## Adapter, CLI und Performance

`tests/test_yahoo.py` verwendet synthetische Providerdaten: start-inklusive/
end-exklusive lokale Sitzungsdaten, verschiedene Zeitzonen und DST, online
vor Cache-Schreiben sowie Replay. Ungültige Antworten überschreiben keinen
gültigen Cache; gültige Teilintervalle/Lücken bleiben zulässig. Netzwerk,
Uhrzeit und Live-Yahoo sind keine Unit-Test-Abhängigkeiten. ADR-015 und
[Yahoo-Vertrag](25_M3_YAHOO.md) dokumentieren die Datumssemantik.

42 Tests in `tests/test_cli_errors.py` prüfen fünf CLI-Grenzen: erwartete
ValueError/DataError/OSError/ImportError ergeben Exitcode 1 und knappe stderr
ohne Traceback; Parserfehler bleiben 2, Erfolg 0, Pollingabbruch 130.
Ungültige Index-JSON-Typen und Timeout-/Retrywerte werden vor Providerzugriff
abgelehnt. Interne TypeError/KeyError bleiben sichtbar. ADR-016 und README
beschreiben die API-/CLI-Grenze.

Kompatibilitätsänderung #59: Attributionen jetzt in
`hedge/<name>/attribution.{json,csv}` und
`strategy/<name>/attribution.{json,csv}`; das Manifest `comparison.json`
enthält kind/name/json/csv. Exportleser müssen diese Pfade berücksichtigen.

[Profilbericht #65](29_M4_EXPORT_PROFILE.md) mit ausführbarem Benchmark und
Vorher-/Nachher-Rohdaten: vollständige Vermögensberechnungen in reiner
Attribution 641/3201/6401 → jeweils 1 für 20/100/200 Pfade. Im Vergleichsexport
5898/29418/58818 → jeweils 12; Reconciliations 4172/20812/41612 → jeweils 12.
Alle Attributionsfelder und je Fall sämtliche 18 numerischen Exportdateien
sind identisch zur Referenz. Beschreibbare Arrays bleiben zwischen Aufrufen
aktuell, kein globaler Cache. Profilerzeiten sind keine Laufzeitgarantie.

## Technische Gesamtverifikation und Releasegate

Abschlussstand enthält main `3764550` (M5-Planung, PR #82). Die beiden
Dokumentationskonflikte in Entscheidungen/Abhängigkeiten sind unter Erhalt
beider Inhalte auf dem Milestone gelöst (`de85429`). Keine TUI implementiert.
pyproject.toml/uv.lock stehen auf 0.3.1; keine Dependency-Version verändert.

Frische gelockte macOS-Umgebungen mit Python 3.13.5, NumPy 2.5.3 und SciPy
1.18.1; vorhandene alte .venv nicht als Nachweis verwendet. Vollprofil mit
plots/yahoo: **423 Tests ohne Auslassungen**. Basis-/Dev-Profil ohne Extras:
**417 Tests, genau sechs optionale Diagrammtests übersprungen**; Matplotlib,
pandas/yfinance fehlen tatsächlich. Numerischer Kern und vier Offline-CLIs
werden zusätzlich unter blockierten optionalen Imports geprüft.
ruff check/format, striktes mypy (22 Quellmodule), git diff --check erfolgreich.
Wheel und Quelldistribution mit gecachtem hatchling 1.27.0 offline gebaut.

```sh
uv sync --locked --offline --extra plots --extra yahoo
python -m pytest --junitxml=/tmp/m4-release-full.xml
python -m ruff check .
python -m ruff format --check .
python -m mypy src/finance_toolkit
git diff --check
uv build --offline
```

Hier bezeichnet python den Interpreter der frischen Vollumgebung. Das
separate Basisprofil verwendet ebenfalls eine frische UV_PROJECT_ENVIRONMENT.
Wheel-Abnahme: neue Umgebung, gehashte gelockte Abhängigkeiten, Installation
des 0.3.1-Wheels ohne editable/src-Pfad, kopierte Tests unter /tmp sowie M1-,
Risk-, Hedge- und Index-Lab mit Diagrammen außerhalb des Repositorys.
Ergebnis: ebenfalls **423 Tests ohne Auslassungen**, alle vier Offline-CLIs
mit Diagrammen erfolgreich. Version 0.3.1, Importort in der frischen
Wheelumgebung und py.typed geprüft.

CI prüft Vollprofil/Paketbau/Wheel-Smokes auf Python 3.11–3.13 sowie Basisprofil
ohne Extras auf 3.13; Vollprofil darf keinen Test überspringen. Beispiel für
integrierten Funktionsstand 9c1a256:
[Run 38398616756](https://github.com/maschin96/FinanceToolkit/actions/runs/38398616756).
Aktuelle Abschluss-PR-/Milestone- und tatsächliche main-Zielcommit-CI werden
in [#66](https://github.com/maschin96/FinanceToolkit/issues/66) verlinkt;
lokale 3.13-Prüfungen ersetzen diese Matrix nicht.

Release-PR erst nach vollständiger Verifikation ausdrücklich nach main.
Nach Merge erfolgreiche CI am tatsächlichen main-Zielcommit abwarten; erst
danach v0.3.1 taggen und Wheel/Quelldistribution dieses Commits im öffentlichen
[Release](https://github.com/maschin96/FinanceToolkit/releases/tag/v0.3.1)
veröffentlichen. #66/M4 erst nach vollständigem Veröffentlichungsabschluss
schließen. [Release-Prozess](09_RELEASE_PROCESS.md). Keine PyPI-Veröffentlichung.

## Grenzen

Numerisch verifiziert, keine empirische Marktvalidierung. Modelle, Einheiten
und M1–M3-Grenzen bleiben erhalten: keine Kalibrierung, FX, Margin, Broker,
Steuern, amerikanischen Optionen oder neuen Corporate-Action-Modelle.
Keine erneute Live-Yahoo-Prüfung und kein aktueller CVE-/Lizenzrechtsaudit.
Konservative Ablehnung extremer nicht darstellbarer Zwischenwerte ist möglich;
endliche Eingaben garantieren keine darstellbaren Ergebnisse. Fehlendes
unabhängiges Review bleibt eine transparente Prüflücke.
