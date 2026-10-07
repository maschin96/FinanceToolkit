# Portfolioanalyse

`analyze_portfolio(PortfolioPaths, confidence=0.95)` liefert Vermögen, P&L,
kumulative einfache Rendite, Drawdowns, maximalen Drawdown je Pfad,
terminale Verluste und aggregierte Tail-Risiken.
P&L = Vermögen - Anfangs-Cash vor ersten Trades, einschließlich Gebühren.
Verlust = Anfangs-Cash - terminales Vermögen. Positive Verluste bedeuten Schaden;
VaR darf bei profitablen Szenarien negativ sein. Keine Außenkapitalflüsse.

`tail_risk(losses, confidence=0.95)` erwartet einen endlichen nichtleeren 1D-Vektor.
VaR ist NumPy-Quantil mit Methode linear. Expected Shortfall ist der Mittelwert
der schlechtesten (1-confidence)*n Beobachtungen mit anteiligem Grenzpunkt.
Beispiel Verluste [0,10,20,30], confidence=0,625: VaR=18,75;
ES=(30+0,5*20)/1,5=26,6666666667. Bei kleinen Stichproben differieren lineare
VaR-Interpolation und Tail-Massengewichtung bewusst. Einzelsamples und Ties zulässig.
Die Confidence muss strikt zwischen null und eins liegen. Keine VaR-Summierung
über Einzelinstrumente; ein Test mit gegenläufigen Aktienrisiken prüft die Aggregation.

`portfolio_returns(wealth, initial_value=...)` braucht positives Anfangskapital;
sonst ValueError. `analyze_portfolio` liefert stattdessen returns=None und weiterhin
P&L/Risiko. `drawdown` = 1 - wealth/running_peak, entlang der Zeitachse;
der erste beobachtete Wert nach Trades/Gebühren setzt den Peak. Nur positive
Vermögen erlauben relative Drawdowns; andernfalls reportet die Analyse None.
`maximum_drawdown` ist der größte positive Verlustanteil je Pfad.

Verifikation gegen handgerechnete Verlust-/Vermögensvektoren und Portfoliobilanzen.
Renditen/Drawdowns atol 1e-14 (dimensionslos); P&L in ganzzahligen Beispielen exakt.
Cashflow-Verifikation und Restlaufzeit-/Zinsnachweise stehen in Doc/14_PORTFOLIO.md.
Kein numerischer Optimierer, keine empirische Marktvalidierung und keine
Investmentempfehlungen. Diese Kennzahlen bewerten die eingegebenen Szenarien.
