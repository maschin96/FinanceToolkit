# M3 Optionsbuch

`finance_toolkit.options_book.simulate_book` verarbeitet einen `GBMPaths`-Markt,
ein festes Tupel eindeutiger `Stock`/`EuropeanOption`-Instrumente, Anfangscash und
`Order`-Sequenzen. `Order.instrument` ist der nullbasierte Positionsindex,
`quantity` signed Stückzahl/Verträge. Ein optionaler Ausführungspreis ist je
Underlying-Einheit; `fee` ist eine absolute Währungsgebühr. Zusätzlich gelten
fixe und proportionale Gebühren pro Order. Mehrere Orders werden in der angegebenen
Reihenfolge verbucht; die resultierende Cash-/Aktienposition muss zulässig sein.

Zeit ist in Jahren, Cash und Marktwerte in einer gemeinsamen Währung. Raster
startet bei null und steigt strikt; Preise sind positiv endlich. Innerhalb des
Horizonts liegende Fälligkeiten müssen im Raster enthalten sein (1e-10 Jahre
Zuordnungstoleranz). Aufgeschobene Trades an/nach Fälligkeit sind Fehler.
Instrumentuniversum und aktuelle Beobachtungen werden im `BookState` geliefert;
Arrays sind eigene schreibgeschützte Kopien. Callback hat keinen Zukunftszugriff.

`BookPaths` enthält Mengen, Modellquotes, signed Positionswerte, signed Trades,
Prämiencashflows, positive Gebühren/Turnover und signed Abrechnung als Arrays
`(Pfade, Zeiten, Instrumente)`. Cash/Finanzierung sind `(Pfade, Zeiten)`.
Cashbilanz: Anfangscash plus kumulierte Prämien minus Gebühren plus Abrechnung
plus Finanzierung. Vermögen = Cash plus Positionswerte. Fälligkeit ist kein
Verkauf; Mengen werden gelöscht. Modellzins und instrumenteigene Volatilität
sind explizit, unabhängig von der Szenariodrift.

Handreferenzen in `test_options_book.py` rekonstruieren Teilverkauf, vollständige
Schließung, mehrere Fälligkeiten, Long/Short und pfadabhängige Ausführung.
Toleranzen 1e-10 Währung absolut und 1e-14 relativ decken Rundung von kleinen
Summen bei Kapitalgrößen um 1000 ab; ganzzahlige Ereignismengen werden exakt geprüft.

## Finanzierung (#40)

`allow_short_stocks` und `allow_borrowing` sind standardmäßig false und müssen
Boolesche Werte sein. Optionsshorts benötigen keinen besonderen Schalter; etwaige
Cashdefizite dennoch die explizite Kreditfreigabe. `lending_rate`/`borrowing_rate`
sind separate endliche stetige Jahresraten, Standard null. Auf den Cashstand am
Intervallbeginn wird `cash * expm1(rate * dt)` gebucht. Danach fallen Aktienleihe-
Modellkosten `max(-shares,0) * previous_spot * stock_borrow_rate * dt` an,
positionsweise in `stock_borrow_costs`; Standard null, negative Kostensätze verboten.
Gebühren bleiben hiervon getrennt. Kein Broker-, Margin- oder Verfügbarkeitsmodell.

Cashbilanz ergänzt um minus kumulierte Aktienleihekosten. Absolute Vermögen und
P&L bleiben auch bei Null/negativem Vermögen verfügbar; `weights` lehnt solche
Verläufe ausdrücklich ab. Handreferenzen prüfen positive/negative Exponential-
finanzierung und die linke Intervallbewertung beim Teil-Cover eines Aktien-Shorts.
