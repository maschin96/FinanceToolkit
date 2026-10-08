# P&L-Reconciliation und Greek-Näherung (#43)

`attribute_book` erklärt jedes Intervall mit Anfangsbeständen. Marktbewegung =
Anfangsmenge mal Änderung des ex-Ereignis-Modellquotes mal Multiplikator plus
Barausgleich. Abrechnung wird separat gezeigt, ist bereits im Markteffekt
enthalten und wird niemals ein zweites Mal addiert. Execution = neue Trade-
Menge mal aktueller Modellquote mal Multiplikator plus signed Trade-Cashflow;
abweichende Ausführungspreise werden somit als Slippage sichtbar. Gesamt-P&L =
Markt + Execution - Gebühren - Aktienleihe + Cashfinanzierung. Anfangsorders
sind Bestandteil des Anfangsvermögens und kein späteres Intervall-P&L.

Die lokale Approximation verwendet Anfangs-Greeks: delta*dS + gamma*dS²/2 +
vega*dSigma + theta*dt + rho*dr. Sigma/Zinsänderungen sind Dezimaljahresraten,
dt ist verstrichene Zeit in Jahren; die signed Anfangsmenge und Multiplikator
skalieren alle Komponenten. `explain_option_move` ermöglicht explizite Spot-,
Volatilitäts- und Zinsschocks; das Buch selbst verwendet konstante Preisparameter.
Gemischte Ableitungen/höhere Ordnungen liegen im Rest. Keine eindeutige kausale
Attribution. Bei Verfall und nichtglatten Anfangsgrenzen gibt es ein Ereignisflag,
keine Taylor-Aussage: Komponenten null, tatsächliche Bewegung im Ereignisrest.

Positionen: (Pfade, Intervalle, Instrumente), Finanzierung/P&L: (Pfade, Intervalle).
Relative Intervall-P&L ist bei nichtpositiver Anfangsbasis `None`, JSON null.
CSV zeigt dieselben Positionen plus ausdrücklich benannte Portfolio-Finanzierung
und Portfolio-P&L; diese Portfolio-Spalten nicht über Positionen summieren.
`export_attribution` exportiert JSON und CSV einschließlich Einheiten/Ereignissen.

Handtests für Aktien, Executionpreis, Gebühren, reinen Cashzins und Optionsverfall
reconcilieren mit 1e-10 Währungstoleranz (kleine Kapitalgrößen bis 1000). Separate
kleine Spot-/Vol-/Zins-/Zeitschocks zeigen kleiner werdenden Taylor-Rest bei
halbiertem Schock. Die automatische Bilanzkontrolle verwendet zusätzlich 1e-12
relative Rundungstoleranz bei großen Buchwerten.
