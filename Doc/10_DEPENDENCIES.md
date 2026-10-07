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

Actions werden auf vollständige Commit-SHAs fixiert: checkout v4, setup-python v5,
setup-uv v7 (Referenzen am 2026-10-07 geprüft). Versionskommentare dienen der
Zuordnung; Updates erfordern erneute Prüfung des SHA und CI-Laufs. CI nutzt nur
contents: read, keine Secrets, keine persistierten Git-Zugangsdaten und keine
pull_request_target-Ausführung. PR-Code läuft ausschließlich in unprivilegierten Jobs.
