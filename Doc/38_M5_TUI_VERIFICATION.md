# M5 – Gesamtverifikation und Freigabestand (#81)

Stand 2026-10-15. **Noch kein Release v0.4.0.** Alle funktionalen Pflichtpakete
A–G sind integriert; manuelle Terminal-Smokes stehen aus. Der Eigentümer hat
dieses Gate ausdrücklich beibehalten. #81 und M5 bleiben offen, main enthält
weiterhin das freigegebene M4/v0.3.1. Der Verifikationsbranch bereitet Paketversion
0.4.0 vor, veröffentlicht aber weder Tag noch Release. Keine PyPI-Veröffentlichung.

## Implementierung und TDD-Nachweise

| Paket | Issue / integrierter PR | Nachweis |
| --- | --- | --- |
| A: Konfiguration, optionales Extra, Einstieg | #74 / #87 | [Verträge](31_M5_TUI_CONTRACTS.md) |
| B: Navigation und begrenzte Jobs | #75 / #88 | [Jobs](32_M5_TUI_JOBS.md) |
| C: GBM/Portfolio und Tradeeditor | #76 / #89 | [Portfolio](33_M5_TUI_PORTFOLIO.md) |
| D: Risiko und Stress | #77 / #90 | [Risiko](34_M5_TUI_RISK.md) |
| E: Strategien/Hedges/Attribution | #78 / #91 | [Strategien](35_M5_TUI_STRATEGIES.md) |
| F: Index-/Datenansicht | #79 / #92 | [Indizes](36_M5_TUI_INDICES.md) |
| G: Workspaces und vollständige Exporte | #80 / #93 | [Workspaces](37_M5_TUI_WORKSPACES.md) |

Jeder Paketbericht hält beobachtete Red-/Green-Nachweise und Referenzen fest.
Die Issues sind nach grüner aktueller CI und Integration in M5 ausdrücklich
mit PR-Verweis geschlossen. Keine offenen Review-Anmerkungen bei Integration;
Eigenreview, kein unabhängiger Reviewer verfügbar. Der H-Beitrag ergänzt
Dokumentation, Versionsmetadaten und Start-/Beendennachweise für beide
Einstiege über einen echten POSIX-Terminaltreiber. Keine neue Produktfunktion,
daher kein künstlicher Red-Test. Die anfänglich blockierende Testausgabe wurde
im Testaufbau durch laufendes Lesen des Terminalpuffers korrigiert.

## Automatisierte Verifikation

Lokal macOS, Python 3.13.5, derselbe uv.lock:

| Profil | Ergebnis | Erlaubte Auslassungen |
| --- | --- | --- |
| tui/plots/yahoo | 495 bestanden | keine |
| Kern ohne Extras | 476 bestanden | zwölf UI-, sieben Diagrammtests |
| tui ohne plots/yahoo | 488 bestanden | sieben Diagrammtests |

`python -m pytest`, `python -m ruff check .`,
`python -m ruff format --check .`, `python -m mypy src/finance_toolkit` (strict,
34 Module), `git diff --check` und `uv build` sind am H-Stand lokal bestanden.
Relative Dokumentationslinks sind geprüft. CI prüft das Vollprofil auf Python
3.11–3.13 unter Ubuntu 24.04 sowie beide reduzierten Profile auf 3.13.
Jeder Skipname und dessen Anzahl wird aus dem Testbericht geprüft;
Replay-/Provider-Fakes sind in keinem Profil als optionale Netztests ausgenommen.
[PR #93 CI](https://github.com/maschin96/FinanceToolkit/pull/93/checks)
war vor Integration vollständig erfolgreich, einschließlich Wheelprüfungen.

Wheel/Quelldistribution werden mit dem gelockten Buildbackend erzeugt.
Die CI installiert das Wheel samt separat installierten Test-/Laufzeitpaketen
in einer frischen Umgebung, kopiert die Tests nach /tmp und führt sie dort
außerhalb des Quellbaums aus. Das enthält den kompletten Headless-Ablauf
Ändern/Rechnen/Speichern/Laden/erneut Rechnen/Export mit voller Präzision.
Modul-/Konsolenhilfe, tatsächlicher Prozessstart samt Ctrl+Q über einen
automatisierten POSIX-Terminaltest werden gesondert geprüft. Alle vier bisherigen
Offline-CLIs werden zusätzlich mit Diagrammen ausgeführt. Kein editable- oder src-Pfad als Wheelnachweis.
Lokal: frisches Wheel 0.4.0 in `/tmp/finance-m5-final-wheel`, 493 Fälle der
Gesamtsuite und anschließend die zwei ergänzten Prozessstartfälle bestanden;
Importpfad und Versionsmetadaten geprüft. Alle vier Offline-CLIs erzeugten
CSV/JSON/PNG. Die aktuelle CI führt alle 495 Fälle zusammen auch im Wheel aus.

## Fachliche Erwartungen und Grenzen

Die TUI leitet Konfigurationen an dieselben öffentlichen APIs weiter. Exakte
Arraygleichheit prüft diese Durchleitung und JSON-Roundtrips, keine unabhängige
Approximation. Zusätzlich bleiben alle analytischen Cashflow-/Paritäts-/
Bilanzreferenzen aus M1–M4 verpflichtend. Neue Adapterreferenzen: Prozentwerte
einmalig umgerechnet; path/time-Snapshots post-event; Nullkupon-DV01;
additive hypothetische Schocks gegen vollständige Neubewertung; unabhängige
Indexlevel/Beitragsbilanzen; Rebalancing-/Hedgekosten und P&L-Reconciliation.
Einheiten und vorab begründete absolute/relative Toleranzen stehen in den
Paketberichten und Tests. Keine nachträgliche Toleranzaufweitung oder deaktivierte
Tests. Bestehende Hedge-/gekoppelte Rasterkonvergenz läuft in der Gesamtsuite.
M5 verändert keine numerischen Verfahren, daher kein neues Zeitverfahren zu prüfen.

Verifiziert bedeutet implementierte Gleichungen und Adapterverträge geprüft;
keine empirische Marktvalidierung. Keine realen Yahoo-Abrufe als Testbeweis,
keine Echtzeit-, FX-, Margin-, Broker- oder Windows-Zusage. Ein laufender
Kernthread kann nach Escape/Beenden weiterlaufen; spätere Rückgabe wird verworfen.
Exportschutz behandelt reguläre Schreibfehler und Abbruch; keine garantierte
Dateisystemtransaktion bei Stromausfall. Numerische Ergebnisse werden vollständig,
Terminaltabellen begrenzt angezeigt.

## Verbleibende Freigabeschritte

1. Die [manuelle Prüfanleitung](39_M5_MANUAL_SMOKE.md) unter macOS und Linux
   jeweils bei 80×24 und 120×40 tatsächlich durchführen und protokollieren.
   Die Computersteuerung sperrt den Zugriff auf die Terminal-App; deshalb ist
   dieser Nachweis derzeit nicht erbracht. Automatisierte Tests zählen nicht
   als manuelle Prüfung.
2. Nach ggf. erforderlichen Korrekturen main erneut in M5 übernehmen und die
   resultierende CI/Reviews prüfen. Abgleich am 2026-10-15: main
   `0b39f06d32b368d10c0c2db656e56c7b618d065f` ist bereits Vorfahr von M5
   `3fad3b6831de78408c8efd86c69712ffddb3ac51`; keine fehlenden main-Änderungen.
3. Erst bei vollständiger Abnahme Release-PR nach main; nach Merge CI am
   tatsächlichen main-Zielcommit prüfen, dann v0.4.0 taggen und öffentliche
   Wheel-/Quelldistribution mit SHA-256-Prüfsummen veröffentlichen.
4. Release-Artefakte/Tag prüfen; erst anschließend #81 und M5 schließen.

[Release-Prozess](09_RELEASE_PROCESS.md), [Architekturentscheidungen](07_RISKS_AND_DECISIONS.md),
[Abhängigkeiten/Lizenzen](10_DEPENDENCIES.md). Ein lokaler oder integrierter
Vorbereitungscommit erfüllt den vollständigen Releaseauftrag noch nicht.
