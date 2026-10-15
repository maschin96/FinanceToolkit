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
empirisches Backtesting, Optimierung und FX bleiben spätere Erweiterungen.
Eine Terminal-Oberfläche ist jetzt für M5 geplant.

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

## M4 – Stabilisierung und Robustheit

[M4](https://github.com/maschin96/FinanceToolkit/milestone/5) bündelt die
Stabilisierung des vorhandenen M3-Funktionsumfangs mit Ziel v0.3.1.
Releaseabschluss und Pflichtumfang werden in
[#66](https://github.com/maschin96/FinanceToolkit/issues/66) verfolgt.
M4 ist Voraussetzung für die funktionale Umsetzung von M5.

Alle Pflichtissues #58–#65 sind über PRs #67–#72, #83 und #84 geprüft
in `codex/milestone-m4` integriert und explizit geschlossen.
[Gesamtverifikation](30_M4_VERIFICATION.md): Fälligkeits-/Cash-/Attributions-
bilanzen, numerische Grenzen, Daten-/CLI-Verträge, optionale Profile und
[Exportprofil](29_M4_EXPORT_PROFILE.md). Version 0.3.1 ist das Wartungsrelease.
Der vollständige Veröffentlichungsnachweis (Release-PR nach main,
Zielcommit-CI, Tag und öffentliche Pakete) wird in #66 festgehalten.
Der dortige Abschluss belegt die Freigabe von M4 für den Beginn von M5.

## M5 – FinanceToolkit Textual-TUI

[Detailplanung](29_M5_TUI_ROADMAP.md),
[Planungsissue #73](https://github.com/maschin96/FinanceToolkit/issues/73) und
[Milestone M5](https://github.com/maschin96/FinanceToolkit/milestone/6).
Ziel v0.4.0: optionale, vollständig tastaturbedienbare Terminal-App auf den
bestehenden Toolkit-APIs, mit Offline-Demos und reproduzierbaren Exporten.

| Issue | Ergebnis | Voraussetzung |
| --- | --- | --- |
| [#74](https://github.com/maschin96/FinanceToolkit/issues/74) | TUI-/API-Verträge und optionales Installationsprofil | M4/v0.3.1 abgeschlossen, stabil in main |
| [#75](https://github.com/maschin96/FinanceToolkit/issues/75) | App, Navigation und Hintergrundjobs | #74 |
| [#76](https://github.com/maschin96/FinanceToolkit/issues/76) | GBM, Einzelinstrumente und Portfolios | #74, #75 |
| [#77](https://github.com/maschin96/FinanceToolkit/issues/77) | Portfolio-Risiken und Stress | #74–#76 |
| [#78](https://github.com/maschin96/FinanceToolkit/issues/78) | Strategien, Hedging und Attribution | #74–#77 |
| [#79](https://github.com/maschin96/FinanceToolkit/issues/79) | Eigene Indizes und optionale Yahoo-Daten | #74, #75 |
| [#80](https://github.com/maschin96/FinanceToolkit/issues/80) | Workspaces, Konfigurationen und Exporte | #74–#79 |
| [#81](https://github.com/maschin96/FinanceToolkit/issues/81) | Gesamtverifikation und Release v0.4.0 | #74–#80 |

Alle acht Arbeitspakete sind Release-Pflichtumfang. Planung ist keine
Implementierung; keine Deadline ohne belastbare Schätzung. Erst nach
vollständigem M4-Abschluss und bei Umsetzungsbeginn `codex/milestone-m5`
vom aktuellen stabilen main anlegen. Issue-PRs dorthin, Release-PR nach main
erst bei Freigabereife; #81/M5 erst nach vollständiger Veröffentlichung schließen.


Stand 2026-10-15: M5 A–G (#74–#80) sind über PR #87–#93 in
`codex/milestone-m5` integriert und geschlossen. #81 bereitet die abschließende
Dokumentation und Paketversion 0.4.0 vor. Die manuellen macOS-/Linux-Tastaturtests
bleiben nach Eigentümerbestätigung Pflicht; kein Release oder Merge nach main
vor diesem Nachweis. [Abnahmestand](38_M5_TUI_VERIFICATION.md).
