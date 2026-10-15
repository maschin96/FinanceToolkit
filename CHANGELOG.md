# Änderungen

## Unveröffentlicht – 0.4.0 (M5)

- Optionale Textual-TUI mit sechs tastaturbedienbaren Ansichten und begrenzten,
  abbrechbaren Hintergrundjobs (#74, #75).
- GBM-/Portfolioformulare, Tradeeditor, Pfad-/Zeitwahl, Risiken, Greeks und
  benannte Stressszenarien mit Terminalraster (#76, #77).
- Gemeinsame Rebalancing-/Options-/Hedgevergleiche, dynamische Orders und
  vollständige P&L-Attribution (#78).
- Synthetische Indexdemo, Cache-Replay, Datenvorschau und ausschließlich
  ausdrücklich ausgelöste Yahoo-Abrufe (#79).
- Versionierte Konfigurationen, exakte CSV/JSON-Exporte mit Parametern, Einheiten,
  Versionen/Hashes, Überschreibschutz und Abbruch-/Fehlerbehandlung (#80).
- Voll-, Kern- und TUI-Installationsprofile mit expliziten Skiplisten und
  isolierten Wheeltests; manuelle Terminalabnahme vor Release noch offen (#81).

Keine neuen Finanzmodelle oder numerischen Diskretisierungen. Keine empirische
Marktvalidierung, Windows-Supportzusage oder PyPI-Veröffentlichung.
[Abnahmestand](Doc/38_M5_TUI_VERIFICATION.md).

## 0.3.1 – 2026-10-13

- Einheitliche Fälligkeitstoleranz für Optionsbuch und Attribution, einschließlich
  einmaligem Settlement, Long/Short und Vertragsmultiplikatoren (#58).
- Separate Attributionspfade `hedge/<name>` und `strategy/<name>` mit Manifest;
  gleichnamige Bücher überschreiben sich nicht mehr (#59).
- Endliche numerische Ergebnisverträge und robuste Nettoaggregation bei großen
  gegenläufigen Positionen; explizite Fehler statt inf/nan (#60).
- BSM-Grenzfälle berechnen ausschließlich benötigte Zweige (#61).
- Yahoo-Historien prüfen lokale Sitzungsdaten gegen das inklusive/exklusive
  Requestintervall, online und beim Offline-Replay (#62).
- Separates Basisprofil ohne Extras; vollständige Python-3.11–3.13-Matrix
  ohne Testauslassungen (#63).
- Einheitliche knappe CLI-Eingabefehler ohne Traceback und frühe Index-JSON-
  Validierung vor Providerzugriff (#64).
- Lokale Wiederverwendung von Vermögen und Reconciliation in Attribution/
  Export; identische numerische Ergebnisse und Exportdateien (#65).

Wartungsrelease ohne neue Finanzmodelle oder Pflichtabhängigkeiten.
[Gesamtverifikation](Doc/30_M4_VERIFICATION.md), Releaseabschluss #66.
Keine empirische Marktvalidierung und keine PyPI-Veröffentlichung.

## 0.3.0 – 2026-10-08

- Dynamisches Optionsbuch mit pfadabhängigen Orders, Settlement und Cashbilanz.
- Explizite Kredit-/Anlagezinsen, Aktien-Shorts und Aktienleihekosten.
- Verzögertes Kalender-/Schwellen-Delta-Hedging mit gekoppelter Rasterreferenz.
- Protective Put, Covered Call, Collar und vertikale Optionsspreads.
- Exakte P&L-Reconciliation und lokale Greek-Näherung mit Ereignis-/Restfehlern.
- Reproduzierbares Hedge-Lab mit gemeinsamen Pfaden, CSV/JSON und PNG.
- Optionaler Yahoo-Adapter mit Einheiten-/Zeit-Audit, Cache und Offline-Replay.
- Eigene Kurs-/Total-Return-Indizes mit verzögertem Rebalancing und Offline-Demo.
- Vollständige Python-3.11–3.13-CI mit allen vier Offline-CLIs und Wheel-Prüfung.

Keine empirische Validierung, keine garantierte Echtzeit oder Marktdatenrechte.

## 0.2.0 – 2026-10-08

- Analytische BSM-Greeks mit Broadcasting und expliziten Einheiten/Grenzen.
- Portfolio-Exposures je Position/Underlying; Anleihen-DV01 und Konvexität.
- Vollständige Snapshot-Neubewertung unter Spot-/Volatilitäts-/Zinsschocks.
- Pfadabhängige Long-only-Aktien-/Cash-Strategien mit verzögerter Ausführung,
  Cashbegrenzung, festen/proportionalen Gebühren und expliziter Finanzierung.
- Kalender- und Schwellen-Rebalancing einschließlich Cashrest.
- Reproduzierbares Offline-Risk-Lab mit CSV/JSON und optionalen PNGs.
- Bestehende M1-APIs und Arrayformen erhalten; keine neuen Pflichtabhängigkeiten.

## 0.1.0 – 2026-10-07

Erster vollständiger M1-Funktionsumfang:

- Korrelierte exakte GBM-Aktiensimulation mit reproduzierbaren Seeds/Generatoren.
- Europäische Calls/Puts, Black-Scholes-Merton, Payoffs und deterministische Grenzen.
- Kupon-/Nullkuponanleihen, Stückzinsen, Clean-/Dirty-Bewertung und Zinsszenarien.
- Long-/Short-Trades, Ausführungspreise, Gebühren, Finanzierung und einmalige Zahlungen.
- Portfolioverläufe, P&L, Rendite, Drawdown, aggregierter VaR/Expected Shortfall.
- Offline-Beispiele, CSV/JSON und optionale Matplotlib-Diagramme.
- Python 3.11–3.13, gelockte Abhängigkeiten, Tests, Lint/Format, strikte Typprüfung,
  Paketbau und frische Wheel-Prüfung in der CI-Matrix.

Numerisch verifiziert; keine empirische Marktvalidierung. Öffentliche GitHub-Artefakte,
keine PyPI-Veröffentlichung. Grenzen und Referenzen im M1-Verifikationsbericht.
