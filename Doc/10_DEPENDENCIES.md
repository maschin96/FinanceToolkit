# Abhängigkeiten und Lizenzen

Die genauen, Python-abhängigen Versionen und Artefakt-Hashes stehen in uv.lock.
Die pyproject.toml enthält kompatible Bereiche und sämtliche Werkzeugkonfiguration.
Die Toolbox selbst erhält damit keine Open-Source-Lizenz.

| Abhängigkeit | Zweck | Projektlizenz / Primärquelle |
| --- | --- | --- |
| NumPy | Arrays und Zufallszahlen für die kommenden Modelle | [BSD-3-Clause](https://numpy.org/doc/stable/license.html) |
| SciPy | Verteilungen und numerische Verfahren | [BSD-3-Clause](https://scipy.org/about/) |
| pytest | Tests | [MIT](https://github.com/pytest-dev/pytest/blob/main/LICENSE) |
| ruff | Lint und Formatierung | [MIT](https://github.com/astral-sh/ruff/blob/main/LICENSE) |
| mypy | Statische Typprüfung | [MIT](https://github.com/python/mypy/blob/master/LICENSE) |
| hatchling 1.27.0 | Isolierter Paketbuild | [MIT](https://github.com/pypa/hatch/blob/master/LICENSE.txt) |
| Matplotlib (optional plots extra) | Diagramm-Adapter | [PSF-basierte BSD-kompatible Lizenz](https://matplotlib.org/stable/project/license.html) |
| uv 0.11.23 | Installation und Lockverwaltung | [MIT oder Apache-2.0](https://github.com/astral-sh/uv/blob/main/LICENSE-MIT) |

Lizenzangaben der installierten direkten Abhängigkeiten wurden in den
Distributionsmetadaten geprüft. Binäre NumPy/SciPy-Wheels können weitere
Lizenzhinweise für enthaltene Drittkomponenten mitbringen; diese bleiben erhalten.
Vor einer Distribution gebündelter Abhängigkeiten deren Hinweise separat prüfen.

## CI-Referenzen

Actions werden auf vollständige Commit-SHAs fixiert: checkout v5, setup-python v6,
setup-uv v7 (Referenzen am 2026-10-07 geprüft). Versionskommentare dienen der
Zuordnung; Updates erfordern erneute Prüfung des SHA und CI-Laufs. Runner: Ubuntu 24.04, ohne automatische ubuntu-latest-Migration. CI nutzt nur
contents: read, keine Secrets, keine persistierten Git-Zugangsdaten und keine
pull_request_target-Ausführung. PR-Code läuft ausschließlich in unprivilegierten Jobs.

## Optionaler Yahoo-Adapter (2026-10-08, #45)

`yfinance[repair]==1.7.0` kapselt den optionalen I/O-Provider. Repair bleibt ein
explizites Opt-in; die Zusatzbibliotheken unterstützen dessen Reparaturpfade.
Die numerischen Module verwenden keine DataFrames. Installierte Metadaten und
beigefügte Lizenzdateien wurden geprüft, Python-Unterstützung über CI 3.11–3.13.
Exact Builds/Hashes und weitere Python-abhängige Varianten stehen in uv.lock.

| Neue Yahoo-Abhängigkeiten (lokal Python 3.13) | Lizenz laut Distribution |
| --- | --- |
| yfinance 1.7.0, multitasking .0.13, requests 2.34.2 | Apache-2.0 |
| beautifulsoup4 4.15.0, charset-normalizer 3.5.2, curl-cffi .16.3, narwhals 2.26.0, peewee 4.5.3, platformdirs 4.12.4, pytz 2026.5, soupsieve 2.10, urllib3 2.8.0 | MIT |
| cffi 2.1.1 | MIT-0 (No Attribution) |
| certifi 2026.7.22 | MPL-2.0 |
| cloudpickle 3.1.2, idna 3.20, joblib 1.6.0, lxml 6.1.3, pandas 3.0.6, protobuf 7.36.2, pycparser 3.0, scikit-learn 1.9.1, threadpoolctl 3.7.0, websockets 17.2 | BSD-3-Clause |

Primärnachweis: Paket-Wheel-METADATA und enthaltene LICENSE-Dateien; für peewee
fehlte der License-Metadateneintrag, die enthaltene MIT-Lizenz wurde gelesen.
[Provider pyproject/Lizenz](https://github.com/ranaroussi/yfinance/blob/main/pyproject.toml).
Binärwheels (z.B. curl-cffi/lxml) bringen zusätzliche Drittkomponentenhinweise
mit; diese nicht entfernen, bei separater Bündelung vollständig prüfen.
Softwarelizenzen gewähren keine Marktdatenrechte; siehe [Yahoo-Vertrag](25_M3_YAHOO.md).

## Verifizierte Installationsprofile (#63)

`uv sync --locked` installiert Laufzeitkern (NumPy/SciPy) und Entwicklungswerkzeuge,
ohne optionale Extras. `uv sync --locked --no-dev` installiert nur den Laufzeitkern;
pytest ist dann bewusst nicht verfügbar. Für die vollständige Entwicklungs- und
Release-Prüfung `uv sync --locked --extra plots --extra yahoo` verwenden. Eine
frische isolierte Basisumgebung ist mit `UV_PROJECT_ENVIRONMENT=/tmp/finance-core`
vor beiden `uv sync`-/`uv run`-Aufrufen möglich; siehe README.

Der Basis-CI-Job auf Python 3.13 prüft, dass Matplotlib, pandas und yfinance
tatsächlich fehlen, und führt die gesamte Suite mit sichtbaren Übersprüngen aus.
Nur sechs konkrete Diagrammtests dürfen übersprungen werden (M1-Beispiele,
Hedge-Lab, Index-Lab, Risk-Lab und zwei Stress-Heatmap-Tests). Der JUnit-Bericht
wird gegen diese Namensliste geprüft; numerische Fehler oder zusätzliche
Übersprünge sind Fehler des Jobs. Numerische Hedge-Exportnachweise laufen
unabhängig vom Diagrammtest weiter. Zusätzlich blockieren Tests alle optionalen
Imports in einem frischen Prozess und prüfen sämtliche Paketimporte sowie die
vier numerischen Offline-CLIs mit ihren Pflichtdateien. Die Index-Demo ist
synthetisch und funktioniert auch bei Wheel-Prüfung außerhalb des Repositorys.
Yahoo-Cache-Replay bleibt durch die vorhandenen Offline-Tests abgedeckt.

Die vollständige Python-3.11–3.13-Matrix, Diagramm-Smokes und Wheel-Prüfungen
bleiben verpflichtend. Ihr Testbericht darf keinen Übersprung enthalten.
Keine neue Abhängigkeit und keine Änderung von Versionslocks, Tokenrechten
oder Action-Pins. Dies ist Installations-/Adapterverifikation, keine empirische
Marktvalidierung oder Änderung numerischer Toleranzen.

## Optionales TUI-Extra für M5 (#74)

Textual 8.2.8 ist als optionale UI-Abhängigkeit für `tui` aufgenommen. Die
[Projektlizenz ist MIT](https://github.com/Textualize/textual/blob/main/LICENSE).
Vor Aufnahme wurden Wheel-METADATA einschließlich Python-Anforderungen,
License-Expression, Classifier und License-File in isolierter Umgebung geprüft
(2026-10-14). Die Python-Anforderung von Textual lautet >=3.9,<4.0; alle TUI-Transitiven
erlauben die unterstützten Python-Versionen 3.11–3.13.
Neue Pakete: Textual 8.2.8, Rich 15.0.0, markdown-it-py 4.2.0,
mdit-py-plugins 0.6.1, mdurl 0.1.2 und linkify-it-py 2.2.0: MIT.
Bereits gelockte Transitiven: platformdirs 4.12.4 MIT, Pygments 2.21.0
BSD-2-Clause, typing-extensions 4.16.0 PSF-2.0. Keine syntax-Extras aufgenommen.
Versionen/Hashes einschließlich Pythonvarianten stehen in uv.lock. Lizenzen
verbleiben in den Distributionen; kein separates Bündeln der Abhängigkeiten.
Python-Kompatibilität wird zusätzlich über die aktuelle CI-Matrix geprüft.
[Verträge und Profil](31_M5_TUI_CONTRACTS.md); vollständige App-Abnahme in #81.


## Abschließende M5-Profile (#81)

Vollprofil: `uv sync --locked --all-extras`; 495 Tests ohne Auslassung.
Kern: `uv sync --locked`; 476 Tests und 19 namentlich erlaubte Skips (zwölf
UI-, sieben Diagrammtests). TUI: `uv sync --locked --extra tui`; 488 Tests,
sieben Diagramm-Skips. Alle Profile verwenden denselben Lockstand, ohne neue
Pflichtabhängigkeiten. Vollprofil-CI läuft auf Python 3.11–3.13; die beiden
reduzierten Profile auf 3.13. Namen und Anzahl werden im XML-Bericht geprüft.
Der isolierte Wheeltest installiert Laufzeit-/Testwerkzeuge gesondert und
führt außerhalb des Quellbaums dieselben Tests sowie alle alten Offline-CLIs aus.
Textual bleibt lazy; numerische Workspaces/Exporte benötigen es nicht.
Lizenzangaben des Abschnitts oben wurden am 2026-10-15 erneut mit installierter
Paket-METADATA abgeglichen; keine zusätzlichen Abhängigkeiten in H.
