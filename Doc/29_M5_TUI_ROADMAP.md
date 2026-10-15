# M5 – FinanceToolkit Textual-TUI

Planungsstand: **2026-10-13**. [Planungsissue #73](https://github.com/maschin96/FinanceToolkit/issues/73),
[Milestone M5](https://github.com/maschin96/FinanceToolkit/milestone/6).
Zielrelease: **v0.4.0**, ohne zugesagten Termin. Textual ist vom Eigentümer
bestätigt. Dieser Text hält die ursprüngliche Planung fest.
Aktualisierung 2026-10-15: A–G sind integriert;
[Gesamtverifikation und verbleibende Release-Gates](38_M5_TUI_VERIFICATION.md).
Voraussetzung für die Umsetzung: M4/v0.3.1 vollständig abgeschlossen
([#66](https://github.com/maschin96/FinanceToolkit/issues/66)) und stabil in main.

## Produktziel und Nutzerablauf

Eine zusammenhängende Terminal-App erschließt den bestehenden Toolkit-Umfang
ohne selbst geschriebenen Python-Code: Markt und Portfolio konfigurieren,
Simulation starten, Ergebnisse und Risiken prüfen, Strategien unter gleichen
Bedingungen vergleichen und den Lauf reproduzierbar speichern/exportieren.
Der numerische Kern bleibt die einzige Quelle für Bewertung und Kennzahlen.

Der erste durchgehende Ablauf ist offline: Demo laden → Seed/Parameter ändern →
Aktien, Protective Put und Anleihe konfigurieren → berechnen → Vermögen/Cash und
Risiken prüfen → Stress vergleichen → Konfiguration und CSV/JSON speichern.
Weitere Abläufe vergleichen Rebalancing und Delta-Hedges oder berechnen einen
eigenen Index aus synthetischen Daten, Yahoo-Cache-Replay oder explizitem Abruf.

## Bedienung und Ansichten

| Ansicht | Eingaben und Ergebnis |
| --- | --- |
| Start / Demo | Offline-Vorlagen, zuletzt explizit gespeicherte Konfiguration öffnen, Hilfe |
| Simulation / Portfolio | Korrelierte GBM-Assets, Seed/Raster, Einzelinstrumente, Positionen/Trades, Cash/Finanzierung; Pfad-/Zeitwahl und Vermögensverlauf |
| Risiko / Stress | Bewertungs-Snapshot, Positions-/Asset-Greeks, DV01/Konvexität, VaR/ES, Drawdown und benannte Schocks samt Stressraster |
| Strategien / Hedging | Buy-and-Hold/Rebalancing, Optionsstrategien, dynamisches Buch, Hedgevarianten, Kosten/Restdelta und Attribution |
| Indizes / Daten | Ticker/Gewichte/Basis/Kalender, Preis-/Total-Return-Index und Beiträge; optionale Quotes/Historien und Cache-Replay |
| Workspace / Export | Versionierte JSON-Konfiguration, erneute Rechnung, vollständige CSV/JSON-Resultate, optionale Diagrammexporte |

Tastatur ist der vollständige Bedienweg: Tab/Shift-Tab wechseln Felder, Enter
aktiviert, Escape schließt einen Dialog, Hilfe erklärt Kürzel und Einheiten.
Ein sichtbarer Fokus, Fehler am Feld und ein Statusbereich gehören zur Abnahme.
Mausbedienung kann ergänzen. Sprache zunächst Deutsch mit etablierten
Finanzbegriffen; Internationalisierung ist kein M5-Pflichtpaket.

80×24 und 120×40 sind verpflichtende Testgrößen. Formulare und Tabellen sind
scrollbar; kleinere Terminals erhalten einen Hinweis und eine Beenden-Funktion.
Mindestens ein beschrifteter Terminal-Verlauf zeigt die gewählte Reihe; Anzeige
großer Arrays erfolgt ausschnittsweise, nicht durch Millionen Tabellenzeilen.
Plots sind für Bedienung und numerische Exporte nicht erforderlich.

## Abdeckung durch vorhandene APIs

| Toolkit-Bereich | Bestehende API / Modul | TUI-Paket |
| --- | --- | --- |
| GBM, mehrere Assets und Korrelation | `simulation.simulate_gbm` | C |
| Europäische Optionen und Greeks | `instruments.options.black_scholes`, `option_payoff`, `option_greeks` | C, D |
| Anleihen / Zahlungszeitpunkte | `instruments.bonds.Bond`, `cashflows`, `price`, `accrued_interest` | C, D |
| Gemischtes Portfolio / Trades | `portfolio.value_portfolio`, `Stock`, `EuropeanOption`, `Trade` | C |
| Vermögen, P&L, Rendite, Drawdown, VaR/ES | `analytics.analyze_portfolio`, `tail_risk` | C, D |
| Exposures und Stress-Neubewertung | `risk.portfolio_exposures`, `bond_sensitivity`, `stress_portfolio`, `stress_grid` | D |
| Aktien-/Cash-Rebalancing | `strategies.simulate_rebalancing` | E |
| Dynamisches Buch / Finanzierung | `options_book.simulate_book`, `Order` | E |
| Optionsstrategien / Delta-Hedges | `option_strategies.build_strategy`, `hedging.simulate_hedge`, `hedge_lab.compare_hedges` | E |
| P&L-Attribution | `attribution.attribute_book`, `explain_option_move` | E |
| Eigene Indizes | `indices.calculate_index`, `index_lab.build_indices`, `demo_histories` | F |
| Optionale Marktdaten / Replay | `yahoo.YahooClient`, bestehende Provider-/Cache-Verträge | F |
| Lab-Resultate / Exporte | Bestehende Beispiele, Risk-/Hedge-/Index-Lab-Exporter | G |

Der TUI-Umfang übernimmt bestehende Modellgrenzen. Frei programmierte Callbacks
und sämtliche vektorisierten API-Sonderformen benötigen keinen eigenen Editor;
die vorhandenen Instrumente, Parameter und eingebauten Strategien müssen über
typisierte Konfigurationen erreichbar sein. Wiederverwendbare Lab-Logik darf
verhaltensneutral zugänglich gemacht werden; CLI-Argumente werden nicht geparst
oder über Subprozesse als Rechenkern aufgerufen.

## Architektur und Framework

Textual wird ein optionaler Adapter unter `src/finance_toolkit/tui/`.
Geplante Zuständigkeiten: Einstieg/App, Screens/Widgets, typisierte
Konfigurationen, Service-Adapter, Jobzustand und Persistenz/Export. Der Datenfluss
ist Formular → validierte Konfiguration → unveränderlicher Lauf-Snapshot →
öffentliche Toolkit-APIs → Ergebnis → Ansicht/Export. Der Kern importiert
keine UI-, Yahoo- oder Plotbibliothek; keine Formeln werden im UI dupliziert.

Textual bietet Widgets für Formulare/Tabellen, Worker für Hintergrundarbeit und
Headless-Bedienungstests mit `App.run_test()`/Pilot. Die Projektlizenz ist MIT.
Primärquellen, geprüft am 2026-10-13:
[Projekt](https://github.com/Textualize/textual),
[Lizenz](https://github.com/Textualize/textual/blob/main/LICENSE),
[Worker](https://textual.textualize.io/guide/workers/),
[Tests](https://textual.textualize.io/guide/testing/).
Konkrete Version, Python-3.11–3.13-Verträglichkeit und transitive Lizenzen werden
in A vor Dependency-Aufnahme geprüft. Die Planung ändert noch keinen Lockstand.

Geplant sind das Extra `tui`, der Konsolenstart `finance-toolkit-tui` und
`python -m finance_toolkit.tui`. Diese Aufrufe sind **noch nicht verfügbar**.
`plots` und `yahoo` bleiben getrennte Extras. Ohne `tui` erklärt der spätere
TUI-Einstieg die benötigte Installation ohne Traceback; Kern und alte CLIs laufen
weiter. Ohne `yahoo` funktionieren synthetische Daten und Cache-Replay.

## Fachliche Verträge und Ergebniszustand

- Zeit bleibt in Jahren, Raten annualisiert/dezimal, eine gemeinsame Währung.
  UI-Prozentwerte werden genau einmal konvertiert. Reale GBM-Drift und
  risikoneutrale Bewertung sowie Simulations-/Optionsvolatilität bleiben getrennt.
- Vorzeichen, Mengen, Optionsmultiplikatoren, Finanzierung, Gebühren und
  Signal-/Ausführungszeiten folgen den bestehenden API-Verträgen. Keine stillen
  Short-/Kreditfreigaben. Ein Raster muss relevante Ereignistermine enthalten;
  ansonsten konkrete Eingabefehler statt verschobener Cashflows.
- Nicht definierte relative Kennzahlen/Greeks erhalten eine Erklärung statt
  Nullwert. Absolute Ergebnisse bleiben sichtbar, soweit die Kern-API sie liefert.
  Stress-P&L und probabilistische VaR/ES werden unterschiedlich beschriftet.
- Ergebnisse gehören zu einer Lauf-ID und einem Konfigurationssnapshot.
  Parameteränderungen markieren sie als veraltet. Pro Workspace höchstens ein
  aktiver Rechenlauf; keine unbeschränkte Jobwarteschlange.
- Hintergrundarbeit hält Navigation, Hilfe und Abbruch bedienbar. Zustände sind
  idle/running/succeeded/failed/cancelled. Fortschrittsprozente erscheinen nur
  bei tatsächlich messbarem Fortschritt; sonst eine Aktivitätsanzeige.
- Thread-Abbruch ist kooperativ: Ein bereits laufender Kernaufruf kann zunächst
  weiterrechnen. Seine späteren Ergebnisse werden verworfen; kein Erfolgsexport.
  Jobgrenzen, Freigabe von Ressourcen und Verhalten beim Beenden sind in B zu
  testen. Keine erzwungene Threadbeendigung und keine UI-Mutation aus Workern.
- Große Arrays werden nur für die Darstellung reduziert. Exporte verwenden
  vollständige Rechenwerte und eindeutige Kategorie-/Buchnamen. M4-Korrekturen,
  insbesondere die Hedge-/Strategie-Exportpfade aus #59, sind Voraussetzung.

JSON-Konfiguration v1 speichert Parameter, Seed, Währung und Daten-/Cache-Referenzen.
Laden löst weder Netzwerk noch Rechnung aus; unbekannte Schemaversionen werden
abgelehnt. Gespeicherte Konfigurationen sind keine Python-Programme.
CSV/JSON-Ergebnisse enthalten Versionen, Einheiten und vorhandene Daten-/Pfadhashes.
Gleicher Seed und Abhängigkeitsstand liefern gleiche numerische Nutzdaten;
Abruf-/Laufmetadaten sind als zeitabhängig gekennzeichnet. Vor Überschreiben
bestehender Dateien erfolgt eine explizite Freigabe im App-Ablauf.

## Verpflichtende Arbeitspakete

P0 bezeichnet Grundlagen/Release-Gate, P1 Nutzerfunktionen. **Alle Pakete sind
Pflichtumfang**. Größen sind relative Komplexität, keine Zeit- oder Lieferzusage.
Die verlinkten Issues enthalten detaillierte Abnahmekriterien und Prüfpläne.

| Paket / Issue | Priorität | Ergebnis | Voraussetzung | Größe |
| --- | --- | --- | --- | --- |
| [A / #74](https://github.com/maschin96/FinanceToolkit/issues/74) | P0 | API-/UI-/Schema-Verträge, optionales tui-Extra und Startwege | stabiles, abgeschlossenes M4 | mittel |
| [B / #75](https://github.com/maschin96/FinanceToolkit/issues/75) | P0 | App, Navigation, Fokus, Jobzustände und Responsivität | A | groß |
| [C / #76](https://github.com/maschin96/FinanceToolkit/issues/76) | P1 | GBM, Einzelinstrumente, gemischte Portfolios und Offline-Demo | A, B | groß |
| [D / #77](https://github.com/maschin96/FinanceToolkit/issues/77) | P1 | Exposures, VaR/ES, Stress und terminales Stressraster | A, B, C | mittel |
| [E / #78](https://github.com/maschin96/FinanceToolkit/issues/78) | P1 | Rebalancing, Optionsbuch/-strategien, Hedging und Attribution | A, B, C, D | groß |
| [F / #79](https://github.com/maschin96/FinanceToolkit/issues/79) | P1 | Eigene Indizes, Offline-Demo, Yahoo-Opt-in und Replay | A, B | mittel |
| [G / #80](https://github.com/maschin96/FinanceToolkit/issues/80) | P1 | Konfigurations-Roundtrip und vollständige reproduzierbare Exporte | A–F | mittel |
| [H / #81](https://github.com/maschin96/FinanceToolkit/issues/81) | P0 | Gesamtverifikation, Anleitung und Release v0.4.0 | A–G | mittel |

Reihenfolge: A → B → kleiner vertikaler C-Durchstich → C → D → E → F → G → H.
F kann fachlich nach B beginnen; eine parallele Agentenbearbeitung ist nicht
vorausgesetzt. Schema und Adapterverträge aus A müssen vor den abhängigen
Implementierungen geklärt sein. Eine mit G kompatible minimale Exportgrenze
früh im C-Durchstich vorsehen; vollständige Persistenz folgt in G.

## Teststrategie und Release-Abnahme

Für ausführbares Verhalten gilt Red–Green–Refactor je Akzeptanzkriterium.
Formular-/Schema-/Jobtests sind deterministisch; feste Seeds, kontrollierte
Worker-Barrieren, synthetische Marktdaten, Provider-Fakes und temporäre Dateien
ersetzen Live-Netz und Timingannahmen. Pilot prüft Navigation, Formulare,
Resize, Berechnung, Fehler, Abbruch und Export aller Pflichtansichten.

TUI/API-Vergleiche prüfen Parameterdurchleitung, Auswahl und Exportpräzision.
Zusätzlich bleiben unabhängige finanzielle Erwartungen Pflicht: Cash-/Kupon-
und Kostenbilanzen, Put-Call-Parität, Nullkupon-DV01, Stress-Handrechnungen,
Indexlevel/Beiträge und Attributionsbilanz. Absolute/relative Toleranzen werden
vorab nach Einheit und Größenordnung begründet. Keine gelockerten Erwartungen.
Die bestehende Suite einschließlich Prefix-/Hedge-Konvergenznachweisen bleibt
grün. Neue Konvergenztests sind erforderlich, falls entgegen dem Adapterplan
numerische Verfahren oder Diskretisierung verändert werden.

Geplante Installationsprüfung: Kern ohne Extras; `tui` ohne `plots`/`yahoo`;
Vollprofil `tui`/`plots`/`yahoo` auf Python 3.11–3.13. Kernimporte und alle alten
Offline-CLIs bleiben unabhängig. Jedes Profil besitzt eine ausdrückliche
Skip-Namensliste: Kern nur optionale TUI-/Diagrammtests, TUI nur Diagrammtests,
Vollprofil keine Auslassungen. Replay-/Fake-Tests sind keine Online-Tests.

Vor Release: pytest, ruff check/format, striktes mypy, diff-Prüfung, Paketbau
und frische Wheelinstallation außerhalb des Quellbaums. Modul-/Konsolenstart
und Headless-Demo/Export sowie alte Offline-CLIs prüfen. Ein manueller
Tastatur-Smoke auf macOS und Linux bei beiden Testgrößen ergänzt Headless-Tests.
Windows-Unterstützung erst nach tatsächlichem Smoke behaupten. README,
Nutzeranleitung, CHANGELOG, Abhängigkeits-/Lizenzliste und Verifikationsbericht
müssen aktuell sein. Diese Prüfungen sind geplant, noch nicht ausgeführt.

## Nichtziele und Risiken

Keine neuen Finanzmodelle, Kalibrierung, empirisches Backtesting, Optimierung,
Brokerorders, Margin, FX, Steuern, Web-/Desktop-GUI oder PyPI-Veröffentlichung.
Keine neue HTML-Berichtspflicht aus M3. Numerische Verifikation bleibt von
empirischer Marktvalidierung getrennt; Yahoo-Daten haben keine Echtzeitgarantie.

Die größte Unsicherheit sind bedienbare Hintergrundjobs bei großen Arrays
sowie der Umfang der Strategieformulare. Der frühe C-Durchstich prüft diese
Architektur vor vollständigem Ausbau. Ressourcen-/Fortschrittsgrenzen sind in
A/B zu dokumentieren; keine harte Laufzeitgarantie ohne Messung. UI-Snapshots
ergänzen Verhaltenstests, ersetzen keine Abnahme. Framework-/Lizenzprüfung und
manuelle Terminal-Smokes bleiben explizite Umsetzungsgates.

## Integration und Status

Die Planungsdokumentation gehört zu Repository-Pflege auf
`codex/73-plan-textual-tui-m5` von stabilem main; ein Planungs-PR zielt nach main.
Sie führt keine M5-Funktionalität ein. #73 bleibt bis geprüfter Integration offen.

**Kein M5-Integrationsbranch bei bloßer Planung.** Erst nach vollständigem
M4-Abschluss und bei tatsächlichem Umsetzungsbeginn `codex/milestone-m5` vom
dann aktuellen stabilen main erstellen. Je Pflichtissue eigener Branch und PR
zurück nach milestone-m5; CI und Review-Anmerkungen am aktuellen Stand klären.
Fehlendes unabhängiges Review transparent benennen.

Erst bei vollständigem Pflichtumfang main in milestone-m5 übernehmen, erneut
prüfen und Release-PR nach main erstellen. Nach Merge die tatsächliche
main-Zielcommit-CI prüfen, danach v0.4.0 taggen und öffentliche Wheel-/Quell-
artefakte veröffentlichen. Funktionsissues explizit mit PR-Verweis schließen;
#81 und M5 bleiben bis zum vollständigen Releaseabschluss offen.
[Release-Prozess](09_RELEASE_PROCESS.md). Keine Terminverpflichtung und kein
automatischer Umsetzungs- oder Veröffentlichungsauftrag durch diese Planung.
