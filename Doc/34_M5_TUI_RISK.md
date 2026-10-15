# M5 – Risiko und Stress (#77)

Ctrl+3 öffnet Risiko/Stress. Snapshotpfad und -zeitindex beziehen sich explizit
auf den Zustand nach Trades/Zahlungen am gewählten GBM-Punkt. Die Rechnung
verändert weder Trades noch Cashflows und verwendet dieselben öffentlichen
Portfolio-, Analyse- und Risiko-APIs. Ctrl+R/der Rechnen-Button verwendet den
begrenzten Jobvertrag aus B. Die Portfolioansicht bleibt für Preise/Cash verfügbar.

Konfidenz wird als Prozent eingegeben, z.B. 90 → .9. Terminaler aggregierter
VaR/ES und hypothetische Stress-P&L sind getrennt beschriftet. Rendite-/Drawdown-
Grenzen bleiben in der Portfolioansicht mit Grund sichtbar.

## Schocks und Darstellung

Spot-/Zinslisten und eine gemeinsame Volatilitätsänderung bilden ohne eigene
Szenarien benannte Spot×Zins-Kombinationen. Eigene Szenarien lassen sich mit Namen
anlegen und ausgewählt löschen; ihre Liste ersetzt diese Kombinationen.
Relative Spotänderungen sind in Prozent, absolute Zins-/Volatilitätsänderungen
in Prozentpunkten beschriftet. Ein skalarer Volatilitätsschock betrifft nur
Optionen; eine Positionsliste muss bei Nichtoptionen null enthalten.
Kein Abschneiden negativer gestresster Spots/Volatilitäten: der Kern lehnt
ungültige Kombinationen ab. Ein Nullschock bleibt unverändert null.

Die Stresstabelle zeigt Basis-/Stressvermögen, Portfolio-/Positions-P&L und
unverändertes Cash in der Workspace-Währung. Das terminale Spot-/Volatilitätsraster
verwendet `stress_grid`, mit Volatilitätszeilen und Spotspalten, ohne Matplotlib
oder Wahrscheinlichkeitsinterpretation. Die Ansicht begrenzt sich auf 50×50
Zellen; vollständige Werte verbleiben im Ergebnis für G. UI-Grenzen: höchstens
10.000 Rasterzellen und 100 benannte/Kombinationsszenarien pro Lauf, ohne harte
Laufzeitgarantie. Eingabegrenzen ändern die öffentlichen Kern-APIs nicht.

## Greeks und Einheiten

Delta/Gamma werden je Asset getrennt, Positionen zusätzlich mit Menge und
Optionsmultiplikator dargestellt. Vega ist für einen Volatilitäts-Prozentpunkt,
Rho für einen Zins-Prozentpunkt mit Faktor .01 skaliert. Theta ist in
Währung/Jahr, DV01 in Währung für einen Basispunkt gemäß `−rho×1e−4`;
Bond-Konvexität ist pro Anleihe in Jahren². Die Darstellung ändert keine
Rechenwerte. Positionen folgen derselben Instrumentreihenfolge wie die
Portfolioansicht; kein Summieren ungleicher Asset-Deltas.

Nicht differenzierbare aktive Optionen können den öffentlichen Greek-Aufruf
ablehnen. Der Adapter kennzeichnet die Greeks dann ausdrücklich mit Grund als
undefiniert und setzt keine Nullwerte ein. Gültige Preise/Cash und vollständige
Stress-Neubewertung bleiben verfügbar. Fällige/ausgeglichene Positionen haben
dagegen gemäß Kernvertrag tatsächlich null Sensitivität; ihre bereits gebuchten
Zahlungen verbleiben im Snapshotcash.

## Schema und Verifikation

Schema v1 erhält vor M5-Veröffentlichung die optionalen Felder
`risk.grid_volatility_shocks` (Standard [0,.05]) und `risk.scenarios` (Standard []).
Szenariofelder: name=scenario, spot_shocks=0, volatility_shocks=0, rate_shock=0;
beide Schockarten erlauben Skalar oder passende Liste. JSON enthält Dezimalwerte;
nur Formfelder konvertieren Prozent-/Prozentpunktwerte. Unbekannte Felder und
falsche Typen bleiben abgewiesen, doppelte/leere Namen und übergroße Raster ebenfalls.

Sieben neue Fälle, anfänglich fehlende Services/Formulare rot, nach Umsetzung
grün. Unabhängige Referenzen: 100 Aktien à 100, Cash 10000; −20% Spot ergibt
−2000 EUR Stress-P&L, 18000 EUR Stressvermögen. Nullschock und Gegenpositionen
ergeben exakt null. Nullkupon N=1000, T=1, r=.03: DV01=1000 exp(−.03)×1e−4,
Konvexität 1 Jahr²; nach Tilgung Sensitivität/Raster null. Geldtoleranz absolut
1e−10 EUR bei 20000 EUR Vermögen; DV01 absolut/relativ 1e−12 wegen der kleineren
Derivatgröße. Negative Spots/Volatilitäten und nichtendliche Schocks werden
abgelehnt. Nonsmooth-Greek-Fall erhält Cash/Preis und gültige Stresswerte.
Pilot prüft Snapshot-/Konfidenzeingabe, benannte Szenarien, Raster und Abbruchpfad
über den bereits verifizierten Jobvertrag. Keine Live-Dienste.

Lokal macOS/Python 3.13.5: Vollprofil 464 bestanden; Basis 450 bestanden und
14 benannte Skips (acht UI-, sechs Diagrammfälle); tui ohne plots/yahoo
458 bestanden, sechs Diagramm-Skips. ruff check/format, striktes mypy (31 Module),
git diff --check und Paketbau erfolgreich. Neue Fälle zusätzlich im aktuellen
Wheel außerhalb des Quellbaums geprüft; aktuelle CI ist Integrationsvoraussetzung.
Eigenreview, kein unabhängiger Reviewer verfügbar. Keine empirische Validierung.
