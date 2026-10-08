# Eigene Aktienindizes (#46)

```sh
python -m finance_toolkit.index_lab --config examples/m3_index_demo.json --demo --output outputs/index-demo --plot
python -m finance_toolkit.index_lab --config examples/m3_index_yahoo.json --cache outputs/yahoo --output outputs/my-index
python -m finance_toolkit.index_lab --config examples/m3_index_yahoo.json --cache outputs/yahoo --offline --output outputs/my-index-replay
```

Das Demo ist eine originale synthetische Handreferenz, keine Yahoo-Daten.
Konfigurationsfelder: feste eindeutige tickers, start inklusiv/end exklusiv,
base_date (vorhandene gemeinsame Sitzung), base_value positiv (default 100),
weights in Ticker-Reihenfolge (default gleich), calendar_policy strict oder
explizites intersection, rebalance buy_and_hold/monthly/explicit und ggf.
rebalance_dates, repair (default false). Es gibt keinen historischen
Marktkapitalisierungsindex aus heutigen Kapitalisierungen und keine FX-Annahmen.

Der reine NumPy-Kern `calculate_index` konsumiert positive bereits konsistent
adjustierte Preise `(Sitzungen, Assets)`, ISO-Daten und Gewichte. Nichtnegative
Gewichte müssen innerhalb 1e-12 Rechenrundung zu eins summieren; nur innerhalb
dieser Toleranz normalisiert. Basis wird exakt auf base_value gesetzt. Danach
bleiben synthetische Stückzahlen konstant; Marktgewichte driften. Rebalancing-
Signale verwenden bekannte Sitzung t, Ausführung zum Preis t+1. Monatlich ist
das Signal die erste beobachtete Sitzung des neuen Monats (ab Basis), ebenfalls
Ausführung erst in der Folgesitzung. Keine zukünftige Monatsend-Erkennung.
Stückzahlen sind Einheiten der adjustierten Serie, keine Rohaktien-Brokerbestände.

`build_indices` übernimmt den Yahoo-Datenvertrag: Kursindex aus splitbereinigtem
Close, separater Total-Return-Index aus dividendenbereinigtem Adj Close. Split-
und Dividendfelder werden auditiert, aber nicht nochmals angewandt. Die
Adjustierung folgt dem Provider und ist keine eigenständige Corporate-Action-
Validierung. Minor Quotes GBp/ZAc/ILA werden vor Aggregation zu GBP/ZAR/ILS
normalisiert; bereits normalisierte Daten nicht nochmals skalieren. Eine
abweichende gemeinsame Währung wird abgelehnt; keine implizite Umrechnung.

Strict verlangt gleiche beobachtete Handelsdaten; intersection ist bewusstes
Opt-in und exportiert alle verworfenen sowie je Symbol fehlenden Sitzungen.
Keine langen Forward-Fills/Nullkurse. Fehlende Basis, ungültige Gewichte,
Duplikate, falsche Adjustierungsmodelle und fehlende relevante Rebalance-Daten
werden abgelehnt. Ein langer Handelsstopp kann im intersection bewusst Daten
entfernen: Ausschlüsse vor Verwendung prüfen, nicht als unauffällig behandeln.

Beiträge je Intervall = Anfangsstückzahl * Preisänderung / Anfangsindex.
Ihre Summe ist die Intervallrendite; erste Rendite/Beiträge null. Rebalancing
ändert den Indexstand nicht, Gebühren/Steuern/FX sind ausgeschlossen.
JSON enthält vollständige Inputkonfiguration, beide Reihen, Bestände/Gewichte/
Beiträge und Datenhash/Abrufzeit/Quelle/Modell/Einheiten pro Symbol. CSV enthält
beide Reihen positionsweise; Indexlevel und Gesamtrendite sind je Ticker
wiederholt und dürfen nicht über Ticker summiert werden. Optional index.png.

## Unabhängige Referenzen

Zwei Assets starten bei 100/100 mit Gewichten .5/.5, Basis 100. Dann Preise
120/80, 150/100, 150/120: Buy-and-hold-Level 100,100,125,135; Gewichte nach
zweiter Sitzung .6/.4. Signal an zweiter Sitzung rebalanced erst an dritter;
Level 100,100,125,137.5. Drei Assets mit .2/.3/.5 und Renditen .1/-.1/.2
liefern Beiträge .02/-.03/.10 und Level 109. Ein Asset folgt seiner korrekten
adjustierten Preisratio. Splitneutrales Close 50/50/49 und Adj Close 49/49/49
zeigen Preislevel 100/100/98 versus Total Return 100/100/100, ohne doppelten
Dividenden-/Spliteffekt.

Indexpunkt-Toleranz 1e-12 absolut und 1e-14 relativ für rationale Stückzahlen
bei Levelgrößen um 100–250; Beitragstoleranz 1e-14 für kleine Bruchsummen.
Basislevel bleibt exakt. Prefix-, Cache-, Kalender-, Währungs-/Einheiten-,
Monatssignal-, CLI-Reproduzierbarkeits- und PNG-Tests ergänzen die Referenzen.
Keine Indexzertifizierung, dynamische Mitgliedschaft oder empirische Validierung.
