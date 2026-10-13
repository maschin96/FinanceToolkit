# M4 – Profilnachweis für lokale Ergebniswiederverwendung (#65)

`attribute_book` berechnet Vermögen nun einmal je Aufruf. Der Vergleichsexport
verwendet je Buch ein lokales Vermögensarray für CSV-Zeilen; die Ledger-Schleife
liest ihre Pfadanzahl aus der Mengenform. Das Profil zeigte zusätzlich eine
wiederholte P&L-Reconciliation je Attributions-CSV-Zeile: `export_attribution`
berechnet diese nun einmal und verwendet sie für JSON und CSV. Kein globaler
Cache auf den beschreibbaren `BookPaths`-/`Attribution`-Arrays. Ein späterer
Aufruf liest weiterhin aktuelle Arrays; kein neues Exportformat oder Modell.

## Reproduktion und Referenz

```sh
uv sync --locked --extra plots --extra yahoo
uv run --no-sync python benchmarks/profile_book_exports.py --output /tmp/m4-profile.json
```

Das Skript erzeugt exakte synthetische GBM-Pfade mit S0=100, Drift 0,02,
Volatilität 0,2, Horizont 1 Jahr, 16 Schritten (17 Rasterpunkte), Seed 314 und
je 20/100/200 Pfaden. Die reine Attribution nutzt eine Aktie und Kapital 1000,
ohne Kosten/Zinsen. Der Export nutzt den regulären ungehedgten Vergleich plus
die fünf eingebauten Strategiekontrollen. Konstruktion/Simulation liegen
außerhalb des Profils; gemessen wird jeweils der einzelne Verarbeitungsaufruf
mit cProfile. Keine Zeitgrenze in Unit-Tests.

Vorher: M4-Referenz `4428ae7`, unveränderte numerische Export-/Attributionspfade.
Danach: Refactoring in Issue #65, auf M4 mit integriertem #64 (`2621a61`). Die
CLI-Korrektur #64 verändert die profilierten numerischen Funktionen nicht.
Messumgebung: Python 3.13.5, NumPy 2.5.3, macOS 27.0.1 arm64, gelockte Extras.
[Rohprofil vorher](../benchmarks/results/m4_before.json),
[Rohprofil nachher](../benchmarks/results/m4_after.json).

## Beobachtete Aufrufe

| Pfade | Vermögen / reine Attribution vorher → nachher | Vermögen / Vergleichsexport vorher → nachher | Reconciliation / Vergleichsexport vorher → nachher |
| --- | --- | --- | --- |
| 20 | 641 → 1 | 5898 → 12 | 4172 → 12 |
| 100 | 3201 → 1 | 29418 → 12 | 20812 → 12 |
| 200 | 6401 → 1 | 58818 → 12 | 41612 → 12 |

Die zwölf Vermögensberechnungen sind je sechs Bücher einmal für Wealth-CSV
und einmal in deren Attribution. Die zwölf Reconciliations sind je Buch einmal
für die Bilanzprüfung und einmal für den gemeinsamen JSON-/CSV-Export. Beide
Zahlen hängen nicht mehr von Pfaden oder Exportzeilen ab; die Property bleibt
eine aktuelle Berechnung und wird nicht auf dem Ergebnisobjekt gecacht.

| Pfade | Reine Attribution Sekunden vorher → nachher | Vergleichsexport Sekunden vorher → nachher |
| --- | --- | --- |
| 20 | 0,006186 → 0,000276 | 0,688606 → 0,578759 |
| 100 | 0,034987 → 0,000510 | 3,963745 → 2,860462 |
| 200 | 0,091418 → 0,000886 | 9,304423 → 5,706767 |

Einzelmessungen unter Profiler, keine allgemeine Laufzeitgarantie. Die belastbare
Aussage ist die beseitigte vollständige Neuberechnung innerhalb der Schleifen.
Options-Greek-Auswertung und Serialisierung bleiben Teil des Exportaufwands.

## Verhaltensnachweis

Alle Attributionsfelder einschließlich relativer P&L, Events, Approximation
und Reconciliation stimmen pro Pfadfall per SHA256 mit der Referenz überein.
Je Fall sind zusätzlich sämtliche 18 CSV-/JSON-Exportdateien byteidentisch.
Referenzen werden nicht neu gesetzt, um numerische Änderungen zu verdecken.

Bestehende 38 Attributions-/Hedge-Lab-Tests vor Umbau grün; ergänzte Abdeckung
für Null-/negative Anfangsbasen und spätere Änderungen beschreibbarer Arrays
vor Umbau grün (40 Tests), danach erneut grün. Handfall: Aktie zu 100 auf Kredit,
Spots 100/90/100/120/110: Equity 0/-10/0/20/10 und relative P&L
null/null/null/-0,5. Nach späterer Cashänderung werden Quotienten neu berechnet;
dimensionslose Rundungstoleranz 1e-14. CSV/JSON führen null-Basen unverändert.
Bestehende Währungs-/Konvergenz-/Bilanztests und Toleranzen unverändert.
