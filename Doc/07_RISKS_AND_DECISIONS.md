# Architektur und Entscheidungen

## ADR-001 – Finance-Projekt statt FEM (2026-10-07)

Das vorhandene AGENTS.md stammt aus einer FEM-Toolbox. Fachbegriffe und Paketpfad
werden auf Finance übertragen. Issue-/Milestone-Workflow, TDD und Qualitätsregeln
bleiben erhalten. Es existieren keine FEM-Module oder Referenzdaten.

## ADR-002 – Modelle und Konventionen

- Zeit: Jahre; Zinssätze, Drift und Volatilität annualisiert, Raten dezimal.
- Eine konfigurierbare Währung; keine implizite Währungsumrechnung.
- Aktien: exakte GBM-Schritte. Realwelt-Drift mu für Szenarien; r-q für
  risikoneutrale Bewertung. Korrelation beschreibt Brownsche Inkremente.
- Optionen: europäische Calls/Puts nach Black-Scholes-Merton, stetiger Zins r
  und Dividendenrendite q; Barausgleich. Modellvolatilität wird explizit angegeben.
- Anleihen: ausfallfrei, feste Kupons, regelmäßige Zahlungen; Laufzeit als ganze
  Anzahl Kuponperioden. Flache stetige Discountkurve, getrennt von Kuponrate.
  Szenarien können diese Kurve im Zeitverlauf ersetzen; kein stochastisches Zinsmodell.
- Kuponrate bezogen auf Nennwert und Jahr; Stückzins linear innerhalb der Periode.
  Keine Feiertagskalender oder handelsüblichen Day-Count-Konventionen in M1.
- Beobachtung auf einem gemeinsamen Raster mit allen Trade-, Kupon- und
  Fälligkeitsterminen. Zahlungen am Zeitpunkt zuerst buchen, danach ex-Cashflow
  bewerten. Nach Tilgung/Verfall ist der Instrumentwert null.
- Positive Stückzahl ist Long, negative ist Short. Optionsmultiplikator explizit.
  Transaktionspreise können von Modellwerten abweichen; Gebühren separat.
- Cashfinanzierung: stetiger Zins auf positive/negative Guthaben explizit
  konfigurierbar, Standard ohne Verzinsung; keine Margin-/Liquidationssimulation.
- Totalvermögen umfasst Marktwerte und Cash. P&L bezieht sich auf Anfangsvermögen
  unter Berücksichtigung externer Zu-/Abflüsse; M1 sieht keine externen Zuflüsse vor.
- Verlust = Anfangsvermögen minus Endvermögen. VaR ist das empirische
  Verlustquantil (NumPy-Methode linear); ES ist der Mittelwert der schlimmsten
  (1-alpha)-Wahrscheinlichkeitsmasse mit anteilig gewichtetem Grenzbeobachtungspunkt.
  Bei nichtpositivem Anfangsvermögen ist prozentuale Rendite undefiniert und wird
  abgelehnt. Drawdown wird für positive Vermögensverläufe definiert.

## ADR-003 – Modulgrenzen und Abhängigkeiten

Geplant: simulation, instruments/options, instruments/bonds, portfolio, analytics.
Reine numerische Funktionen; Zufallsgenerator übergeben, keine globalen Seeds.
I/O und Diagramme sind Adapter. NumPy/SciPy (BSD-Lizenzen) sind begründete
numerische Abhängigkeiten; genaue Versionen, Lizenznachweise und optionale
Diagrammbibliothek werden in #2/#8 vor Aufnahme geprüft.

## Modellgrenzen

GBM bildet konstante Volatilität und lognormal verteilte Kurse ab, aber keine
Sprünge oder Volatilitätscluster. Black-Scholes setzt idealisierte Handelsbedingungen
voraus. Shortpositionen können unbegrenzte Verluste verursachen; M1 modelliert
keine Brokeranforderungen. Zinsszenarien enthalten kein Kredit- oder Liquiditätsrisiko.
Numerische Verifikation ist keine empirische Marktvalidierung.
