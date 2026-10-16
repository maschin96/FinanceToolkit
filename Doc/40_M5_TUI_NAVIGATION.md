# M5 – Terminalnavigation ohne Ctrl+Ziffer (#95)

Der Nutzer meldet bei der manuellen macOS-Bedienung, dass Ctrl+1…6 keine
Ansichten wechseln. Die bisherigen Pilotfälle haben diese Kürzel als
synthetische Ereignisse geschickt; sie beweisen keine Übertragung durch ein
reales Terminal. Die Navigation darf deshalb nicht von diesem einzigen Weg
abhängen. Es werden keine Terminalprofile oder Systemeinstellungen geändert.

## Bedienung

Die sechs Ansichten stehen in einer ständig sichtbaren Menüleiste. Tab bzw.
Shift+Tab fokussiert das Menü, Links/Rechts wechselt die Ansicht. Der Fokus
bleibt im Menü, damit weitere Pfeiltasten funktionieren. Tab wechselt danach
in das Formular. Die Leiste kann auch angeklickt werden. Auswahl und Inhalt
bleiben beim Wechsel über Tastenkürzel synchron.

| Kürzel | Ansicht |
| --- | --- |
| F3 | Start |
| F4 | Portfolio |
| F5 | Risiko |
| F6 | Strategien |
| F7 | Indizes |
| F8 | Workspace |

Auf Mac-Tastaturen je nach Funktionstasteneinstellung Fn mitbenutzen.
Die Menüleiste bleibt unabhängig von diesen Funktionstasten bedienbar.
F1 = Hilfe, F2 = Diagnose, Ctrl+R = rechnen, Escape = abbrechen,
Ctrl+Q = beenden. Ctrl+1…6 bleiben versteckte Kompatibilitätsaliase für
Terminals, die entsprechende Ereignisse tatsächlich liefern. Sie werden nicht
mehr als notwendiger Bedienweg beworben. Die Navigation startet keine Rechnung
oder Netzabfrage und verändert keine Formulareingaben.

## Regression und Verifikation

Zwei neue Regressionstests waren vor Implementierung bei 80×24 und 120×40 rot,
weil die sichtbare Navigation fehlte. Nach Implementierung grün: alle Seiten
per Pfeiltasten/Funktionstasten, Fokus beim wiederholten Wechsel, Tab/Shift+Tab,
synchrone Auswahl, unveränderte Eingaben, Hilfe und keine Rechenaufrufe.
Die bisherigen Kompatibilitätstests bleiben bestehen.

Die beiden bestehenden Prozessstarttests für Modul und Konsolenprogramm prüfen
jetzt zusätzlich echte xterm-F3…F8-Bytesequenzen über den POSIX-Terminaltreiber.
Für jede Ansicht wird ihre eigene gerenderte Formularbeschriftung erwartet,
anschließend reguläres Beenden per Ctrl+Q. Das ist eine automatisierte
Terminalprüfung und keine manuelle Abnahme. Ein falscher erwarteter Textmarker
im Testaufbau wurde anhand der tatsächlich vorhandenen Formularbeschriftung
korrigiert; keine Produktprüfung abgeschwächt.

Keine Finanzmodell-/Diskretisierungsänderung, daher keine neuen wissenschaftlichen
Konvergenzfälle. Alle bisherigen numerischen Nachweise bleiben verpflichtend.
Vollprofil nun 497 Fälle; Kern 476 bestanden/21 ausdrücklich benannte Skips
(14 UI, sieben Diagramme), TUI 490 bestanden/sieben Diagramm-Skips. Die CI
zählt jeden erlaubten Skip, einschließlich beider neuen UI-Fälle.

Eigenreview; kein unabhängiger Reviewer verfügbar. Die vier manuellen
macOS-/Linux-Prüfzeilen in [#81](https://github.com/maschin96/FinanceToolkit/issues/81)
bleiben offen. Der gemeldete Fehler zählt als manueller Befund, nicht als
bestandene Wiederholungsprüfung des korrigierten Standes.
