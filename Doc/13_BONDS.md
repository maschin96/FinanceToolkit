# Anleihen

`Bond(face, coupon_rate, maturity, frequency=1)` modelliert eine ausfallfreie
festverzinsliche Anleihe, ausgegeben bei t=0. Laufzeit in Jahren, nominaler
Jahreskupon als Dezimalzahl, positive ganzzahlige Zahlungsfrequenz.
Maturity*frequency muss ganzzahlig sein (Toleranz 1e-10 Perioden).
`cashflows()` liefert Zahlungstermine und separate Kupon-/Tilgungsarrays.
`price(time, rate=..., clean=False)` diskontiert künftige Zahlungen mit einer
flachen stetigen Zinskurve; Zinsarrays erlauben Szenariovergleiche. Der
Bewertungszeitpunkt ist absolut seit Ausgabe. Negative Zinsen sind erlaubt.

Zahlungen am Bewertungszeitpunkt gelten als bereits gebucht. Der Dirty-Preis
ist deshalb ex-Kupon und am/nach Laufzeitende null. Zahlungszeitpunkte werden
mit 1e-10 Jahren abgeglichen; Stückzinsen sind linear in der Kuponperiode und
an Zahlungsterminen null. Clean = Dirty - Stückzins. Kursnotierung ist in
Währung je Anleihe, nicht in Prozent. Keine Kalender, Steuern, Defaults oder
Handels-Day-Count-Konventionen.

Referenzen: N exp(-rT) für Nullkupons; unabhängig enumerierte diskontierte
Kupons/Tilgung; Parität bei r=frequency*log(1+coupon_rate/frequency).
Absolute Preistoleranz 1e-11 für N=100 bzw. 1e-10 für N=1000 erlaubt wenige
Float64-Rundungsfehler; Cashflows bei ganzzahligen Referenzen exakt geprüft.
Bilanz bei r=0, Kuponsprünge, Clean/Dirty, Tilgung, Zinsmonotonie und ungültige
Parameter sind geprüft. Analytische Diskontierung benötigt keinen
Diskretisierungs-Konvergenztest. Keine Marktvalidierung.
