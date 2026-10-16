# Release-Prozess

1. Projektinitialisierung erzeugt main mit Projektauftrag und Dokumentation.
   Dies ist kein numerisches Release und keine Freigabe von M0-Funktionalität.
2. Bei M0-Arbeitsbeginn codex/milestone-m0 vom stabilen main erstellen.
   Issue-Branches davon ableiten und per geprüftem PR nach milestone-m0 integrieren.
3. Nach vollständig verifiziertem M0 Release-PR nach main, main-CI prüfen.
   Erst danach bei Arbeitsbeginn codex/milestone-m1 erstellen.
4. M1-Issue-Branches per PR nach milestone-m1 integrieren. Aktuelle CI und
   Review-Anmerkungen prüfen; fehlendes unabhängiges Review transparent benennen.
5. Vor Release main in milestone-m1 übernehmen; vollständige Tests und
   Qualitätsprüfungen durchführen, Dokumentation und Beispiele aktualisieren.
6. Release-PR nach main erst bei fertigem Pflichtumfang. Nach Merge CI am
   tatsächlichen main-Zielcommit prüfen. Danach v0.1.0 taggen und Release erstellen.
7. Integrierte Issues mit PR-Verweis explizit schließen; #9 erst nach vollständigem
   Release-Abschluss. Paketveröffentlichung auf PyPI benötigt einen separaten Auftrag.

Kein Force-Push, kein vorzeitiger Merge neuer Milestone-Funktionen nach main.
Das Repository und seine GitHub-Releases sind öffentlich (Eigentümerentscheidung
vom 2026-10-08). Es wird keine Open-Source-Lizenz ohne
Eigentümerentscheidung vergeben.


## M2 / v0.2.0

Issue-PRs #30–#36 und der Verifikations-PR zielen auf `codex/milestone-m2`. Release-Issue #28 bleibt
bis zum vollständigen Veröffentlichungsabschluss offen. Vor Release main in
milestone-m2 integrieren; Pflichtumfang, Dokumentation, CI und Review-Anmerkungen
am aktuellen Stand prüfen. Release-PR nach main, Zielcommit-CI prüfen, danach
v0.2.0 taggen und Wheel/Quelldistribution im öffentlichen Release ablegen.
Ein Umsetzungsauftrag auf dem Milestone-Branch veröffentlicht noch kein Release.

## M3 / v0.3.0

Pflicht-Issue-PRs #48–#55 und der Verifikations-PR zielen auf
`codex/milestone-m3`. Gesamtverifikation in [M3-Bericht](28_M3_VERIFICATION.md).
Vor Release main übernehmen und erneut prüfen; Release-PR ausdrücklich nach
main. Nach Merge tatsächliche main-Zielcommit-CI für Python 3.11–3.13 prüfen,
erst danach v0.3.0 taggen und Wheel/Quelldistribution im öffentlichen Release ablegen.
#47 und M3 erst nach vollständigem Abschluss schließen. M2-Nachweise verbleiben
in #28. Kein unabhängiger Reviewer verfügbar; eigenen Review transparent nennen.

## M4 / v0.3.1

Pflichtissues #58–#65 sind über PRs #67–#72, #83 und #84 nach
`codex/milestone-m4` integriert. Abschlussarbeitspaket #66 aktualisiert
Version/Lockfile, Dokumentation und [Gesamtverifikation](30_M4_VERIFICATION.md).
Aktuelles main vor Freigabe im Milestone übernehmen und den kombinierten
Stand erneut prüfen; M5-Planungsdokumentation erhalten. Release-PR ausdrücklich
nach main, erst bei vollständig geprüftem Pflichtumfang. CI und vorhandene
Review-Anmerkungen am aktuellen PR-Stand prüfen; fehlendes unabhängiges Review
transparent nennen.

Nach Merge CI am tatsächlichen main-Zielcommit für Python 3.11–3.13 und
das Basisprofil ohne Extras prüfen. Erst danach diesen Commit als v0.3.1
taggen, Wheel/Quelldistribution daraus bauen und im öffentlichen GitHub-Release
veröffentlichen. Frische Wheelinstallation außerhalb des Quellbaums und alle
vier Offline-CLIs mit Diagrammen gehören zur Abnahme. #66 und M4 erst nach
Verifikation von Tag, Release und Paketartefakten schließen; Nachweise dort
verlinken. Keine PyPI-Veröffentlichung oder neue Open-Source-Lizenz.

## Geplant: M5 / v0.4.0

[M5-TUI-Plan](29_M5_TUI_ROADMAP.md), Pflichtissues #74–#80,
Releaseissue #81. Umsetzung erst nach vollständigem M4/v0.3.1-Abschluss (#66)
und stabilem main. `codex/milestone-m5` erst bei tatsächlichem Arbeitsbeginn
anlegen; Issue-PRs dorthin. Die Planungsdokumentation (#73) ist Repository-Pflege
mit PR-Ziel main und führt keine TUI-Funktionalität ein.

Vor Release alle Pflichtpakete, Headless-/Referenztests, Installationsprofile,
Python-3.11–3.13-CI, Wheel-Smokes, manuelle Terminal-Smokes und Dokumentation
abschließen; main übernehmen und resultierenden Stand erneut prüfen.
CI und Review-Anmerkungen am aktuellen PR-Stand klären. Erst dann Release-PR
nach main; nach Merge CI am tatsächlichen main-Zielcommit prüfen, danach
v0.4.0 taggen und öffentliche Wheel-/Quelldistributionsartefakte veröffentlichen.
#81/M5 erst nach vollständigem Veröffentlichungsabschluss schließen.
Keine PyPI-Veröffentlichung und kein Releaseauftrag durch die Planung.

Stand 2026-10-15: A–G sind integriert (PRs #87–#93). Die Version 0.4.0 wird im
H-Branch vorbereitet, ist aber noch nicht freigegeben/veröffentlicht.
Der Eigentümer behält die manuellen macOS-/Linux-Smokes ausdrücklich bei.
[Verifikationsstand](38_M5_TUI_VERIFICATION.md) und
[Prüfanleitung/Protokoll](39_M5_MANUAL_SMOKE.md) zeigen das offene Gate.
Vor dessen Abschluss keinen Release-PR nach main, Tag oder Veröffentlichung
vornehmen. Der H-Vorbereitungs-PR zielt weiterhin nach codex/milestone-m5 und
verwendet Refs #81; das Releaseissue bleibt offen.


Stand 2026-10-16: Der Eigentümer hat die manuelle Abnahme als durchgeführt
bestätigt und die Integration von M5 nach main beauftragt. Das manuelle Gate
ist damit für die Integration freigegeben; siehe [Bestätigung](39_M5_MANUAL_SMOKE.md).
Die Veröffentlichung von Tag/Artefakten und das Schließen von #81/M5 bleiben
eigene nachgelagerte Schritte nach erfolgreicher main-CI.
