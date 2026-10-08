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
