# Reproduzierbares Hedge-/Strategy-Lab (#44)

```sh
python -m finance_toolkit.hedge_lab --paths 100 --steps 32 --seed 314 --calendar-every 1 4 --thresholds .1 .25 --fees 0 .05 --strides 1 2 --output outputs/hedge-lab --plot
```

`--plot` weglassen für einen numerischen Lauf ohne Plotimporte. Keine Netzimports
oder Downloads. Varianten vergleichen Kalenderfrequenzen (Anzahl Rasterintervalle),
strikte Delta-Schwellen in Aktienäquivalenten und fixe Währungsgebühren.
API `ComparisonCase` unterstützt zusätzlich proportionale Gebühren; `compare_hedges`
explizite Optionsposition und Lending-/Borrowing-/Leihe-/Preisraten.

Eine feine exakte GBM-Simulation erzeugt sämtliche Varianten; gröbere Raster sind
exakte Teilfolgen desselben Markts, Stride muss die Basis-Schrittzahl teilen.
Optionsposition, Anfangskapital und Openingquote sind gemeinsam. Openinggebühren
unterscheiden sich bei unterschiedlichen Gebührenvarianten und bleiben im P&L.
Die fünf gewöhnlichen Optionsstrategien werden als eigene feine Kontrollen ohne
Handelsgebühren, mit den gemeinsamen Cashfinanzierungsraten ausgewiesen.

Pflichtartefakte: comparison.json (Konfiguration, Seed/Modell, Versionen, Einheiten,
Pfadhash und Kennzahlen), comparison.csv, strategies.csv, market.csv (alle
Basisspots), wealth.csv (Cash/Zinsen/Kosten/Ziel-/Ist-Delta), ledgers.csv
(positionsweise Mengen/Quotes/Werte/Trades/Prämien/Fees/Settlement/Leihe/Turnover),
Attributions-CSV/JSON pro Variante. Optional comparison.png zeigt aus denselben
Ergebnissen mittleres Vermögen. Vollständige Ausgangsparameter und Basiswerte
machen auch übergebene nichtsynthetische Märkte prüfbar.

P&L = Endvermögen minus Anfangskapital, inklusive Openinggebühren. VaR/ES
sind probabilistische empirische Verlustkennzahlen mit 95% Konfidenz, keine
Stresswerte. Rendite nur bei positiver Kapitalbasis, Drawdown nur bei überall
positivem Vermögen; sonst null. RMS Restdelta misst tatsächliche Exposure nach
verzögerter Ausführung. RMS Replication P&L beschreibt die Größe des terminalen
P&L; nur unter dokumentierten risikoneutralen Nullkosten-/Finanzierungsannahmen
ist null das Replikationsziel. Kein universelles Ranking/Gewinnversprechen.

Mini-Referenz im Test: zwei konstante Spotpfade 100 mit Zeiten 0,.25,.5,.75,1,
short ATM Call, K=100, sigma=.2, Multiplikator 1. Ungehedgt endet die wertlos
verfallene Position mit Openingpremium im Cash; Anfangsvermögen bleibt 1000.
Kalenderkontrolle nutzt exakt dieselben Spots, Stride 2, denselben Openingquote.
CSV/JSON werden gegen die verifizierten Kernresultate geprüft, CLI-Doppellauf mit
Seed 123 ist identisch; PNG-Signatur und Pflichtartefakte werden kontrolliert.
