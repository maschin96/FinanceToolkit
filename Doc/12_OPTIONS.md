# Europäische Optionen

`instruments.options.black_scholes(spot, strike, maturity, volatility, rate,
dividend_yield=0, kind="call")` liefert Preise je Underlying-Einheit.
Alle Parameter sind NumPy-broadcastfähig; skalare Eingaben liefern einen 0D-Array.
Zeit in Jahren, annualisierte Dezimalraten, kontinuierliche Zins-/Dividendenrechnung.
`option_payoff` liefert den intrinsischen Wert. Multiplikatoren und Positionen
gehören zur Portfolioebene. Negative Zinsen sind zulässig; negative Laufzeiten,
Volatilitäten oder Kurse, nichtpositive Strikes und nichtendliche Werte nicht.
Spot null ist zulässig. Bei T=0 gilt Payoff, bei sigma=0 diskontierter Forward-Payoff.
Nicht darstellbare numerische Werte werden als ValueError abgelehnt.

Verifikation: S=K=100, T=1, sigma=0,2, r=0,05, q=0 liefert Call
10,450583572185565 und Put 5,573526022256971 (analytische Normal-CDF-Auswertung).
Absolute Toleranz 1e-11 bei Kursgrößen um 100 berücksichtigt Float64-Rundung.
Put-Call-Parität wird mit Dividenden und negativen Zinsen getestet (atol 1e-11).
Ein unabhängiges Integral des diskontierten lognormalen Payoffs mit scipy.integrate
(±12 Standardabweichungen, Quadratur epsabs 1e-11) wird mit atol 1e-9 verglichen.
Bounds, Monotonie, Broadcasting, Eingabegrenzen und deterministische Grenzfälle
sind geprüft. Kein Konvergenztest nötig für die analytische Bewertungsformel.
Die SciPy-Normal-CDF ist die einzige untypisierte Infrastrukturgrenze; ihr Ergebnis
wird als Float64-Array zurückgegeben. Die übrige API bleibt strikt typgeprüft.
Realwelt-Drift mu ist kein Bewertungsparameter. Marktvalidierung ist nicht erfolgt.

## M2 – analytische Greeks (#22)

`option_greeks(S, K, T, sigma, r, dividend_yield=q, kind="call")`
liefert `OptionGreeks(delta, gamma, vega, theta, rho)` in der Broadcast-Form
aller Eingaben. Theta pro verstrichenem Jahr; Vega/Rho je 1,0 Dezimaländerung,
`vega_per_percent`/`rho_per_percent` je Prozentpunkt. Quotes je Underlying,
kein impliziter Multiplikator. Die Greek-API erfordert S,K,T,sigma > 0;
Preisbewertung unterstützt weiterhin null. Siehe [Verträge](18_M2_CONTRACTS.md).

Red: `pytest tests/test_greeks.py` scheiterte nach intakter Installation am
fehlenden `option_greeks`-Import. Green/Refactor: 147 Tests bestanden, ruff
check/format und mypy grün. Differenzen verwenden für Spot einen relativ zum
Kurs skalierten Schritt: absolute 1e-4-Währungsschritte verursachten bei Gamma
Auslöschung; Toleranzen wurden nicht aufgeweitet. Paritätsableitungen und
analytische ATM-Referenz prüfen unabhängig von den Preis-Differenzen.
