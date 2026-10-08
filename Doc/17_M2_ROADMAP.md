# M2 – Portfolio Risk Lab

Planungsstand: 2026-10-08. Planungs-Issue: [#20](https://github.com/maschin96/FinanceToolkit/issues/20).
Vorgesehenes Release: **v0.2.0**. M1/v0.1.0 ist veröffentlicht und Issue #9
geschlossen. Der Feature-Umfang ist auf `codex/milestone-m2` umgesetzt;
[Gesamtverifikation und Release-Stand](20_M2_VERIFICATION.md). Die Paket-IDs A–H sind den unten verlinkten GitHub-Issues zugeordnet.

## Produktziel

Ein Portfolio nicht nur bewerten, sondern seine Risiken erklären und Strategien
unter identischen Bedingungen vergleichen: Welche Position verursacht das Delta?
Was passiert bei einem Kurseinbruch mit steigender Volatilität? Lohnt sich
regelmäßiges Rebalancing nach Kosten?

Das Vorzeigebeispiel vergleicht ein Aktien-/Cash-Portfolio ohne Umschichtung,
kalenderbasiertes und schwellenbasiertes Rebalancing auf denselben GBM-Pfaden.
Ein separater Protective-Put-Vergleich zeigt Options-Exposures und Stressverluste.
CSV/JSON-Ergebnisse und optionale Diagramme machen die Rechnung nachvollziehbar.
Die Beispiele liefern Modellvergleiche, keine empirischen Anlageempfehlungen.

## Verpflichtende Arbeitspakete

Alle Pakete sind Release-Pflichtumfang. P0 bezeichnet Grundlagen, P1 die darauf
aufbauenden Nutzerfunktionen; P1 ist keine Erlaubnis zum Weglassen.

| Paket | Priorität | Ergebnis | Voraussetzung | Relative Größe |
| --- | --- | --- | --- | --- |
| [A / #21](https://github.com/maschin96/FinanceToolkit/issues/21) | P0 | Konventionen, API-Verträge und Referenzfälle | stabiles M1 | klein |
| [B / #22](https://github.com/maschin96/FinanceToolkit/issues/22) | P0 | Analytische Options-Greeks | [A / #21](https://github.com/maschin96/FinanceToolkit/issues/21) | mittel |
| [C / #23](https://github.com/maschin96/FinanceToolkit/issues/23) | P0 | Portfolio-Exposures und Anleihen-Zinssensitivität | [B / #22](https://github.com/maschin96/FinanceToolkit/issues/22) | mittel |
| [D / #24](https://github.com/maschin96/FinanceToolkit/issues/24) | P1 | Szenario-Stresstests mit vollständiger Neubewertung | [C / #23](https://github.com/maschin96/FinanceToolkit/issues/23) | mittel |
| [E / #25](https://github.com/maschin96/FinanceToolkit/issues/25) | P0 | Pfadabhängige Strategieausführung und Kostenbuchung | [A / #21](https://github.com/maschin96/FinanceToolkit/issues/21) | groß |
| [F / #26](https://github.com/maschin96/FinanceToolkit/issues/26) | P1 | Kalender- und Schwellen-Rebalancing | [E / #25](https://github.com/maschin96/FinanceToolkit/issues/25) | mittel |
| [G / #27](https://github.com/maschin96/FinanceToolkit/issues/27) | P1 | Risk-Lab-Beispiele und Exporte | D, F | mittel |
| [H / #28](https://github.com/maschin96/FinanceToolkit/issues/28) | P0 | Gesamtverifikation und Release v0.2.0 | B–G | mittel |

Die Größen sind erste Komplexitätseinschätzungen, keine Liefertermine. E ist das
größte Architekturrisiko und erhält nach A früh einen kleinen vertikalen Durchstich.

### A – Konventionen vor Implementierung

- Einheiten, Vorzeichen, Broadcasting und Grenzfälle der Greeks festlegen:
  Theta als Ableitung nach verstrichener Zeit pro Jahr; Vega/Rho pro Änderung
  um 1,0 der dezimalen Eingabe, zusätzlich eindeutig skalierte Anzeige je Prozentpunkt.
- Ableitungen an nicht differenzierbaren Grenzen explizit behandeln; keine
  stillschweigenden Nullwerte für undefinierte Greeks.
- Stress auf einen Portfolio-Snapshot beziehen: gleicher Bewertungszeitpunkt,
  gleiche Bestände und gleicher Cashbestand, keine zwischenzeitlichen Trades.
  Bestehende Zahlungsreihenfolge und ex-Zahlungsbewertung erhalten.
- Rebalancing zunächst auf Aktien und Cash begrenzen: Long-only, Zielgewichte
  nichtnegativ, Summe höchstens eins; Rest ist Cash. Bruchstücke erlaubt,
  keine Kreditaufnahme, keine Dividenden oder externen Kapitalflüsse.
- Signal, Ausführung, Gebühren, Finanzierung und Vergleichsbasis im ADR festlegen.
  Signal nach Ereignissen am Zeitpunkt t, Ausführung am nächsten Rasterpunkt;
  nur bis t bekannte Preise/Bestände verwenden. Letztes Signal erzeugt keinen Trade.

Abnahme: dokumentierte API-Verträge und handgerechnete Referenzfälle für alle
Folgepakete; offene fachliche Fragen vor davon abhängiger Implementierung klären.
Die Konventionen sind Planungsentscheidungen und werden bei Umsetzung in
Doc/07_RISKS_AND_DECISIONS.md mit ihrer Begründung festgehalten.

### B – Delta, Gamma, Vega, Theta und Rho

Analytische BSM-Greeks für europäische Calls/Puts mit stetiger Dividendenrendite,
vektorisierten Eingaben und denselben Eingabeprüfungen wie die Preis-API.

Abnahme: typisierte API mit dokumentierten Formen/Einheiten; Long-/Short-Vorzeichen
werden erst bei Positionsaggregation angewandt. T=0, sigma=0 und S=0 haben
explizite dokumentierte Ergebnisse oder konkrete Exceptions.
Verifikation: unabhängig hergeleitete Referenzwerte, Ableitungen der Put-Call-Parität
und zentrale Differenzen bei mehreren Schrittweiten im glatten Bereich.
Toleranzen vorab nach Einheit und Konditionierung festlegen.

### C – Risiken auf Position und Portfolio herunterbrechen

Aktien-Delta, Options-Greeks mit Menge und Multiplikator sowie Anleihen-DV01 und
Konvexität für die bestehende flache stetige Zinskurve. Delta/Gamma pro Underlying
ausweisen; unterschiedliche Underlyings nicht zu einem unbeschrifteten Wert summieren.
Vega/Rho nur mit klar benanntem gemeinsamem Schock aggregieren.
DV01 als positiver Verlust bei einer Zinserhöhung um einen Basispunkt definieren.

Abnahme: Einzelpositionen und Summen nachvollziehbar, Cash unter einem reinen
Bewertungsschock unverändert, fällige Positionen gemäß Ereigniskonvention behandelt.
Verifikation: entgegengesetzte Positionen heben sich auf, Multiplikator skaliert
linear; Nullkupon-DV01/Konvexität aus analytischen Ableitungen, Kuponanleihe aus
unabhängiger Cashflow-Summe und Vergleich mit kleinen Zinsänderungen.

### D – Benannte Stressszenarien

Relative Spot-Schocks je Asset, absolute Volatilitätsänderungen je Option und
parallele Zinsänderungen; kombinierte Szenarien mit vollständiger Neubewertung.
Beispiele: Aktien −20 %, Volatilität +10 Prozentpunkte, Zins +100 Basispunkte.
Szenarien sind hypothetisch und haben keine behauptete Eintrittswahrscheinlichkeit.

Abnahme: Basiswert, Stresswert und P&L je Position und Portfolio, einschließlich
Cash; ungültige negative Spots/Volatilitäten werden abgelehnt statt abgeschnitten.
Eine Spot-/Volatilitäts-Heatmap nutzt denselben Rechenkern, sofern plots installiert ist.
Verifikation: Nullschock exakt unverändert bei identischer Bewertung; Aktien-P&L
handgerechnet, Anleihe direkt aus Cashflows, Optionsstress aus Referenzfällen;
lokale Greek-Näherung gegen vollständige Neubewertung bei schrumpfenden Schocks.
Stressverluste werden nicht als VaR oder ES bezeichnet.

### E – Zustandsabhängige Ausführung

M1 verwendet identische Trades auf allen Pfaden und Mengen mit Form
(times, instruments). M2 benötigt pfadspezifische Entscheidungen und Mengen
(paths, times, instruments). Eine eigene Ergebnisstruktur oder ein expliziter
Adapter erhält die M1-API; keine stille Änderung ihrer Array-Formen.

Abnahme: pfadweiser Ledger mit ausgeführten Trades, Cash, Beständen, Gebühren
und Vermögen; feste Gebühr pro ausgeführtem Auftrag plus proportionaler Gebühr
auf absoluten Umsatz. Leerverkäufe und negative Cashbestände ablehnen.
Bei Kursänderungen zwischen Signal und Ausführung Käufe auf verfügbares Cash
nach Verkäufen und Kosten begrenzen; Regel deterministisch dokumentieren.
Verifikation: handgerechneter Ein-Pfad-Fall, keine Zukunftsinformation, identische
Pfadpräfixe erzeugen identische Entscheidungen, kein Trade ohne Mengenänderung,
Vermögensbilanz und Kostenvorzeichen. M1-Regressionssuite bleibt grün.

### F – Zwei Rebalancing-Regeln

Kalenderregel mit expliziten Rasterterminen; Schwellenregel bei Überschreiten
einer absoluten Zielgewichtsabweichung. Gewicht wird auf positives Gesamtvermögen
bezogen, Schwelle in Prozentpunkten; bei Auslösung zurück auf Zielgewichte.

Abnahme: Regeln teilen denselben Ausführungskern, dokumentieren Signal-/Tradezeit
und liefern Umsatz, Kosten und realisierte Gewichte. Nichtpositive Vermögensbasis
wird ausdrücklich abgelehnt. Vergleich mit Buy-and-Hold nutzt identische
Marktpfade, Anfangskapital, Eröffnungskosten und Finanzierungsannahmen.
Verifikation: konstante Preise, exakt erreichbare Gewichte ohne Kosten,
Schwellen-Grenzfälle, Kosten reduzieren Vermögen um den gebuchten Betrag,
fehlende Folgetermine und Cashknappheit. Rasterverfeinerung als Sensitivitätsprüfung
ausweisen, ohne identische Resultate unterschiedlicher Handelsfrequenzen zu erwarten.

### G – Reproduzierbares Risk Lab

Offline-CLI-Beispiel mit Seed, expliziten Parametern und zwei Vergleichen:
Rebalancing gegen Buy-and-Hold sowie Aktien gegen Protective Put.
Exporte enthalten Vermögen, P&L, VaR/ES, Drawdown soweit definiert, Umsatz/Kosten,
Positions-Exposures und Stress-P&L. Optionale Diagramme zeigen Strategieverläufe
und Stress-Heatmap; keine GUI nötig.

Abnahme: ein dokumentierter Aufruf erzeugt alle Pflichtartefakte; Konfiguration,
Seed, Paketversion und Einheiten sind mit exportiert. Fehlende plots-Abhängigkeit
verhindert keine numerischen Exporte. Handgerechnetes Mini-Beispiel erklärt die
Buchungen; Integrationstest prüft Exportwerte gegen die jeweiligen API-Ergebnisse.

### H – Verifikation und Release

TDD-Nachweis pro ausführbarem Verhalten, unabhängige numerische Referenzen,
explizite Toleranzen und aktualisierte Modellgrenzen dokumentieren.
Python 3.11–3.13, pytest, ruff check/format, mypy, diff-Prüfung, Paketbau und
frische Wheel-Installation einschließlich Offline-Beispielen müssen grün sein.
Release-CI installiert plots; relevante numerische Konvergenznachweise sind Pflicht.
Numerisch verifiziert bedeutet weiterhin nicht empirisch validiert.

## Bewusst außerhalb von M2

Live-Daten, historische Kalibrierung und empirisches Backtesting; Portfoliooptimierung;
amerikanische/exotische Optionen; stochastische Zinsen/Volatilität; FX, Steuern,
Margin, Brokeranbindung, Dividenden-Cashflows und externe Zu-/Abflüsse.
Delta-Hedging mit Optionen, HTML-Dashboard und weitere Strategien sind Kandidaten
für M3 und blockieren M2 nicht. Keine neue Pflichtabhängigkeit ist eingeplant.

## Umsetzung und Integration

Die Arbeitspakete A–H sind als Issues #21–#28 mit Kriterien und Prüfplänen im
[Milestone M2](https://github.com/maschin96/FinanceToolkit/milestone/3) angelegt.
Das Planungs-Issue #20 verfolgt die Veröffentlichung dieser Roadmap. Die Planung ist Repository-Pflege
auf einem Issue-Branch von main; sie führt noch keine M2-Funktionalität ein.

Erst bei Beginn der funktionalen Umsetzung `codex/milestone-m2` vom aktuellen
stabilen main erstellen. Pro Issue eigener Branch und PR nach milestone-m2.
Zuerst A, dann B→C→D und E→F; G führt beide Stränge zusammen, H schließt ab.
Keine parallelen Agenten sind für diese Reihenfolge vorausgesetzt.

Alle Pflichtpakete, Dokumentation, CI am aktuellen Stand und Review-Anmerkungen
müssen vor dem Release-PR nach main abgeschlossen sein. Fehlendes unabhängiges
Review transparent nennen. main zuvor im Milestone integrieren und erneut prüfen;
nach Release-Merge CI am tatsächlichen main-Zielcommit prüfen, erst dann v0.2.0
taggen und öffentliche Release-Artefakte veröffentlichen. Release-Issue bleibt bis
dahin offen. Keine PyPI-Veröffentlichung; keine unbelegten Terminversprechen.
