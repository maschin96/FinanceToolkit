# Europäischer Strategiebaukasten (#42)

`build_strategy` erzeugt `OptionStrategy` mit gewöhnlichen Instrumenten/Mengen,
`orders()` für M3 und `trades()` für M1. `close=True` liefert Gegenorders;
deren Ausführungszeit muss vor Fälligkeit liegen. Asset, Fälligkeit,
Volatilität, Dividend-Yield und Multiplikator werden gemeinsam für alle Options-
Legs vergeben. Positive Vertragszahl, gültiges Asset und 0 < lower < upper gelten.

Für n Verträge, Multiplikator m, kL < kU und terminalen Spot S:

| Strategie | Legs | Payoff / (n m) |
| --- | --- | --- |
| Protective Put | n m Aktien, n Put kL | max(S,kL) |
| Covered Call | n m Aktien, -n Call kU | min(S,kU) |
| Collar | n m Aktien, n Put kL, -n Call kU | min(max(S,kL),kU) |
| Bull Call | n Call kL, -n Call kU | min(max(S-kL,0),kU-kL) |
| Bear Put | n Put kU, -n Put kL | min(max(kU-S,0),kU-kL) |

`payoff` ist die unfinanzierte Leg-Summe am gemeinsamen Verfall, ohne Cash.
Profit entsteht erst nach Abzug des signed Opening-Premiums und Gebühren sowie
Addition der separat gebuchten Cashfinanzierung/Leihekosten. Die Payoff-Grenzen
sind daher keine garantierten Grenzen des finanzierten Gewinns. Die fünf
Handreferenzen verwenden Spots unter/auf/zwischen/über Strikes und zwei Verträge;
M1- und M3-Ledger liefern dieselben Werte (1e-10 Währung absolute Rundungstoleranz).
