# M1-Verifikationsbericht – 0.1.0

## Abnahmeumfang

| Issue | Implementiertes Ergebnis | PR |
| --- | --- | --- |
| #3 | Korrelierte exakte GBM-Pfade | #12 |
| #4 | Europäische Calls/Puts, Payoffs | #13 |
| #5 | Kuponanleihen, Kurven-/Stückzinsbewertung | #14 |
| #6 | Transaktionen, Positionen, Cashflows, Finanzierung | #15 |
| #7 | Gesamtportfolio-P&L und Risikokennzahlen | #16 |
| #8 | Reproduzierbare Beispiele und Export-/Diagrammadapter | #17 |
| #9 | Gesamtverifikation, Dokumentation, Paketbau und Release | Release-PR |

Die Issues enthalten Red-/Green-Nachweise. Neue Funktionen wurden vor ihrer
Implementierung mit fehlenden Modul-/Verhaltenstests geprüft, anschließend gegen
unabhängige Erwartungen verifiziert. Referenzwerte wurden nicht blind regeneriert.

## Fachliche Nachweise

- [GBM](11_GBM_SIMULATION.md): deterministische Grenzen, analytische Normal-/
  Lognormalmomente, Kovarianzen, singuläre Korrelation, unabhängige Zeitinkremente,
  fester RNG, unveränderte globale Zufallsquelle und extreme Größenordnungen.
- [Optionen](12_OPTIONS.md): bekannte Preise, Payoff-Quadratur, Put-Call-Parität,
  Bounds/Monotonie, Fälligkeit, null Volatilität und negative Zinsen.
- [Anleihen](13_BONDS.md): unabhängig enumerierte Zahlungen, Nullkuponformel,
  Clean/Dirty/Stückzins, Kuponsprünge, Tilgung und Zinsmonotonie.
- [Portfolio](14_PORTFOLIO.md): Cash-Rekonstruktion, Long-/Short-Symmetrie,
  Gebühren, Finanzierung, ex-Zahlungsstichtage und keine Doppelzahlungen.
- [Analyse](15_ANALYTICS.md): handgerechnete Verluste, Quantile/Tail-Massen,
  Drawdowns und Risikoaggregation vor Quantilbildung.
- [Beispiele](../examples/README.md): Put-Floor, Call-Cap, Zinsszenarien,
  vertragliche Coupon-/Tilgungsbilanz, Parameteränderung, CLI/CSV/JSON/PNG.

Toleranzen sind in den jeweiligen Modelldokumenten mit Einheiten und Größenordnung
festgelegt. Monte-Carlo-Tests nutzen sechs analytische Standardfehler bei festen
Seeds; deterministische Tests nutzen begründete Float64-Toleranzen. Exakte GBM-
Schritte und analytische Bewertungen haben keinen Euler-/Solverfehler; hierfür
sind Diskretisierungs-Konvergenztests nicht anwendbar. Stichprobenmomentprüfungen
mit verschiedenen n und unabhängige Bilanz-/Integralreferenzen ergänzen Unit-Tests.

## Technische Release-Prüfungen

Die lokale Gesamtsuite enthält 130 erfolgreiche Tests inklusive Diagrammtest.
Release-Abnahme erfordert weiterhin erfolgreiche Prüfungen am aktuellen Commit:
ruff check/format, striktes mypy, git diff --check, Lock-Konsistenz, Paketbau,
frische Wheel-Installation außerhalb des Quellbaums und Offline-Beispielausführung.
Die Linux-CI-Matrix prüft Python 3.11, 3.12 und 3.13; lokal Python 3.13/macOS.
Zusätzliche frische Python-3.11-Wheel-Prüfung: alle 130 Tests und Beispiel-CLI
bestanden; Actions-Ausführung prüft zusätzlich die Linux-Plattform.
CI muss am aktuellen Release-PR-Stand und tatsächlichen main-Zielcommit grün sein,
bevor v0.1.0 getaggt und Wheel/Quelldistribution im öffentlichen GitHub Release abgelegt
werden. Konkrete Commit-/CI-Ergebnisse sind im Release-PR und Release-Issue #9.

## Einschränkungen und Review

Keine empirische Marktvalidierung. GBM bildet keine Sprünge/Volatilitätscluster ab;
BSM ist idealisiert; Anleihen sind ausfallfrei. Keine Steuern, FX, Margin, Broker,
Live-Daten oder Aktien-Dividenden-Cashflows. Zinsen sind je Bewertungszeitpunkt
flache Kurven; keine stochastische Zinsdynamik. Extremwerte können numerisch nicht
darstellbar sein und werden abgelehnt. Große Pfadarrays benötigen entsprechend
Speicher. Prozentuale Kennzahlen sind bei nichtpositivem Kapital/Vermögen explizit
undefiniert; absolute P&L bleiben verfügbar. Keine Open-Source-Lizenz vergeben.

Diff, Modellannahmen, öffentliche APIs, Bilanzkonventionen und Diagramme wurden
geprüft. Kein unabhängiger Reviewer verfügbar; eine externe Freigabe wird nicht
behauptet. Keine offenen Review-Anmerkungen dürfen bei Integration bestehen.
