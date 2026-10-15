# M5 – Manuelle Terminalprüfung vor v0.4.0 (#81)

**Status: ausstehend.** Diese Liste ist eine Prüfanleitung, kein bestandener
Nachweis. Der Eigentümer hat die manuelle macOS-/Linux-Abnahme am 2026-10-15
bestätigt. Automatisierte Pilot-/Wheeltests ersetzen sie nicht. Die verfügbare
Computersteuerung verweigert den Zugriff auf die Terminal-App; Codex hat daher
keine manuelle Bedienung bestätigt. Windows wurde nicht manuell geprüft und
wird nicht als unterstützte Terminalplattform zugesagt.

## Vorbereitung

Den jeweiligen aktuellen `codex/milestone-m5`-Commit oder den darauf aufbauenden
Verifikations-PR zu #81 verwenden und den exakten Commit protokollieren.
Auf macOS und Linux Python 3.11–3.13 verwenden:

```sh
uv sync --locked --extra tui
uv run --no-sync finance-toolkit-tui
```

Keine Yahoo-Verbindung für diese Abnahme nötig. Diagramme sind optional.
Terminalfenster nacheinander auf **80 Spalten × 24 Zeilen** und
**120 Spalten × 40 Zeilen** einstellen, vor dem Appstart mit `stty size` prüfen
(Ausgabe: Zeilen, dann Spalten). Terminalname/-version, Betriebssystem, Python,
Toolkit-Commit und Textualversion festhalten. Prüfen, dass das Terminal die
Funktionstasten weiterleitet (Mac ggf. Fn). Die sichtbare Menüleiste muss
zusätzlich per Tab und Links/Rechts bedienbar sein. Abweichungen protokollieren.

## Ablauf je Betriebssystem und Größe

1. App starten: Startansicht, sichtbarer Fokus und keine automatische Rechnung/
   Datenabfrage. Tab/Shift+Tab, Menüleiste mit Links/Rechts, F3…F8 und F1/Escape prüfen. Alle Ansichten
   müssen per Tastatur erreichbar sein; überlange Formulare scrollbar. Einmal
   unter 80×24 verkleinern: Warnung und Ctrl+Q bleiben erreichbar. Danach die
   geforderte Größe wiederherstellen.
2. Start: Seed 99 eingeben, Ctrl+R. `running` und anschließend `succeeded`.
   Portfolioansicht: Vermögen/Positionen und beschrifteter Verlauf sichtbar;
   Pfad/Zeit ändern und Tabelle prüfen. Seed ungültig setzen: klare Fehlermeldung,
   kein neuer Lauf; Seed korrigieren. Bestehendes Ergebnis bleibt veraltet, bis
   erneut gerechnet wurde.
3. Risiko: F5, Ctrl+R, Snapshot/Greeks/VaR/ES und Stressraster prüfen.
   Eine Szenariozeile hinzufügen/ändern/löschen. Strategie: F6, Ctrl+R;
   Rebalancing und Optionsbuch prüfen, im Buch Ledger/Attribution ansehen.
   Ein Hedge benötigt ausdrücklich Short-/Kreditfreigaben gemäß Formular.
4. Indizes: F7, source=demo; Daten zuerst vorbereiten, Quellen/Sitzungen
   prüfen, separaten Indexbutton aktivieren. Preis-/Total-Return-Reihen sichtbar.
   Für einen Fehler source=replay mit einem neuen, leeren Cachepfad und
   Datenvorbereitung verwenden: konkreter Cache-Miss ohne Online-Fallback.
   F2 zeigt die Diagnose, Escape kehrt zurück. Danach demo zurückstellen.
5. Start mit Seed 99 erneut rechnen. F8: neue Konfigurationsdatei und
   Exportverzeichnis wählen; speichern. Seed ändern, Datei laden: keine Rechnung,
   altes Ergebnis veraltet. Erneut rechnen und exportieren. Vollständiges Manifest,
   `result.json`, `parameters.json` und CSV vorhanden. Zweiter Export ohne
   Überschreibcheckbox scheitert konkret; mit Freigabe gelingt er. Erfolgreicher
   Dateipfad im Status sichtbar. Keine automatische Sitzungsdatei beim Beenden.
6. Abbruch unter kontrollierter Last mit dem folgenden Teststart prüfen.
   Ctrl+R, während der fünfsekündigen Pause Ansichten wechseln, F1 schließen,
   Escape drücken. `cancelled`, kein verspätetes Ergebnis oder Export. Während
   der physische Worker noch läuft, wird ein weiterer Start abgelehnt.
   Nach Abschluss erneut starten; auch Ctrl+Q während eines laufenden Jobs prüfen.
   Der Python-Prozess darf vor Ende noch auf den Thread warten; die UI muss
   unmittelbar schließen. Dieser Start ist ein manueller Infrastruktur-Smoke,
   keine Messung der numerischen Laufzeit:

```sh
uv run --no-sync python -c 'from time import sleep; from finance_toolkit.tui.app import create_app; from finance_toolkit.tui.services import run_portfolio; create_app(work=lambda config: (sleep(5), run_portfolio(config))[1]).run()'
```

## Ergebnisprotokoll

Die vier Zeilen erst nach tatsächlicher Bedienung ausfüllen. Pro Zeile die
Schritte 1–6 mit bestanden/Fehler und Beleg beschreiben; Probleme vor Release
beheben und den betroffenen Umfang erneut prüfen. Keine pauschale Freigabe aus
einer einzigen Startansicht ableiten.

| System | Größe | OS / Terminal / Python / Textual | Commit | Schritte 1–6 / Prüfer / Datum |
| --- | --- | --- | --- | --- |
| macOS | 80×24 | ausstehend | ausstehend | ausstehend |
| macOS | 120×40 | ausstehend | ausstehend | ausstehend |
| Linux | 80×24 | ausstehend | ausstehend | ausstehend |
| Linux | 120×40 | ausstehend | ausstehend | ausstehend |

Nach diesen Nachweisen: main erneut in M5 übernehmen, vollständige CI am
kombinierten Stand prüfen, Review-Anmerkungen klären, Release-PR nach main.
Erst nach erfolgreicher CI des tatsächlichen main-Zielcommits v0.4.0 taggen und
Wheel/Quelldistribution mit Prüfsummen veröffentlichen. #81/M5 erst danach
schließen; siehe [Release-Prozess](09_RELEASE_PROCESS.md).


Befund vom 2026-10-15: Der Nutzer meldet funktionslose Ctrl+1…6 im
macOS-Terminal. #95 korrigiert den Bedienweg; dieser Bericht ist keine bestandene
manuelle Wiederholungsprüfung. Die vier Zeilen bleiben bis tatsächlicher
Bedienung des korrigierten Commits offen.
