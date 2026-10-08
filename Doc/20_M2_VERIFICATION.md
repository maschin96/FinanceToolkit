# M2-Verifikationsbericht – 0.2.0

## Umfang und Integration

| Issue | Ergebnis | Issue-PR nach codex/milestone-m2 |
| --- | --- | --- |
| #21 | Konventionen und unabhängige Referenzfälle | #30 |
| #22 | Analytische Options-Greeks | #31 |
| #23 | Portfolio-Exposures, Anleihen-DV01/Konvexität | #32 |
| #24 | Vollständige Stress-Neubewertung und Heatmap | #33 |
| #25 | Pfadabhängige Strategieausführung mit Kosten | #34 |
| #26 | Kalender-/Schwellen-Rebalancing | #35 |
| #27 | Reproduzierbares Offline-Risk-Lab | #36 |
| #28 | Gesamtverifikation und Release-Vorbereitung | Verifikations-PR |

#21–#27 wurden nach erfolgreicher aktueller Python-3.11–3.13-CI, eigenem
Diff-Review und Prüfung auf Review-Anmerkungen integriert und mit PR-Verweis
explizit geschlossen. Kein unabhängiger Reviewer verfügbar; keine externe
Freigabe behauptet. M2 ist über PR #38 in main integriert; tatsächlicher
Zielcommit 05144b7e59c0c2ec0128c6d234f586cea3c4cb23 mit erfolgreicher
[Python-3.11–3.13-CI](https://github.com/maschin96/FinanceToolkit/actions/runs/37753366082).
[v0.2.0 mit öffentlichen Wheel-/Quelldistributionsartefakten](https://github.com/maschin96/FinanceToolkit/releases/tag/v0.2.0)
wurde am 2026-10-08 veröffentlicht; #28 und M2 sind geschlossen.

## Red – Green – Refactor

Alle ausführbaren Pakete wurden zunächst mit Tests für fehlende APIs ausgeführt,
anschließend minimal implementiert und formatiert/typgeprüft. Intakte temporäre
Umgebung vermeidet veraltete Metadaten der bestehenden lokalen .venv.

| Paket | Beobachteter Red-Nachweis | Green-Nachweis |
| --- | --- | --- |
| Greeks | fehlender option_greeks-Import | ATM-Referenz, Paritätsableitungen, zentrale Differenzen |
| Exposures | fehlendes risk-Modul | Nullkupon/Kuponreferenzen, Asset-Zuordnung, Mengen/Multiplikator |
| Stress | fehlender StressScenario-Import und Plot-Modul; überlaufender Cash-only-Zins zunächst nicht abgelehnt | vollständige Referenzneubewertung, Grenzen, Heatmap-PNG |
| Ausführung | fehlendes strategies-Modul | Cash-/Mengenbilanz, Verzögerung, Prefix-Invarianz, Finanzierung/Kosten |
| Regeln | fehlende simulate_rebalancing-API; Cashschwelle zunächst übersehen | strikte Grenzfälle, Cashrest, gemeinsame Eröffnung, Raster-Sensitivität |
| Exporte | fehlendes risk_lab-Modul, Finanzierungsfeld und Optionsvergleich-Kostenmetriken | CSV/JSON-Werte gegen APIs, numerische Exporte ohne Matplotlib, PNGs |
| Abschluss | Heatmap änderte globales Backend | eigener FigureCanvasAgg, Regression grün |

Für #21 reine Dokumentation ohne künstlichen Red-Test. Die letzten
Abschlusskorrekturen betreffen Backend-Isolation und vollständige Kosten-/
Umsatzmetriken des Optionsvergleichs. Keine Tests deaktiviert; Toleranzen nicht
nachträglich aufgeweitet. Gamma-Differenzen nutzen relativ zum Kurs skalierte
Schritte statt kleiner absoluter Schritte mit Auslöschung.

## Wissenschaftliche Referenzen und Toleranzen

[API-Verträge](18_M2_CONTRACTS.md), [Optionen](12_OPTIONS.md) und
[Risk Lab](19_RISK_LAB.md) dokumentieren Herleitungen, Einheiten und Grenzen.

- Greeks: unabhängige ATM-Standardnormal-Referenz, Ableitungen der
  Put-Call-Parität und Preis-Differenzen über mehrere Schrittweiten.
  Analytische Identitäten relativ/absolut 1e-12; Differenzen relativ 2e-5 und
  absolut 2e-7 bei den dokumentierten Parametern/Einheiten. Zweite Differenzen
  sind stärker von Auslöschung betroffen; Schrittweite skaliert mit Spot.
- Bonds: unabhängige verbleibende Kupon-/Tilgungszahlungen, analytischer
  Nullkupon. Rho und zweite Ableitung aus diskontierten Zeitmomenten,
  DV01 pro Basispunkt, Konvexität in Jahren². Analytisch 1e-12 relativ/absolut;
  zentrale Zinsdifferenz relativ 2e-7, absolut 1e-8 für Schritt 1e-4.
- Portfolio: signed Mengen, Multiplikator, Gegenpositionen und separate
  Underlyings; Cash unverändert. Fällige Positionen haben null Exposure.
- Stress: Aktien-Handrechnung, ATM-Option und Nullkuponreferenz, Nullschock
  unverändert; zweiteilige Delta/Gamma-Näherung mit sinkendem Fehler bei
  halben Spotschocks. Stress ist kein probabilistisches VaR/ES.
- Strategien: Ein-Pfad-Handrechnung und unabhängige kumulierte Cash-/Mengen-
  Rekonstruktion. Absolute Toleranz 1e-10 Währung/Stück, relative 1e-12
  für kleine deterministische Referenzen. Prefix-Invarianz exakt für identische
  Eingabedaten, keine Zukunftsinformation und keine Nullauftragsgebühren.
- Rebalancing: konstante Preise, strikte Schwelle inklusive Cashrest und
  feinere Raster auf demselben deterministischen Kursverlauf. Die feinere
  Handelsfrequenz ändert die Strategie; daher keine falsche Raster-Invarianz.
- Export: direkte API-Konsistenz zusätzlich zu unabhängigen Kernreferenzen.
  Profiling des 100-Pfad-Exports begründete einmalige Gewichtsberechnung;
  Regressionen vergleichen weiterhin identische Exportwerte.

Analytische Bewertung und exakte GBM-Schritte benötigen keine Euler-Konvergenz.
Bestehende M1-GBM-Moment-/Kovarianz-/Stichprobennachweise bleiben Teil der Suite.
Neue Strategie-Rasterprüfung und Greek-Schrittweiten prüfen die betroffenen
Diskretisierungs-/Approximationsfragen. Keine empirische Marktvalidierung.

## Technische Nachweise

Lokal macOS/Python 3.13, saubere Umgebung mit `uv sync --locked --extra plots`:

```sh
/tmp/finance-m2-dev/bin/python -m pytest -q
/tmp/finance-m2-dev/bin/python -m ruff check .
/tmp/finance-m2-dev/bin/python -m ruff format --check .
/tmp/finance-m2-dev/bin/python -m mypy src/finance_toolkit
git diff --check
uv build
```

Gesamtsuite nach den Abschlussregressionen: **211 Tests**, einschließlich
optionaler Diagramme bei installiertem plots-Extra. ruff und striktes mypy
bestanden; finale aktuelle CI-Nachweise stehen im Verifikations-PR / Issue #28.
Wheel und Quelldistribution gebaut; Lockfile ändert nur Projektversion 0.1.0→0.2.0.
Keine neue Pflichtabhängigkeit.

Frische Python-3.11-Wheel-Installation mit gehashten Lock-Abhängigkeiten, Tests
außerhalb des Quellbaums: **211 Tests bestanden**; M1- und M2-CLIs mit PNGs
bestanden. CI prüft Python 3.11–3.13, beide Offline-CLIs und dasselbe installierte
Wheel außerhalb des Quellbaums. Installationstests prüfen Metadaten und py.typed.
Ohne plots werden ausschließlich optionale Diagrammtests sichtbar übersprungen;
Release-CI installiert plots und lässt keinen Pflichtnachweis aus.

## Grenzen und verbleibender Release-Abschluss

GBM/BSM-Modellannahmen, flache ausfallfreie Anleihen und M1-Konventionen bleiben.
Keine Live-Daten, empirische Backtests, Optimierung, FX, Margin, Steuern,
Dividenden-Cashflows oder externen Kapitalflüsse. Rebalancing nur Long-only
Aktien/Cash, Bruchstücke erlaubt; deterministische Asset-Reihenfolge bei
Cashknappheit kann die Allokation beeinflussen. Gebühren/Preissprünge können
Zielgewichte verhindern. Eigene Signale dürfen keinen pfadübergreifenden Zustand
führen; Built-in-Regeln sind zustandslos. Greek-API lehnt nichtglatte Grenzen
explizit ab, Preis-API erhält sie. Große Arrays benötigen proportional Speicher.

Release-Integration, Zielcommit-CI, Tag und öffentliche Pakete sind abgeschlossen
(siehe oben). Keine PyPI-Veröffentlichung.
