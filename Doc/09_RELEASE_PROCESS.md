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
Das private Repository bleibt privat. Es wird keine Open-Source-Lizenz ohne
Eigentümerentscheidung vergeben.


## M2 / v0.2.0

Issue-PRs #30–#36 und der Verifikations-PR zielen auf `codex/milestone-m2`. Release-Issue #28 bleibt
bis zum vollständigen Veröffentlichungsabschluss offen. Vor Release main in
milestone-m2 integrieren; Pflichtumfang, Dokumentation, CI und Review-Anmerkungen
am aktuellen Stand prüfen. Release-PR nach main, Zielcommit-CI prüfen, danach
v0.2.0 taggen und Wheel/Quelldistribution im privaten Release ablegen.
Ein Umsetzungsauftrag auf dem Milestone-Branch veröffentlicht noch kein Release.

## M3 / v0.3.0

Pflicht-Issue-PRs #48–#55 und der Verifikations-PR zielen auf
`codex/milestone-m3`. Gesamtverifikation in [M3-Bericht](28_M3_VERIFICATION.md).
Vor Release main übernehmen und erneut prüfen; Release-PR ausdrücklich nach
main. Nach Merge tatsächliche main-Zielcommit-CI für Python 3.11–3.13 prüfen,
erst danach v0.3.0 taggen und Wheel/Quelldistribution im privaten Release ablegen.
#47 und M3 erst nach vollständigem Abschluss schließen. M2-Nachweise verbleiben
in #28. Kein unabhängiger Reviewer verfügbar; eigenen Review transparent nennen.
