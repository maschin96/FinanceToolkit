# M5 – TUI-Verträge und Installationsprofil (#74)

Dieser Bericht dokumentiert Paket A vom 2026-10-14 auf stabilem M4/v0.3.1.
Die folgende Parametertabelle ist der damalige Schema-Startstand. Die Ergänzungen
der Pakete B–G stehen in den jeweiligen Bedienberichten und im aktuellen
`config.py`; [Gesamtstand und Release-Gates](38_M5_TUI_VERIFICATION.md).

## Installation und Einstieg

`uv sync --locked --extra tui` installiert Textual 8.2.8. Start:
`uv run --no-sync finance-toolkit-tui` oder
`uv run --no-sync python -m finance_toolkit.tui`. `--help` funktioniert auch
ohne Extra. Ohne Textual liefert ein Start Exitcode 2 mit Installationshinweis,
ohne Traceback. Kern, Konfigurations-/Serviceimporte und die vier bisherigen
Offline-CLIs importieren weder Textual noch Yahoo/Matplotlib.

Textual wird erst im Einstieg geladen. Die Konfigurationsgrenze ist
`decode_workspace`/`encode_workspace`; `run_portfolio` ist der erste Service.
Er ruft ausschließlich `simulate_gbm`, `value_portfolio` und
`analyze_portfolio` auf. Öffentlich typisierte Dataclasses und striktes mypy
schließen die Adapter ein. Weitere öffentliche Kern-APIs sind im
[M5-Plan](29_M5_TUI_ROADMAP.md) den Ansichten zugeordnet.

## JSON-Konfiguration v1

Jeder Schlüssel entspricht dem gleichnamigen Feld in
`src/finance_toolkit/tui/config.py`. Fehlende Felder übernehmen die unten
genannten Standardwerte; unbekannte Felder/Versionen, falsche Typen,
Bool als Zahl und nichtendliche Zahlen werden abgelehnt. JSON-Listen werden
zu eigenen Tupeln, verschachtelte Objekte zu eingefrorenen Dataclasses.
Decoding liest keine Dateien, ruft keinen Provider und rechnet nicht.
Speichern/Laden und Schema-Roundtrip im App-Ablauf folgen in G.

| Abschnitt | Parameter und Standardwerte |
| --- | --- |
| Workspace | schema_version=1; currency=EUR |
| simulation | spots=[100], drifts=[.06], volatilities=[.2], horizon=1, steps=12, paths=100, seed=42, correlation=null |
| portfolio | initial_cash=20000, rate=.03, lending_rate=0, borrowing_rate=0; trades: 100 Aktien von Asset 0 zu t=0 |
| Instrument | kind=stock; asset=0, strike=100, maturity=1, volatility=.2, multiplier=100, dividend_yield=0, face=1000, coupon_rate=.03, frequency=1 |
| Trade | instrument wie oben, time=0, quantity=1, price=null, fee=0 |
| risk | path=0, time_index=0, confidence=.95, spot_shocks=[-.2,0,.2], rate_shocks=[-.01,0,.01], volatility_shock=0 |
| strategy | weights=[.6], calendar=null, threshold=null, fixed_fee=0, proportional_fee=0, option_strategy=protective_put, asset=0, maturity=1, volatility=.2, multiplier=100, dividend_yield=0, strike=100, upper_strike=110, quantity=1, allow_short=false, allow_borrowing=false, orders=[] |
| hedge | option=Call wie oben mit multiplier=1, option_quantity=-1, strides=[1,2], calendar_every=null, threshold=null, fixed_fee=0, proportional_fee=0, stock_borrow_rate=0, allow_short=false, allow_borrowing=false |
| index | source=demo, tickers=[A,B], start=2026-01-01, end=2026-02-01, base_date=2026-01-01, base_value=100, weights=null, calendar_policy=strict, rebalance_dates=[], monthly=false, cache=outputs/yahoo-cache, repair=false, timeout=10, retries=2 |

Instrumenttags sind stock/call/put/bond. Nur die zum Instrument gehörenden
Felder werden an seinen Kernkonstruktor übergeben. Eingaben für Optionsstrategien
sind protective_put/covered_call/collar/bull_call/bear_put, identisch zu
`build_strategy`. Strategy-orders bilden zeitlich geplante öffentliche Trades ab;
deren dynamische Ausführung folgt in E. Index-source ist demo/replay/yahoo;
Online-Aufruf erfordert in F eine gesonderte explizite Benutzeraktion.
Enddatum ist exklusiv. Eine Cache-Referenz allein löst keinen Abruf aus.

## Einheiten und Zuordnung

Zeit ist absolut in Jahren ab Simulationsbeginn. Alle Preise/Cashflows sind in
einer Währung; kein FX. Drift, Volatilität, Zinsen, Dividenden und Kupons sind
annualisierte Dezimalzahlen. Nur explizit mit Prozent beschriftete Formfelder
verwenden `percent_to_decimal`: 3.5 → .035; JSON enthält bereits .035.
Drift und Bewertungszins sowie GBM- und Optionsvolatilität sind getrennt.

Assetindizes folgen der Reihenfolge der spots/drifts/volatilities-Vektoren.
Korrelation ist assets×assets, symmetrisch PSD mit Diagonale 1; absolute
Toleranz 1e-12 entspricht dem bestehenden GBM-Vertrag. Marktpreise haben Achsen
(paths, steps+1, assets); monetäre Portfoliofelder (paths, steps+1),
Positionswerte zusätzlich instruments. Instrumentreihenfolge folgt dem ersten
Auftreten in Trades; Risikoauswahl bezeichnet einen post-event Snapshot.

Positive Menge ist Kauf, negative Verkauf/Short. Optionsquote ist pro
Underlying-Einheit, Vertragswert berücksichtigt den Multiplikator. Gebühren
sind absolute Währungsbeträge je Trade. Statisches `value_portfolio` erlaubt
Shorts/Kredit gemäß bestehendem Vertrag; dynamisches Buch benötigt ausdrückliche
allow_short/allow_borrowing-Freigaben. Keine implizite Margin-Prüfung.

Kupons, Tilgung, Optionsfälligkeiten und Trades müssen auf dem GBM-Raster
liegen. Der Kern lehnt unpassende Raster konkret ab (1e-10 Jahre bestehende
Zeittoleranz); weder Rundung noch Verschiebung. Abrechnung erfolgt einmalig,
Bewertung anschließend ex-payment. Nicht definierte relative Kennzahlen bleiben
`None` und werden in C/D mit Grund angezeigt; absolute P&L/Risiken bleiben
verfügbar. Anzeigepräzision ändert keine Rechen-/Exportwerte.

## Fehler, Snapshots und Ressourcen

`ValueError` bezeichnet Schema-/Eingabe-/Modelldomänenfehler; `DataError` bzw.
`OSError` später Provider-/Dateigrenzen. Programmierfehler bleiben mit
diagnostischem Traceback sichtbar, statt stillschweigend unterdrückt zu werden.
Jeder Service kopiert und validiert den Workspace vor dem Kernaufruf.
Arrays gehören dem Ergebnis, nicht dem Eingabesnapshot. B versieht Snapshots
mit Lauf-ID und verwirft nach Abbruch/veralteten Eingaben eintreffende Ergebnisse.

Der Terminaladapter begrenzt einen Lauf auf 5 Millionen Preiszellen
paths×(steps+1)×assets; weitere Kernausgaben benötigen zusätzlichen Speicher.
Dies ist eine konservative UI-Eingabegrenze, keine Speicher-/Laufzeitgarantie
und keine neue Beschränkung der Kern-API. Pro Workspace folgt in B ein aktiver
Job ohne Warteschlange. Thread-Abbruch bleibt kooperativ; ein Kernaufruf kann
bis zur nächsten Grenze weiterrechnen.

## Verifikationsnachweis

16 neue Vertragsfälle zunächst rot: fehlendes Paket/Startverhalten; nach
Implementierung grün. Strenge Typ-/Versions-/Feldprüfung, Snapshot-Eigentum,
Seed-Reproduzierbarkeit, einmalige Prozentumrechnung und Modulhilfe geprüft.
Unabhängige Cashreferenz: 1000 EUR, Kauf 2×100 EUR, 3 EUR Gebühr, sigma=0,
mu=.06, T=1, keine Finanzierung → Cash 797 EUR und Endvermögen
797+200 exp(.06) EUR. Absolute Rundungstoleranz 1e-10 EUR bei Größenordnung
1000 EUR; bestehende unabhängige numerische Suite bleibt verpflichtend.
Importblocker umfasst Textual, Matplotlib, pandas und yfinance auch bei
Vollinstallation. Paket A beansprucht keine vollständige UI-Bedienabnahme.

Lokale Prüfung macOS/Python 3.13.5: Vollprofil 439 bestanden, Basis und
tui ohne plots/yahoo jeweils 433 bestanden und genau die sechs bestehenden
Diagrammtests übersprungen. ruff check/format, striktes mypy (27 Module),
git diff --check und Wheel-/Quelldistributionsbau erfolgreich. Frische
Wheelinstallation außerhalb des Repositorys: Modul-/Konsolenhilfe und echte
Terminalstarts mit anschließendem q erfolgreich. Dies ersetzt keine manuellen
Bedien-/Terminal-Smokes der vollständigen App in #81.
