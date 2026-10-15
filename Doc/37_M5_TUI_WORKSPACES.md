# M5 – Workspaces und Exporte (#80)

Ctrl+6 bietet explizites Speichern/Laden einer JSON-Konfiguration v1 und den
Export des zuletzt erfolgreich berechneten, noch aktuellen numerischen Ergebnisses.
Datei- und Verzeichnispfade sind frei wählbar. Die gemeinsame Checkbox erlaubt
Überschreiben ausdrücklich; standardmäßig wird eine vorhandene Datei bzw. ein
vorhandenes Verzeichnis abgelehnt. Es gibt keine automatische Sitzungsdatei.

## Konfigurationen

Alle typisierten Workspace-Felder einschließlich Seed, Währung, Finanzierungs-
und Modellparametern, Orders, Szenarien, Hedgefällen und Cache-Referenzen werden
verlustfrei als JSON geschrieben. Laden prüft Schema, Typen und unbekannte Felder
vor dem Zustandswechsel. Fehlende/defekte Dateien erhalten eine konkrete Meldung;
der bisherige Workspace bleibt erhalten. Maximale Ladegröße: 2 MiB.
Laden markiert vorhandene Ergebnisse als veraltet und startet weder Rechnung
noch Providerzugriff. Erst die nächste Rechenaktion verwendet die neuen Parameter.
Bei gleichem Seed und Abhängigkeitsstand entstehen wieder dieselben GBM-Pfade.

## Vollständiger Export

`result.json` enthält vollständige numerische Arrays und Kennzahlen, nicht die
begrenzten oder gerundeten Terminaltabellen. `parameters.json` hält die exakte
Konfiguration; Python-/Toolkit-/Abhängigkeitsversionen, Einheiten und Pfad-/
Datenhashes stehen im Ergebnis. `arrays.csv` enthält alle Arraywerte mit
JSON-Feldpfad und Index, `export_manifest.json` deren Formen/Datentypen sowie
SHA-256-Hashes der erzeugten Dateien. `volatile_metadata` trennt Abrufzeiten
von numerischen Nutzdaten. Die Indexpayloads behalten ihre tatsächliche Währung;
die Portfolio-Währung bedeutet keine FX-Konversion.

Vorhandene Lab-Verträge bleiben erhalten: Portfolio-Wealth/Risk, Risk-Lab-
Wealth/Stress/Grid, Hedgevergleich und Attribution unter eindeutigen Pfaden
`hedge/<name>`, `strategy/<name>` und `dynamic/scheduled`, sowie Index-CSV/JSON.
Undefined Returns bei nichtpositivem Anfangskapital bleiben leer/None.
Exportiert wird der ausgewählte Risiko-Snapshot mit seinem konfigurierten Raster.
Die Dateiausgabe benötigt kein plots-/yahoo-Extra. Optionale Diagramme werden
nur per Checkbox angefordert; fehlende Abhängigkeiten liefern einen Fehler,
wonach ein numerischer Export ohne Diagramme möglich bleibt.

## Fehler, Abbruch und Überschreiben

Der Export läuft im selben begrenzten Hintergrundjob wie die Rechnungen.
Zunächst werden alle Dateien in einem separaten Verzeichnis vorbereitet.
Abbruch, Eingabeänderung oder Schreibfehler vor Veröffentlichung erzeugen keinen
neuen vollständigen Export. Ein bereits veröffentlichter Export wird nicht
nachträglich als abgebrochen bezeichnet. Die kurze Verzeichnisveröffentlichung
ist gegen gleichzeitigen Abbruch gesperrt. Bestehende Ziele werden erst nach
vollständiger Vorbereitung ersetzt; bei einem fehlgeschlagenen Austausch wird
das ursprüngliche Verzeichnis zurückgesetzt. Unbekannte, nicht kollidierende
Dateien werden erhalten; der Manifest-Hashumfang umfasst nur neu erzeugte Dateien.
Ein Stromausfall zwischen zwei Verzeichnisumbenennungen ist keine garantierte
Dateisystemtransaktion; temporäre Sicherungsverzeichnisse sind dann prüfbar.

Fehlgeschlagene/abgebrochene Rechenläufe können keine alten Ergebnisse exportieren.
Ein fehlgeschlagener Export kann mit korrigiertem Ziel/Überschreibfreigabe erneut
versucht werden, solange die zugrundeliegenden Rechenparameter unverändert sind.
F2 zeigt technische Fehlerdetails. Keine Netzabfrage und keine erneute Simulation
beim Export; vorhandene Lab-Writer bewerten gegebenenfalls das Stressraster erneut.

## Verifikation

TDD: zunächst neun rote Fälle für fehlende Dateiverträge/UI/Jobschutz; anschließend
grün. Zusätzlicher roter Regressionstest für Konfigurationsänderungen während
eines Exports, danach zentraler Abbruch im Jobmanager. Finale elf Tests umfassen
exakte Roundtrips, fremdes Schema/fehlende Datei, vollständige CSV/JSON-Werte,
Überschreibschutz, Erhalt unbekannter Dateien, injizierten Veröffentlichungsfehler
mit Rollback, Abbruch, drei Lab-Verträge und optionales PNG. Der Pilotablauf
prüft Ändern → Rechnen → Speichern → ungültiges Laden ohne Zustandswechsel →
Laden ohne Rechnung → identischen Seed-Doppellauf → Export → Fehler → Retry.
Arraygleichheit ist hier exakt, weil dieselben gespeicherten Floatwerte bzw.
dieselben deterministischen Rechenschritte verglichen werden; keine unabhängige
numerische Approximation. Fachliche Referenzen bleiben in den Kern-/Lab-Tests.

Eigenreview; kein unabhängiger Reviewer verfügbar. Keine empirische Validierung.

Lokal macOS/Python 3.13.5: Vollprofil 493 bestanden; Kern 474 bestanden,
19 benannte Skips (zwölf UI-, sieben Diagrammtests); TUI-Profil 486 bestanden,
sieben Diagramm-Skips. ruff check/format, striktes mypy (34 Module),
git diff --check und Paketbau grün. Alle elf neuen Fälle zusätzlich im Wheel
außerhalb des Quellbaums geprüft. CI am aktuellen PR vor Integration abwarten.
