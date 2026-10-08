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

## ADR-004 – GBM-API und Typprüfung (2026-10-07)

GBM liefert Zeitraster plus dreidimensionalen Preisarray; einzelne Aktien bleiben
auf der Asset-Achse erhalten. Eigenwertzerlegung unterstützt positiv semidefinite
Korrelationen einschließlich Rangdefizienz. RNG ist lokal oder explizit übergeben.
Matrixtoleranz und numerische Fehler sind in Doc/11_GBM_SIMULATION.md festgelegt.
Das gleichmäßige Raster ist die erste Simulations-API; die spätere Portfolio-API
muss Zahlungs-/Tradezeiten darauf ausrichten oder ein separates Zeitraster ergänzen.

mypy verwendet den laufenden Python-Interpreter statt einer pauschalen 3.11-
Einstellung: NumPy-Versionen für neuere Python-Versionen liefern neuere Stub-Syntax.
Die komplette CI-Matrix prüft Quellcode und Abhängigkeiten für jeden unterstützten
Interpreter; die Typprüfung bleibt strikt.

## ADR-005 – M1-Abnahme und Analysekonventionen (2026-10-07)

Optionsquotes je Underlying-Einheit; Multiplikatoren auf Vertragsebene. Coupons
und Tilgung getrennt; Zahlungen vor Trades und ex-Zahlungsbewertung. Ein Käufer
am Kupontermin erhält keinen vorherigen Kupon. Verlust wird vor VaR-/ES-Berechnung
auf Gesamtportfolioebene aggregiert. ES nutzt fraktionale empirische Tail-Masse;
VaR lineare Quantile. Nichtpositive Kapitalbasis liefert keine relative Rendite,
aber weiterhin absolute P&L/Risiken. Aktien-Cashdividenden und Außenkapitalflüsse
sind in M1 ausgeschlossen. Details in Doc/12_OPTIONS.md bis Doc/15_ANALYTICS.md.

Diagramme sind ein optionaler Matplotlib-Adapter, kein numerischer Kern. Die
Release-Matrix installiert den Adapter, damit kein Pflichtnachweis übersprungen
wird. Nur fehlende optionale Matplotlib-Imports toleriert mypy; der Kern bleibt
strikt. CI-Actions nutzen Node-24-fähige SHA-Referenzen und Ubuntu 24.04.

## ADR-006 – M2 Risk Lab und Strategiepfade (2026-10-08, #21)

[API-Verträge und Referenzen](18_M2_CONTRACTS.md) legen Einheiten, glatte
Greek-Domäne, Stress-Snapshot und Ausführung fest. Preisgrenzfälle bleiben erhalten;
Greek-Grenzen werden abgelehnt statt mathematisch undefinierte Werte zu erfinden.
Separate Strategiepfade erhalten die M1-Mengenform. Verzögerte Ausführung und
Prefix-Invarianz verhindern Zukunftsinformation. Verkäufe vor Käufen mit
Cashbegrenzung liefern einen deterministischen, kreditfreien Kostenvergleich.
Asset-Reihenfolge bei Cashknappheit ist bewusst explizit; sie kann Ergebnisse
beeinflussen und ist keine Optimierung. Keine neuen numerischen Abhängigkeiten.
