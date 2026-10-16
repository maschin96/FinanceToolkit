# M5 – Indizes und optionale Daten (#79)

F7 bietet eine synthetische Offline-Demo, Cache-Replay sowie explizite
Yahoo-Historien-/Quoteabrufe. App-Start und Konfigurationsänderungen laden
keine Daten automatisch. Daten werden zuerst vorbereitet und ihre Quellen,
fehlenden Sitzungen und Ausschlüsse angezeigt. Erst der separate Indexbutton
berechnet Preis-/Total-Return-Index mit diesen Daten.

## Offline, Replay und Online

Standard source=demo verwendet ausschließlich `demo_histories`; die festen
synthetischen Sitzungen sind 2026-01-01/02/05/06 in USD. Start/Ende beschränken
das Intervall, Ende ist exklusiv. Ctrl+R bzw. Demo/Cache prüfen bereitet die Daten
vor. Die Demo benötigt weder yahoo noch plots.

source=replay ruft `YahooClient.history(..., offline=True)` auf: derselbe
Request-/Repair-/Cache-/Hash-/Intervallvertrag wie der vorhandene Adapter,
kein Provideraufruf und kein Online-Fallback bei Fehlern. ursprüngliche Abrufzeit,
Quelle, Währung, Zeitzone, Adjustierung, Einheitenfaktor und Datenhash bleiben
sichtbar. Die Intervalle beziehen sich auf Sitzungsdaten in der jeweiligen
Börsenzeitzone. Gemischte Währungen werden nicht per FX vereinheitlicht.

Online-Historien werden nur mit dem ausdrücklich beschrifteten Yahoo-Abrufbutton
angefordert. Dieser setzt den sichtbaren Datenmodus auf yahoo. Ctrl+R im Modus
yahoo verweist auf diesen Button. Der Quoteabruf besitzt eine eigene Online-
Aktion und verwendet Ticker/Timeout/Retries unabhängig vom Indexdatenmodus.
Ein fehlendes yahoo-Extra, Cache-Miss, Provider-/Timeout-/Datenfehler erhalten
konkrete Meldungen und eine F2-Diagnose. Repair ist ein ausdrückliches Opt-in
für Historien; Timeout pro Abruf und 0–5 Retries folgen dem vorhandenen Client.
Alle Online-Aktionen verwenden den begrenzten Job-/Abbruchvertrag aus B.

Quotes sind reguläre Marktpreise mit tatsächlicher Markt-/Abrufzeit, Quelle,
Währung, Börse, Zeitzone und Session. Unbekannte Verzögerung bleibt unbekannt;
es gibt keine Echtzeitzusage. Keine neuen Datenprovider, Streams oder Kalibrierung.

## Indexparameter und Ergebnis

Ticker, Datumsintervall, Basisdatum/-wert, Gewichte, strict/intersection und
Rebalancing sind editierbar. Gewichte sind Dezimalanteile mit Summe 1; leer
verwendet gleiche Gewichte. Monatsregel und explizite Signaltermine schließen
sich aus. Die vorhandene Index-API bestimmt Signal-/Ausführungszeit und füllt
keine fehlenden Preise auf. Ausschlüsse/fehlende Sitzungen werden vor der
Berechnung sichtbar. Gewichts-/Kalenderänderungen können dieselben Daten
verwenden; geänderte Ticker/Intervalle/Quelle/Cache-/Repairidentität verlangen
eine neue Datenvorschau.

Preisindex und Total Return sind getrennt in Indexpunkten bezeichnet.
Kursreihen sind splitbereinigt,
Total Return verwendet dividendenbereinigtes Adj Close; keine doppelte
Corporate-Action-Anwendung. Driftgewichte und Intervallbeiträge haben getrennte
Spalten. Ansicht maximal 50 Sitzungen und 50 Ticker pro Beitragstabelle;
vollständige Ergebnisse bleiben erhalten. Die Indexdatenwährung wird tatsächlich
aus der Quelle angezeigt; eine separat konfigurierte Portfolio-Währung wird
nicht als FX-Konversion auf diese Daten angewandt.

## Verifikation

Vier anfängliche Red-Fälle wegen fehlender Adapter/Formulare, danach grün;
sechs finale Fälle einschließlich zweier Pilotabläufe. Alle Daten sind synthetisch,
keine Live-Netztests und keine Systemzeitabhängigkeit. Ein Provider-Fake prüft
Online-Opt-in, Repair, Cache-Replay ohne zusätzlichen Aufruf und Quotedaten.
Pilot prüft Datenvorschau → Index sowie fehlenden Abruf am Start/Ctrl+R im
Yahoomodus, expliziten Abruf und Cache-Miss ohne Provider-Fallback.

Unabhängige Zwei-Asset-Referenz, Startkurse jeweils 100: A=100/120/150/150,
B=100/80/100/120. Gleiche Gewichte ergeben 100/100/125/135 Punkte,
Gewichte .2/.8 ergeben 100/88/110/126. Absolute Toleranz 1e−10 Indexpunkte
bei ~100 Punkten; Beitragsbilanz gegen Intervallrendite 1e−12 Dezimalanteile.
Strict-Kalender und gemischte Währungen werden abgelehnt; ein geänderter Ticker
erzwingt neue Daten. Bestehende Split-/Dividenden-, Minor-Unit-, Cachehash-,
Intervall-/DST- und Retryreferenzen bleiben unverändert in der Gesamtsuite.

Lokal macOS/Python 3.13.5: Vollprofil 482 bestanden; Basis 465 bestanden und
17 benannte Skips (elf UI-, sechs Diagrammfälle), tui ohne plots/yahoo
476 bestanden mit sechs Diagramm-Skips. ruff check/format, striktes mypy
(33 Module), git diff --check und Paketbau grün. Neue Fälle zusätzlich im
aktuellen Wheel außerhalb des Quellbaums geprüft. Aktuelle CI vor Integration
abwarten; Eigenreview, kein unabhängiger Reviewer verfügbar. Keine Marktvalidierung.
