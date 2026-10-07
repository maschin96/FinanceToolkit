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

## Spätere, nicht beauftragte Erweiterungen

Kalibrierung aus Marktdaten, stochastische Zinsen, amerikanische Optionen,
Greeks, Backtesting, Optimierung, FX und Oberfläche werden bei Bedarf separat geplant.

## Abnahmestand M1

M0 ist stabil in main freigegeben (PR #11). Alle M1-Funktions-Issues #3–#8
sind geprüft und in codex/milestone-m1 integriert (PRs #12–#17).
Issue #9 bleibt bis main-Zielcommit-CI, Tag und privaten Release-Artefakten offen.
Die Release-Integration umfasst ausschließlich den vollständigen M1-Pflichtumfang.
