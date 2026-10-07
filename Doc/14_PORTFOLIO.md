# Positionsbuch und Portfolio-Neubewertung

`value_portfolio(GBMPaths, trades, initial_cash=..., rate=0,
lending_rate=0, borrowing_rate=0)` liefert PortfolioPaths. Aktien: `Stock(asset=0)`;
Optionen: `EuropeanOption(asset, strike, maturity, volatility, kind="call",
multiplier=100, dividend_yield=0)`; Anleihen: `Bond`. Maturity ist absolut seit t=0.
`Trade(time, instrument, quantity, price=None, fee=0)` kauft bei positiver Menge
und verkauft/shortet bei negativer. Modellvolatilität explizit; Bewertung mit r,
nicht Szenariodrift mu. `rate` ist eine flache stetige Kurve je Szenario/Zeitpunkt:
Skalar, Zeitvektor oder (Pfade, Zeiten)-Array. Lending-/Borrowing-Raten sind
separate stetige Konstanten, standardmäßig null. Eine Währung, keine Außenflows.

Ausführungspreis ist je Aktie/Anleihe oder je Underlying-Einheit einer Option.
Optionskosten = Menge*Multiplikator*Quote. Gebühren sind je Trade in Währung.
Ohne Quote wird am aktuellen Modellpreis gehandelt. Abweichende Ausführungspreise
können sofortige Mark-to-Market-Gewinne/Verluste verursachen.

Zeitpunkte müssen bei null starten, streng steigen und alle Trade-/Zahlungs-/
Verfallstermine der verwendeten Instrumente innerhalb des Horizonts enthalten.
Matching-Toleranz 1e-10 Jahre; Rasterpunkte müssen mehr als 2e-10 Jahre auseinander
liegen. Für GBM geeignete Schrittzahlen wählen. Ein Portfolio-Horizont darf vor
Fälligkeit enden; dann bleibt der Marktwert erhalten.

Reihenfolge pro Rasterpunkt: Cashverzinsung seit letztem Punkt; Zahlungen an
vorhandene Halter; fällige Positionen ausbuchen; Trades in Eingabereihenfolge;
ex-Zahlung-Neubewertung. Handel am/nach Verfall wird abgewiesen. Kein Marginzwang;
negatives Cash und Shortpositionen sind ausdrücklich zulässig. Aktien liefern
Preisrenditen, keine Dividendenzahlungen; q bei Optionen ist nur Bewertungsannahme.

PortfolioPaths enthält Instrumentmarktwerte (Pfade, Zeiten, Instrumente),
Bestände (Zeiten, Instrumente), Cash, Vermögen und separate signierte
Cashflows für Trades, Gebühren, Kupons, Tilgung, Optionen und Finanzierung.
P&L-Basis ist initial_cash vor t=0-Trades, nicht der Marktwert nach Gebühren.

Verifikation: unabhängig handgerechnete Roundtrips, Gebühren, Kuponverkauf,
Fälligkeitsauszahlungen, Long-/Short-Symmetrie aller Instrumente und konstante
Finanzierungsraten. Vollständige Rekonstruktion Cash=Anfangs-Cash+Summe aller
Cashflows (atol 1e-10 bei Beträgen bis 1000). Deterministische Optionsneubewertung
prüft sinkende Restlaufzeit mit diskontiertem Strike (atol 1e-11).
Keine doppelte Zahlung nach Verfall, kein Coupon an Käufer am Zahlungstermin.
Keine Steuer-, FX-, Margin- oder Broker-Engine und keine Marktvalidierung.
