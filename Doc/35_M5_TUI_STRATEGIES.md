# M5 – Strategien, Hedging und Attribution (#78)

Ctrl+4 bietet Buy-and-Hold, Kalender-/Schwellen-Rebalancing, die fünf vorhandenen
Optionsstrategien, ein geplantes dynamisches Optionsbuch, Delta-Hedgevergleiche
und P&L-Attribution. Die Adapter erzeugen genau einen Markt; alle Varianten
verwenden dasselbe Anfangskapital. Gemeinsame Zins-/Finanzierungsparameter
stehen in der Portfolioansicht. Die Openingbestände unterscheiden sich bewusst
nach Strategie und sind im Vergleich beschrieben; es gibt kein Gewinnranking.

## Konfiguration und Ausführung

Zielgewichte sind Dezimalanteile mit Summe ≤1, der Rest bleibt Cash. Kalender
enthält Signalzeiten in Jahren; die Schwelle ist ein Gewichtsabstand, z.B. .05
für fünf Prozentpunkte. Kalender und Schwelle schließen sich aus. Die öffentliche
Rebalancing-API führt Signale am nächsten Rasterpunkt aus. Fixkosten sind
Währungsbeträge, proportionale Kosten sind als Prozent beschriftet.

Optionsstrategie: protective_put, covered_call, collar, bull_call oder bear_put;
Asset, zwei Strikes, Fälligkeit, Modellvolatilität, positive Vertragszahl,
Multiplikator und Dividendenrendite sind editierbar. Das dynamische Buch bietet
Order-Anlegen/Ändern/Löschen über denselben Instrumentdialog. Aktien/Optionen
sind erlaubt, Anleihen bleiben im statischen Portfolio. Orderzeit bezeichnet
den gewünschten Ausführungspunkt: t=0 als Opening sofort, spätere Punkte über
ein vorab bekanntes Signal am vorherigen Rasterpunkt. Es wird keine künftige
Marktbeobachtung gelesen. Ausführungsquote/Gebühr folgen dem bestehenden Order-
Vertrag, kein stilles Verschieben der angegebenen Zeit.

Short-Aktien und Cashkredit benötigen im dynamischen Buch die ausdrücklichen
ja/nein-Freigaben. Aktienleihsatz sowie Guthaben-/Kreditzins werden unverändert
an die Kern-API übergeben. Es gibt keine Margin-/Brokerannahme.

Hedgevergleiche sind standardmäßig deaktiviert. Aktivierung erfordert explizite
Short-/Kreditfreigaben, weil die Hedge-API diese Fähigkeiten für Replikation
verwendet. Die gemeinsame Openingoption hat dieselbe Fälligkeit wie der Horizont.
Fallnamen und Strides konfigurieren gekoppelte Teilfolgen des feinen Rasters;
Kalenderhäufigkeit, absolute Delta-Schwelle in Aktien und Kosten sind einstellbar.
Eigene Fälle können hinzugefügt, geändert und gelöscht werden: name, stride,
calendar_every, threshold, fixed_fee und proportional_fee. Sie ersetzen die
gemeinsamen Fall-/Regel-/Kostenfelder und erlauben unhedged, Kalender und Schwelle
mit unterschiedlichen Gebühren in einem Vergleich. Höchstens 20 Fälle; keine
Laufzeitgarantie. Vor dem Hintergrundlauf werden Rechte, Gewichte, Gebühren,
Assetzuordnung, Fälligkeiten, Raster, Stride-Teiler und Regeln geprüft.

Die bestehenden Lab-Strategiekontrollen verwenden zusätzlich 0.9/1.1×Hedgestrike
und keine Tradegebühren, wie im bisherigen `compare_hedges` dokumentiert.
Die explizit konfigurierte eigene Optionsstrategie ist separat benannt.

## Ergebnisse

Buchidentitäten enthalten Kategorie und Name, z.B. hedge/protective_put und
strategy/protective_put; die konfigurierte Variante heißt
strategy/configured_protective_put, geplante Orders dynamic/scheduled.
Gleiche Namen überschreiben einander nicht. Die Buchauswahl per Pfeiltasten
zeigt Pfad 0 mit maximal 50 Zeitpunkten; vollständige Arrays bleiben im Ergebnis
für #80. Rebalancing-Bücher sind ebenfalls auswählbar.

Ledger zeigen Signal-/Ausführungszeit, Trades, Gebühren, Umsatz, Cash,
Finanzierung, Aktienleihkosten, Vermögen/P&L und tatsächliches Restdelta in
Aktienäquivalenten. Hedge-Schließungen bei Fälligkeit sind als Ereignis benannt.
Zusammenfassungen kennzeichnen Mittelwerte bzw. Summen über alle Pfade.
Monetäre Werte haben die oben angegebene Workspace-Währung.

Jedes dynamische Options-/Hedgebuch besitzt die öffentliche `attribute_book`-
Attribution mit Delta/Gamma/Theta/Vega/Rho, Residuum, Kosten, Leihe, Finanzierung
und exakter Bilanz. Eine Taylorzerlegung ist kein kausaler Erklärungsnachweis;
Ereignisresiduen werden nicht als fehlende Gebühren weginterpretiert.
Rebalancing besitzt sein Aktien-/Cash-Ledger, keine erfundene Optionsattribution.

## Schema und Verifikation

Schema v1 erhält vor M5-Veröffentlichung strategy.stock_borrow_rate=0,
hedge.enabled=false, hedge.case_names=[fine,coarse], hedge.cases=[].
Eigene Fälle haben standardmäßig name=case, stride=1, calendar_every=null,
threshold=null und beide Gebühren=0. Prozentfelder konvertieren genau einmal,
persistierte Parameter sind Dezimalwerte. Alte Feldbelegungen bleiben verwendbar.

Acht anfängliche Red-Fälle für fehlende Services/Formulare; zusätzlich Red für
unabhängige Fallregeln/-kosten und eine Null-Openingmenge vor Marktgenerierung,
danach grün. Zwölf finale Fälle prüfen
Orderzeit/Kosten/Attributionsbilanz, gemeinsame Pfade und Kategorien, Rechte und
Raster vor Marktgenerierung, Finanzierung, tatsächliches Restdelta und Pilot-
Bedienung einschließlich Orders, eigenen Fällen und Rebalancingdetails.

Unabhängig: S=100 konstant, Kapital 1000, Kauf 2 zu t=.5, Gebühr 3 ergibt
Cash 797/Vermögen 997, Intervall-P&L −3/0. Geldtoleranz 1e−10 EUR bei ~1000 EUR
berücksichtigt insbesondere GBM-log/exp-Rundung; unmotivierte exakte Geldasserts
wurden entsprechend korrigiert. Kredit über 1000 bei .07 ergibt −1000 exp(.07).
Short einer Aktie, Cash 1100, Leihsatz .02, Guthabenzins .03, Halbjahresraster
ergibt Endcash (1100 exp(.015)−1) exp(.015)−1. BSM-Delta bei S=K=100, sigma=.2,
r=q=0 ist Phi(.2 sqrt(tau)/2); verzögertes Restdelta bei t=.5 ist
Phi(.1)−Phi(.2 sqrt(.5)/2), absolute Toleranz 1e−12 Aktien. Fälligkeit räumt
die Hedgebestände, Restdelta null. Exakte Attributionsbilanz wird unabhängig
gegen Differenzen des tatsächlichen Vermögens geprüft. Bestehende Prefix-/Hedge-
Konvergenztests bleiben verpflichtend, keine geänderten Simulationsverfahren.

Lokale Gesamtprüfung vor dem ergänzenden Nullmengenfall: 475 bestanden;
Basis 460 bestanden mit exakt 15 benannten Skips (neun UI-, sechs Diagrammfälle),
tui ohne plots/yahoo 469 bestanden mit sechs Diagramm-Skips. Zwölf finale
gezielte Fälle grün; elf im gebauten Wheel außerhalb des Quellbaums geprüft.
ruff check/format, striktes mypy (32 Module), git diff --check und Paketbau
erfolgreich. Aktuelle CI prüft den finalen Stand einschließlich des zusätzlichen
Falls und Wheel auf Python 3.11–3.13 vor Integration. Eigenreview, kein
unabhängiger Reviewer verfügbar. Noch keine M5-/Releasefreigabe.
