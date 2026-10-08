# M2 – API-Verträge und Referenzfälle

Issue #21. Zeit in Jahren, Beträge in einer gemeinsamen Währung, Zinssätze und
Volatilitäten dezimal annualisiert. Kein empirischer Marktvalidierungsanspruch.

## Greeks und Exposures

`option_greeks` liefert Delta, Gamma, Vega, Theta und Rho mit NumPy-Broadcasting
wie `black_scholes`. Alle Eingaben müssen endlich sein. Die analytische API gilt
für S, K, T und sigma strikt positiv; S=0, T=0 oder sigma=0 werden mit ValueError
abgelehnt, da nicht alle Ableitungen dort eindeutig/glatt sind. Preisbewertung
behält ihre M1-Grenzfälle. Theta = minus Ableitung nach Restlaufzeit, pro Jahr;
Vega und Rho pro Änderung der Dezimaleingabe um 1. Je Prozentpunkt: mal 0,01.

Referenz: S=K=100, T=1, sigma=0,2, r=q=0: d1=0,1, d2=−0,1.
Call-Delta=Phi(0,1), Put-Delta=Phi(0,1)−1, Gamma=phi(0,1)/20,
Vega=100 phi(0,1), Theta=−10 phi(0,1), Call-Rho=100 Phi(−0,1),
Put-Rho=−100 Phi(0,1). Phi/phi sind Standardnormalverteilung/-dichte.
Differenzenreferenzen im glatten Bereich: relative Toleranz 2e-5, absolute 2e-7;
analytische Identitäten: 1e-12 relativ/absolut bei diesen Größenordnungen.

Snapshots enthalten Zeit, Instrumente, Mengen, Spots, flachen stetigen Zins und
Cash. Mengen sind signed, Optionen skalieren mit Multiplikator. Delta/Gamma
werden je Asset ausgewiesen. Portfolio-Vega bezeichnet einen gemeinsamen
absoluten Volatilitätsschock aller aktiven Optionen; Portfolio-Rho einen parallelen
Zinsschock. Anleihen-Rho ist die erste Preisableitung nach Zins.
DV01 = −dP/dr mal 1e-4, lokale Sensitivität, kein endlicher Stressverlust;
Konvexität = (d²P/dr²)/Dirty-Preis, in Jahren². Bei Fälligkeit beide null.
Referenz Nullkupon N=100, T=2, r=0: P=100, Rho=−200, DV01=0,02,
d²P/dr²=400, Konvexität=4. Gegenpositionen summieren sich zu null.

## Stress-Snapshot

Snapshot nach Zahlungen/Trades, ex-Zahlung bewertet. Gleiche Zeit, Mengen und Cash
in Basis und Stress, keine Handels-/Finanzierungsereignisse dazwischen. Stress:
Spot mal (1+relativer Schock), Optionsvolatilität plus absolute Änderung je
Position und Zins plus parallele Änderung. Negative Ergebnisse ablehnen;
Spot/Volatilität null sind für Preise erlaubt. Abgelaufene Instrumente null.
Nullschock unverändert; eine Aktie Menge 10, Spot 100, Schock −20 % hat P&L −200.
Cash unverändert. Scenario-P&L ist keine probabilistische Verlustkennzahl.

## Strategieausführung

Eigene `StrategyPaths`: Mengen, Trades und Kosten mit Form (paths,times,assets),
Cash und Vermögen (paths,times); M1 bleibt unverändert. Anfangskapital positiv,
Long-only Aktien, Bruchstücke, Cashrest; keine Dividenden, Fremdkapital oder
Außenflüsse. Zielgewichte nichtnegativ, Summe höchstens eins.

Initiale Zielallokation am Rasterbeginn; danach Signale nach aktuellen Ereignissen
und Ausführung erst am nächsten Rasterpunkt. Signal erhält ausschließlich Kopien
der aktuellen Zeit, Spots, Mengen und Cash. Zukunft nicht zugänglich. Signale
am letzten Rasterpunkt werden nicht ausgeführt. Gewünschte Stückzahlen werden
am Signalzeitpunkt aus Zielgewichten und aktuellem Vermögen berechnet, nicht
rückwirkend an den Ausführungskurs angepasst. Kalendertermine müssen genau zum
Raster passen; Schwelle als Bruchteil (0,05 = fünf Prozentpunkte), strikt überschritten.

Ausführung: erst Verkäufe, dann Käufe in Asset-Reihenfolge. Feste Gebühr je
wirklich ausgeführtem Assetauftrag und proportionale Gebühr auf absoluten Umsatz.
Ein Verkauf, dessen Erlös seine Gebühren nicht deckt und den Cashbestand negativ
machen würde, wird nicht ausgeführt. Käufe auf finanzierbare Stückzahl nach
Verkäufen/Gebühren begrenzen; bei Cash kleiner/gleich Fixgebühr entfällt der Kauf.
Keine Nullaufträge/Nullauftragsgebühren; keine negativen Bestände/Cash.
Cash wächst zwischen Rasterpunkten mit explizitem stetigem lending_rate,
Standard null. Kein implizites Borrowing. Numerische Fehler/Überläufe ablehnen.

Referenz: Kapital 100, Spot 10, Zielgewicht 0,5, keine Kosten: fünf Aktien,
Cash 50. Nächster Spot 20: Vermögen 150, Aktiengewicht 2/3; Signal auf 0,5
fordert 3,75 Aktien. Ausführung bei Spot 20 verkauft 1,25 Aktien, Cash 75,
Vermögen weiterhin 150. Fixgebühr 1 reduziert Vermögen genau um 1.
Stückzahl-/Cash-Bilanzen: absolut 1e-10, relativ 1e-12 für diese Beispiele;
Vergleiche keine Unterschiede durch nachträgliche Toleranzaufweitung verdecken.

## Exporte und Verifikation

CLI exportiert Konfiguration inklusive Seed, Version und Einheiten; Buy-and-Hold,
Kalender und Schwelle nutzen dieselben Pfade, Kapital und Eröffnungskosten.
Schutzput-Vergleich verwendet dieselben Aktienpfade und Bewertungsannahmen.
Relative Renditen/Drawdown nur bei gültiger positiver Kapital-/Vermögensbasis;
absolute P&L und VaR/ES nach M1-Konvention. Kleine handgerechnete Referenzen,
Prefix-Invarianz, Nullschocks, Multiplikator und Gegenpositionen sind Pflicht.
Rasterverfeinerung ist eine Sensitivitätsanalyse veränderter Handelsmöglichkeiten,
kein Versprechen identischer Ergebnisse. Keine zusätzlichen Pflichtabhängigkeiten.
