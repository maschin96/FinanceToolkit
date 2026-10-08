# Yahoo-Marktdaten (#45)

Installieren: `uv sync --locked --extra yahoo` (oder `finance-toolkit[yahoo]`).
Der optionale Provider yfinance 1.7.0 und Repair-Abhängigkeiten sind in uv.lock
reproduzierbar gesperrt. Numerische Kernimporte laden weder yfinance noch pandas.
Die CI installiert plots/yahoo auf Python 3.11–3.13; alle Tests bleiben offline.

```sh
python -m finance_toolkit.yahoo history AAPL MSFT --start 2026-09-28 --end 2026-10-08 --cache outputs/yahoo --output outputs/history.json
python -m finance_toolkit.yahoo history AAPL MSFT --start 2026-09-28 --end 2026-10-08 --cache outputs/yahoo --offline --output outputs/replay.json
python -m finance_toolkit.yahoo quote AAPL MSFT
python -m finance_toolkit.yahoo watch AAPL --count 5 --interval 30
```

Daily start inklusiv, end exklusiv, interval explizit 1d. Aktuelle Quote ist der
letzte reguläre Marktpreis mit Marktzeit und Abrufzeit, nicht notwendig ein Tick
von jetzt. Alter in Sekunden wird ausgewiesen; unbekannte Börsenverzögerung
bleibt null, unbekannter Sessionstatus UNKNOWN. Online bedeutet frisch abgerufen,
nicht garantierte Echtzeit. Native Streams sind im Adapter ausdrücklich nicht
unterstützt; `stream` scheitert konkret, `watch` ist bewusst endliches Polling.
Strg-C beendet Watch mit Exitcode 130. Keine stillen Fallbacks.

`YahooClient` hat Timeout pro Providerrequest (default 10 Sekunden), höchstens
0..5 Retries (default 2), exponentielle Backoff .5/1/2/4/8 Sekunden. Eine
Batchantwort muss alle angefragten Symbole liefern; Leer-/Partial-/Schemafehler
werden mit Symbol als DataError abgelehnt. Clock, Sleep und Provider sind
injizierbar. Normale CLI-Fehler liefern Exitcode 1. Datum und Symbolduplikate
werden vor Netzwerkzugriff geprüft. Es gibt keine Zugangsumgehung.

Quotes und Bars tragen Currency, Exchange, IANA-Zeitzone, aware Zeitstempel und
Quelle. GBp/ZAc/ILA werden explizit zu GBP/ZAR/ILS mit Faktor .01 normalisiert;
Originaleinheit/Faktor und zurückgegebene Providerrecords bleiben im Audit.
OHLC muss positiv endlich und konsistent sein, Volumen/Aktionen nichtnegativ.
Daily-Zeitstempel sind Barlabels, keine Tickzeiten. Unsortierte, doppelte
Zeitstempel/Sessions, fehlende Metadaten und NaNs werden abgelehnt; kein Füllen.

Explizite Flags: auto_adjust=False, back_adjust=False, actions=True,
repair=False (nur mit `--repair` opt-in), keepna=True, rounding=False.
Yahoo Close ist bereits splitbereinigt; Adj Close zusätzlich dividendenbereinigt.
Die Bezeichnung unadjusted ist keine Zusage historischer Originalpreise vor Splits.
Dividend/Splitfelder werden separat aufbewahrt, nicht nochmals auf Adj Close
angewandt. Repair-Flag dokumentiert angefragte Providerreparatur, keine
selbständige Validierung. Rawrecords sind Provider-Rückgabe vor unserer
Einheitenkonversion; bei opt-in Repair nicht die unveränderte Yahoo-Rohantwort.

Cache speichert angefragte Identität, Records, Audit und SHA256-Datenhash.
Offline-Replay liest ausschließlich Cache, auch ältere Daten: source_mode=cache
und ursprüngliche Abrufzeit bleiben sichtbar. Kein stiller Online-Fallback.
Der Hash schützt Reproduzierbarkeit/versehentliche Änderungen, ist keine Signatur.
Cache/Downloads bleiben in ignorierten outputs oder /tmp, niemals in Git.

## Verifikation

15 synthetische Offline-Tests: native Providergrenze inklusive MultiIndex,
Einheiten, leere/partielle/NaN-Antworten, DST, begrenzte Retries, unbekannte
Quoteverzögerung, Polling, unsupported Stream, Cachehash und Offline-CLI.
Red: fehlendes Modul; zusätzlicher Live-Schema-Bug als roter Regressionstest
(Provider konvertiert regularMarketTime zu aware Timestamp), danach grün.

Separater Live-Smoke 2026-10-08 10:32:51–10:32:52 UTC, yfinance 1.7.0,
AAPL/MSFT, Timeout 8s, null Retries: Daily-Historien 2026-09-28 bis exklusiv
2026-10-08 mit je acht Bars und beide neuesten regulären Quotes erfolgreich.
Vorheriger Smoke um 10:31:51 UTC: History erfolgreich, Quote-Time-Schemafehler;
Regression und Korrektur oben dokumentiert. Keine Marktdatenwerte eingecheckt.
Dies prüft Adapterzugriff, keine empirische Modellvalidierung oder Verfügbarkeit
zu anderen Zeiten. CI benötigt keinen Yahoo-Zugriff.

## Primärquellen und Nutzungsrechte

[Providerprojekt](https://github.com/ranaroussi/yfinance),
[History-API](https://ranaroussi.github.io/yfinance/reference/api/yfinance.Ticker.history.html),
[Historyimplementierung](https://github.com/ranaroussi/yfinance/blob/main/yfinance/scrapers/history.py),
[Yahoo Börsen/Verzögerungen](https://help.yahoo.com/kb/SLN2352.html).
Die Apache-2.0-Lizenz von yfinance lizenziert Software, keine Yahoo-Marktdaten.
Das Providerprojekt ist nicht von Yahoo autorisiert und verweist auf dessen
Nutzungsbedingungen/persönliche Datennutzung. Keine Weiterverteilungsrechte
an Downloads werden durch diese Toolbox behauptet.
