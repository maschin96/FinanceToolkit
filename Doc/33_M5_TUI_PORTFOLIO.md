# M5 – Simulation und Portfolio bedienen (#76)

Ctrl+2 öffnet das scrollbare Simulations-/Portfolioformular. Tab/Shift+Tab und
Enter reichen für Felder, Tradeauswahl und Buttons aus; Tabellen unterstützen
Pfeiltasten und horizontales Scrollen. Der Seed steht in der Startansicht
(Ctrl+1). Ctrl+R rechnet mit einem eigenen Snapshot im Hintergrund.

## Eingaben

Spots, reale Drifts und GBM-Volatilitäten werden als Komma-Listen in derselben
Assetreihenfolge eingegeben, z.B. 100,200 / 6,4 / 20,10. Drifts und
Volatilitäten sind in Prozent pro Jahr beschriftet und werden genau einmal
in Dezimalzahlen umgerechnet. Korrelation verwendet Kommas pro Zeile und
Semikolon zwischen Zeilen, z.B. `1,.5; .5,1`; leer bedeutet Identität.
Horizont ist in Jahren, Schritte/Pfade sind positive ganze Zahlen.
Eine gemeinsame Währung, Anfangscash, Bewertungs-, Guthaben- und Kreditzins
sind einstellbar; kein FX. Simulations- und Options-Modellvolatilität bleiben
getrennt. Die Preiszellenbegrenzung aus [A](31_M5_TUI_CONTRACTS.md) gilt weiter.

Trade hinzufügen/ändern öffnet ein scrollbares Formular. Instrumenttag:
stock=Aktie, call=europäischer Call, put=europäischer Put, bond=Anleihe.
Assetnummern beginnen bei 0. Je Instrument gelten die beschrifteten
Strike-/Fälligkeits-/Volatilitäts-/Multiplikator-/Dividenden- bzw.
Nennwert-/Kupon-/Frequenzfelder. Menge ist vorzeichenbehaftet, Gebühren absolut
in Währung; eine leere Ausführungsquote verwendet den Modellpreis.
Escape/Abbrechen verwirft einen Dialogentwurf. Der Löschbutton betrifft die
ausgewählte Tradezeile. Das statische Buch übernimmt die vorhandene
Short-/Cashkreditkonvention ohne Margin; dynamische Freigaben folgen in E.

Raster müssen Trades, Optionsfälligkeiten, Kupons und Tilgung enthalten.
Ungültige Raster werden vom Kern konkret abgelehnt; keine stille Rundung oder
Verschiebung. Ungültige Formfelder blockieren Rechnung und Tradeänderungen,
anstatt alte Eingaben heimlich zu verwenden. Mehrfeldänderungen wie zusätzliche
Assets dürfen vorübergehend inkonsistent sein; der Entwurf bleibt erhalten,
bis alle Vektoren zusammen validieren. Jede Eingabeänderung macht alte Resultate
sichtbar veraltet, auch wenn der Entwurf ungültig ist.

## Ergebnisse und Exportgrenze

Pfad- und Zeitindex sind reine Anzeigeauswahlen und erfordern keine neue Rechnung.
Die Ansicht nennt Lauf-ID, Zeit in Jahren, Währung, Bestände, per-unit Quotes,
Cash, Vermögen und P&L. Optionsquotes sind je Underlying, Positionswerte
berücksichtigen Menge und Multiplikator. Anleihen zeigen Dirty/Clean/Stückzins
je Anleihe. Nach Zahlung/Abrechnung ist die Ansicht ex-event.

Renditen sind bei nichtpositivem Anfangskapital mit Grund undefiniert; Drawdown
bei nichtpositivem Vermögen ebenfalls. Absolutes Vermögen/P&L bleiben sichtbar.
Mittleres Endvermögen ist ausdrücklich über alle Pfade aggregiert; terminaler
VaR/ES bezieht sich auf den aggregierten Portfolioverlust. Risiko-/Stressformulare
und Greeks stehen in [D](34_M5_TUI_RISK.md). Die Sparkline ist als Zeitverlauf des gewählten
Pfads beschriftet. Die Tabelle zeigt höchstens 50 Zeitpunkte ab Auswahl;
die Sparkline höchstens ungefähr 80 Stützpunkte. Eine neue Rechnung entfernt
die vorherige Ergebnisdarstellung bis zur erfolgreichen Rückgabe.

`PortfolioResult` enthält alle unveränderten Rechenarrays. `portfolio_payload`
ist die frühe numerische Exportgrenze: JSON-Primitives mit Parametern, Einheiten,
Array-Achsen, Instrumentidentitäten und vollständigen Arrays ohne Anzeigerundung.
Dateidialoge, CSV, Provenienz und Überschreibschutz folgen in #80. Der Test mit
65 Zeitpunkten prüft vollständige Nutzdaten unabhängig von der 50-Zeilen-Anzeige.

## Verifikation

Neue Red-Fälle: fehlende Formularparser/-felder, Positionsquoteadapter und
Exportgrenze; zusätzlich reproduzierter Fehler bei Korrektur eines ungültigen
Felds auf dessen ursprünglichen Wert. Green/Refactor nach Implementierung.
Pilot prüft Formularänderungen, Trade-Anlegen/Ändern/Löschen, Rechnung,
Pfad-/Zeitwahl und bleibende Eingabeblockade bis Korrektur (80×24/120×40).

Unabhängige Referenzen, jeweils Währung EUR: Cash 797 nach 2 Aktien à 100
und Gebühr 3 bei Kapital 1000; Endvermögen 797+200 exp(.06) bei sigma=0.
BSM-Parität bei S=K=100, T=1, r=.03, q=0: C−P=100−100 exp(−.03), per
Underlying. Anleihe N=1000, Kupon=.04, halbjährlich: 20+20 Kupons,
1000 Tilgung; Zwischenpreis 1020 exp(−.03×.5). Nach Fälligkeit Positionen null.
Multiasset-/Short-/Multiplikatorreferenz: Short zwei Aktien à 200,
Long zwei Calls mit Strike 90, Spot 100, sigma=r=0 und Multiplikator 10;
Cash 1200, terminale Abrechnung 200, Vermögen konstant 1000.
Absolute Toleranz 1e-10 EUR bei Größenordnung 1000 EUR deckt Rundung ab,
relative Toleranz höchstens 1e-12; keine Modell-/Diskretisierungstoleranz.
Nichtpassende Tradezeiten .1/.9 bei Raster 0/.5/1 werden ausdrücklich abgelehnt.
Bestehende wissenschaftliche Nachweise bleiben unverändert verpflichtend.

Lokal macOS/Python 3.13.5: Vollprofil 457 bestanden; Basis 444 bestanden mit
genau 13 benannten Skips (sieben UI-, sechs Diagrammfälle), tui ohne plots/yahoo
451 bestanden mit sechs Diagramm-Skips. ruff check/format, striktes mypy
(30 Module), git diff --check und Paketbau erfolgreich. Acht neue
Portfolio-/Parser-/Exportgrenzenfälle auch im aktuellen Wheel außerhalb des
Quellbaums bestanden. Geldtoleranzen im A-Test sind nun ebenfalls explizit mit
rtol=0/atol=1e-10 angegeben; keine Erwartungen gelockert. Aktuelle CI bleibt
Integrationsvoraussetzung; kein unabhängiger Reviewer verfügbar.
