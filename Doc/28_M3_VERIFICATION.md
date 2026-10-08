# M3-Gesamtverifikation – 0.3.0 (#47)

## Pflichtumfang

| Issue | Ergebnis | Integrierter PR nach milestone-m3 |
| --- | --- | --- |
| #39 | Dynamisches Optionsbuch | #48 |
| #40 | Explizite Finanzierung und Aktien-Shorts | #49 |
| #41 | Verzögertes Delta-Hedging | #51 |
| #42 | Optionsstrategie-Baukasten | #50 |
| #43 | P&L-Reconciliation und Greek-Näherung | #52 |
| #44 | Gekoppelte Hedge-/Strategievergleiche | #54 |
| #45 | Optionaler Yahoo-Adapter und Offline-Replay | #53 |
| #46 | Eigene Kurs-/Total-Return-Indizes | #55 |

Alle Funktions-Issues wurden nach grüner aktueller CI und eigenem Diff-Review
integriert und explizit geschlossen. Kein unabhängiger Reviewer verfügbar;
keine externe Freigabe behauptet. HTML-Bericht G ist nicht beauftragt.
M2 ist über PR #38 in main integriert; dessen Zielcommit-CI ist erfolgreich:
[Run 37753366082](https://github.com/maschin96/FinanceToolkit/actions/runs/37753366082).
M2-Tag und öffentliche Pakete: [v0.2.0](https://github.com/maschin96/FinanceToolkit/releases/tag/v0.2.0).

## Wissenschaftliche Nachweise und TDD

Die Issue-PRs dokumentieren Red–Green–Refactor: fehlende Module/APIs zunächst
rot, Implementierung und betroffene Tests danach grün. Zusätzlicher Yahoo-
Quotezeit-Schemafehler wurde vor Korrektur mit Regression reproduziert.
Dieses Abschlussarbeitspaket aktualisiert Dokumentation, Paketversion und CI;
kein neues numerisches Verhalten, daher kein künstlicher Red-Test.

- [Optionsbuch/Finanzierung](21_M3_BOOK.md): unabhängige Cash-/Mengenbilanz,
  Teilverkauf, Long/Short, Fälligkeiten, exponentielle Guthaben-/Kreditzinsen,
  linke Intervallbewertung der Aktienleihe. 1e-10 Währung absolut und 1e-14
  relativ bei Kapitalgrößen um 1000; Ereignismengen exakt.
- [Optionsstrategien](22_M3_OPTION_STRATEGIES.md): algebraische stückweise
  Terminal-Payoffs, Multiplikatoren, Grenzen und Prämien einschließlich Cash.
- [Hedging](23_M3_HEDGING.md): Delta-Handreferenz, verzögerte Ausführung,
  Prefix-Invarianz und Settlement. 1000 gekoppelte risikoneutrale GBM-Pfade,
  Seed 314, S=K=100, sigma=.2, T=1, Nullkosten/Nullzinsen: RMS bei 128
  Schritten unter 70% des 16-Schritt-RMS. Fein/grob verwenden dieselben Pfade.
  Cash 1e-10 Währung, Greek-Referenz 1e-12 Aktienäquivalente.
- [Attribution](24_M3_ATTRIBUTION.md): exakte Intervallbilanz mit Execution,
  Gebühren, Leihe, Finanzierung und einmaligem Settlement; kleinere Taylor-
  Reste bei halbierten Schocks. 1e-10 Währung bei kleinen Handreferenzen,
  zusätzlich 1e-12 relativ bei großen Buchwerten. Ereignisrest explizit.
- [Vergleiche](26_M3_HEDGE_LAB.md): gemeinsames Kapital, Optionsposition und
  Basispfade; grobe Raster sind Teilfolgen. CSV/JSON gegen Kernresultate,
  Seed-Doppellauf identisch, PNGs und vollständige Ledger kontrolliert.
- [Indizes](27_M3_CUSTOM_INDICES.md): rationale unabhängige Stückzahl-/Beitrags-
  referenzen, verzögertes Rebalancing, Basis-/Prefix-Invarianten, Kalender und
  Corporate-Action-Konventionen. 1e-12 Indexpunkte absolut, 1e-14 relativ bei
  Leveln 100–250; Beiträge 1e-14. Kein doppelter Split-/Dividendeneffekt.

Toleranzen decken dokumentierte Einheiten, Größenordnung und Rundung ab;
keine nachträgliche Aufweitung. M1-/M2-Referenzen bleiben Teil der Gesamtsuite.
Exakte GBM-Schritte und analytische BSM-Preise benötigen keinen Euler-Test;
das tatsächlich diskretisierte Hedging hat einen gekoppelten Konvergenztest.

## Daten, Lizenzen und Live-Smoke

Alle Test-Fixtures sind originale synthetische Hand-/Providerreferenzen,
keine privaten Marktdaten. Unit-Tests verwenden injizierte Provider/Clock/Sleep,
feste Seeds und keinen Netzwerkzugriff. Cache und Downloads werden ignoriert.
[Abhängigkeiten/Lizenzen](10_DEPENDENCIES.md), [Yahoo-Vertrag](25_M3_YAHOO.md)
und ADR-007 ff. in [Entscheidungen](07_RISKS_AND_DECISIONS.md) dokumentieren
Einheiten, Zeit, Finanzierung und Adjustierung. Keine neue Pflichtabhängigkeit;
yfinance[repair] 1.7.0 ist optional und gelockt. Softwarelizenzen erteilen
keine Yahoo-Marktdatenrechte.

Separater dokumentierter Live-Smoke am 2026-10-08 10:32:51–10:32:52 UTC:
AAPL/MSFT, Daily 2026-09-28 bis exklusiv 2026-10-08, Timeout 8s, null Retries,
je acht Bars und beide regulären Quotes erfolgreich. Vorheriger Quote-
Schemafehler und Regression sind im Yahoo-Vertrag festgehalten. Dieser Nachweis
prüft damaligen Adapterzugriff, keine dauerhafte Verfügbarkeit oder empirische
Modellvalidierung. Keine Live-Datenwerte werden eingecheckt.

## Technische Verifikation und Release

Lokal macOS/Python 3.13: 295 Tests ohne Auslassungen mit plots/yahoo,
ruff check/format und striktes mypy erfolgreich. Vor Änderungen ebenfalls
295 Tests grün. Die vorhandene lokale .venv enthielt unvollständige alte
Installationsmetadaten; Abschlussprüfung in frischer temporärer Umgebung. Paketversion und uv.lock sind auf 0.3.0 aktualisiert.

```sh
uv sync --locked --extra plots --extra yahoo
uv run --no-sync python -m pytest
uv run --no-sync python -m ruff check .
uv run --no-sync python -m ruff format --check .
uv run --no-sync python -m mypy src/finance_toolkit
git diff --check
uv build
```

CI prüft Python 3.11–3.13, alle 295 Tests, Qualität, Paketbau und frische
Wheel-Installation mit gehashten Abhängigkeiten außerhalb des Quellbaums.
M1-, Risk-, Hedge- und Index-Lab laufen offline mit Diagrammen sowohl im
Quellbaum als auch aus dem Wheel. Indexdemo verwendet die explizite synthetische
Konfiguration, niemals Live-Daten. Installation prüft Version und py.typed.
Aktuelle PR-, Milestone- und main-Zielcommit-CI sowie Release-Artefakte werden
in Issue #47 verlinkt; lokale Prüfungen ersetzen diese Matrix nicht.

Vor Release wird main in milestone-m3 übernommen, erneut geprüft, dann der
Release-PR nach main integriert. Erst nach erfolgreicher tatsächlicher main-CI
werden v0.3.0 und öffentliche Wheel-/Quelldistributionsartefakte veröffentlicht und
#47/M3 geschlossen. Keine PyPI-Veröffentlichung.

## Grenzen

GBM/BSM, europäischer Barausgleich und flache ausfallfreie Anleihen bleiben.
Keine Margin, Brokeranbindung, FX, Steuern, Kalibrierung, amerikanischen Optionen,
empirischen Backtests oder dynamische Indexmitgliedschaft. Aktien-Shorts/Kredite
sind explizite Modellfreigaben, keine Zusage tatsächlicher Handelsmöglichkeit.
Greek-Näherung ist lokal und nicht kausal eindeutig; Fälligkeiten sind Ereignisse.
Yahoo-Adjustierung ist Providerkonvention, keine unabhängige Corporate-Action-
Validierung; Quotes können verzögert sein. Gemeinsame Indexwährung ist Pflicht,
Kalender-intersection explizites Opt-in. Numerisch verifiziert, nicht empirisch
validiert. Speicher-/Exportbedarf wächst mit Pfaden, Zeiten und Positionen.
