# M5 – Navigation und Hintergrundläufe (#75)

Die App bietet sechs per Ctrl+1…6 erreichbare Ansichten: Start, Portfolio,
Risiko, Strategien, Indizes und Workspace. Das
[Portfolioformular](33_M5_TUI_PORTFOLIO.md) ist in #76 ergänzt;
[Risiko/Stress](34_M5_TUI_RISK.md) in #77,
[Strategien](35_M5_TUI_STRATEGIES.md), [Indizes](36_M5_TUI_INDICES.md) und
[Workspaces/Exporte](37_M5_TUI_WORKSPACES.md) in #78–#80.
Tab/Shift+Tab wechseln den sichtbaren Fokus, Enter aktiviert Buttons.
F1 öffnet eine scrollbare Hilfe, Escape schließt sie. F2 zeigt die vollständige
Fehlerdiagnose in einer scrollbaren Ansicht; Escape kehrt zurück.
Ctrl+Q oder der Start-Button beenden. 80×24 und 120×40 sind Headless-Testgrößen;
kleinere Terminals zeigen einen Hinweis, Ctrl+Q bleibt verfügbar.

Die Startansicht rechnet die vorhandene kleine Offline-Demo mit Ctrl+R oder
Enter am Rechnen-Button. Der Seed ist änderbar. Auch ungültige Änderungen
markieren frühere Ergebnisse als veraltet; ein ungültiger Seed blockiert
den nächsten Start, statt unbemerkt alte Parameter zu rechnen.

## Zustände und Nebenläufigkeit

`Jobs` besitzt idle/running/succeeded/failed/cancelled. Jeder Start erhält eine
monoton steigende Lauf-ID und einen eigenen validierten, unveränderlichen
Workspace-Snapshot. Feldänderungen erhöhen die Eingaberevision. Ein erfolgreiches
Ergebnis bleibt sichtbar veraltet, wenn es einer früheren Revision gehört;
`exportable` ist dann false. Vollständige Ergebnisansichten und Exporte sind in C–G ergänzt;
fehlgeschlagene oder abgebrochene Rechenjobs sind nie exportierbar.
Ein fehlgeschlagener Dateiexport darf mit denselben aktuellen Rechenergebnissen
erneut versucht werden (siehe G).

Ein ThreadPoolExecutor besitzt genau einen Worker. Neue Jobs werden abgelehnt,
solange der physische Worker läuft, auch nach Abbruch. Es gibt keine wartende
Jobschlange. Der Worker berührt weder App noch Jobzustand; die UI übernimmt
fertige Futures an einer kurzen Pollinggrenze. Navigation, Hilfe und Abbruch
bleiben daher während eines Kernaufrufs nutzbar. Ohne tatsächlichen messbaren
Fortschritt steht nur eine Aktivitätsmeldung, kein Prozentsatz.

Escape verwirft die Veröffentlichung des laufenden Ergebnisses; ein schon
gestarteter NumPy-/Toolkit-Aufruf wird nicht erzwungen beendet. Seine spätere
Rückgabe wird nicht übernommen. Beenden schließt den Executor ohne blockierendes
Warten und ohne neue Jobs zuzulassen. Python kann vor Prozessende dennoch auf
den noch laufenden Thread warten. Die 5-Millionen-Preiszellengrenze bleibt
eine Eingabegrenze ohne garantierte Laufzeit; kein Thread-Kill.

Eingabe-/Modelldomänenfehler erhalten konkrete Meldungen. Jobfehler behalten
Exceptiontyp, Text und den vollständigen Traceback; F2 macht diesen für Diagnose
zugänglich. Rich-Markup ist für Fehlermeldungen deaktiviert. Fehler werden nicht
als Erfolg oder leere Resultate weitergereicht.

## Prüfung

Sieben anfängliche Fälle waren rot wegen fehlender Job-/App-Module, nach
Implementierung grün. Threading-Events bilden kontrollierte Workerbarrieren
statt Timingannahmen. Geprüft: physischer Einzellauf nach Abbruch, verworfenes
Spätergebnis, unveränderlicher Snapshot, veraltete Resultate, neue Lauf-ID,
Fehlerdiagnosen und gesperrte geschlossene Workspaces. Pilot prüft Navigation,
Fokus, Hilfe/Resize bei beiden Größen, Navigation/Abbruch während eines Jobs
und ungültige Eingaben. Ein zusätzlicher Red-Fall für die fehlende F2-Diagnose
war nach Ergänzung grün. Keine echten Provider und keine Systemzeit.

Beenden während eines kontrolliert laufenden Workers kehrt ohne Warten in die
UI zurück und verwirft das Ergebnis. Lokal zehn Job-/Pilot-Fälle bestanden;
ruff check/format, striktes mypy (29 Module), diff-Prüfung und Paketbau grün.
Gesamtsuite vor dem ergänzenden Beenden-Fall: 448 bestanden; Basis 438 bestanden
mit zehn benannten Skips, tui 442 bestanden mit sechs Diagramm-Skips. Die neue
abschließende CI zählt nun insgesamt 449 Fälle. Wheel-App-/Job-Fälle außerhalb
des Quellbaums geprüft; Gesamtsuite und aktuelle Wheel-Prüfung laufen in CI.

Die gesamte konfigurierte numerische Suite bleibt erforderlich. Basis-CI erlaubt
nur fünf namentlich aufgezählte UI-Fälle und sechs Diagrammtests als Skips;
tui-Profil erlaubt nur die sechs Diagrammtests, Vollprofil keine Skips.
Die Linux-/macOS-Bedien-Smokes der fertigen App bleiben Release-Abnahme in #81.
