# Roadmap

## M0 – Projektbasis

| Issue | Ergebnis | Voraussetzung |
| --- | --- | --- |
| [#1](https://github.com/maschin96/FinanceToolkit/issues/1) | Projektauftrag, Dokumentation, Finance-Regeln | keine |
| [#2](https://github.com/maschin96/FinanceToolkit/issues/2) | Paketbasis, Installation und CI | #1 |

M0 muss vor Arbeitsbeginn an M1 stabil in main integriert sein.

## M1 – Simulation und Portfolioanalyse

| Issue | Ergebnis | Voraussetzung |
| --- | --- | --- |
| [#3](https://github.com/maschin96/FinanceToolkit/issues/3) | Korrelierte GBM-Aktienpfade | #2 |
| [#4](https://github.com/maschin96/FinanceToolkit/issues/4) | Europäische Calls/Puts | #2 |
| [#5](https://github.com/maschin96/FinanceToolkit/issues/5) | Anleihen und Zins-Szenarien | #2 |
| [#6](https://github.com/maschin96/FinanceToolkit/issues/6) | Positionsbuch und Cashflows | #3, #4, #5 |
| [#7](https://github.com/maschin96/FinanceToolkit/issues/7) | Portfolioverläufe und Kennzahlen | #6 |
| [#8](https://github.com/maschin96/FinanceToolkit/issues/8) | Reproduzierbare Beispiele | #7 |
| [#9](https://github.com/maschin96/FinanceToolkit/issues/9) | Verifikation und Release 0.1.0 | #3–#8 |

#8 hat Priorität P1, ist aber für das benutzbare M1-Release verpflichtend.
Alle anderen Arbeitspakete haben Priorität P0. Kein Issue gilt allein durch einen
lokalen Commit als abgeschlossen. Aufwandsschätzungen erfolgen nach Einrichtung
von Paket und Tests, nicht als unbelegte Liefertermine.

## M2 – Portfolio Risk Lab und spätere Erweiterungen

M2 ist als [Portfolio Risk Lab](17_M2_ROADMAP.md) in main integriert (PR #38): Greeks,
Portfolio-Exposures, Stressszenarien und Aktien-/Cash-Rebalancing mit Kostenvergleich.
[Verifikation und Release-Stand](20_M2_VERIFICATION.md); #28 und M2 sind nach
Veröffentlichung von v0.2.0 geschlossen.
Kalibrierung aus Marktdaten, stochastische Zinsen, amerikanische Optionen,
empirisches Backtesting, Optimierung, FX und Oberfläche bleiben spätere Erweiterungen.

## Abnahmestand M1

M0 ist stabil in main freigegeben (PR #11). Alle M1-Funktions-Issues #3–#8
sind geprüft und in codex/milestone-m1 integriert (PRs #12–#17).
M1 ist mit Release-PR #19 in main integriert; v0.1.0 wurde am 2026-10-07
veröffentlicht und Issue #9 geschlossen. Damit ist die Voraussetzung für den
Beginn von M2 erfüllt.

## M3 – Strategy & Hedging Lab

Pflichtumfang #39–#46 über PRs #48–#55 integriert: Optionsbuch, Finanzierung,
Delta-Hedging, Optionsstrategien, Attribution, gekoppelte Vergleiche, Yahoo-
Adapter und eigene Indizes. [Gesamtverifikation](28_M3_VERIFICATION.md) und
Release-Abschluss #47. HTML-Bericht G ist nicht beauftragt. Spätere oben genannte
Erweiterungen bleiben außerhalb des aktuellen Pflichtumfangs.
