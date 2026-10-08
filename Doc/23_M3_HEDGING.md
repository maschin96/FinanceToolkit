# Verzögertes Delta-Hedging (#41)

`simulate_hedge` reserviert genau ein `Stock`-Instrument je Options-Underlying
als Hedge; Anfangsorders enthalten nur Optionen. Das Ziel ist minus aggregiertes
signed Optionsdelta inklusive Verträgen/Multiplikatoren, in Aktienäquivalenten.
Weder Kalender noch Schwelle bedeutet ungehedgte Kontrolle. Der Kalender enthält
Rasterzeiten, die Schwelle ist strikt positiv und wird strikt überschritten.
Signal bei t, Ausführung bei t+1: tatsächliches Restdelta wird nicht null gesetzt.

`HedgePaths` enthält das vollständige `BookPaths`, aktuelle Zielaktienmenge,
Delta vor der tatsächlichen Ausführung und Restdelta danach, jeweils
(Pfade, Zeiten, Assets). Anfangsoptionen, Kapital und Modell-/Finanzierungs-
parameter sind für Kontroll- und Hedgefälle gleich. Die Hedge-API erlaubt
explizit Aktien-Shorts und Kredit; Kostenraten sind benannte Parameter, default null.

Bei der letzten Optionsfälligkeit eines Assets wird nach Barausgleich dessen
Hedge zum aktuellen Aktienkurs und normalen Gebühren geschlossen. Eine veraltete
pending Hedgeorder entfällt. Diese Ereignisregel liest keine zukünftigen Preise;
es gibt keine physischen Optionslieferungen. Aktive nichtglatte Greek-Grenzen
werden gemäß M2 abgelehnt, abgerechnete Optionen werden nicht ausgewertet.

Konvergenzreferenz: 1000 gekoppelte GBM-Pfade, Seed 314, S=K=100, sigma=.2,
r=mu=q=0, T=1, short ein Call mit Multiplikator 1. Gleiche feine 128-Schritt-
Pfade werden auf 16 Schritte ausgedünnt. Keine Gebühren/Leihe/Zinsen. RMS des
terminalen Replikationsfehlers muss bei 128 Schritten unter 70% des groben
RMS liegen. Dies ist ein deterministischer numerischer Test unter diesen
Modellannahmen, kein universelles monotones Risiko-/Gewinnversprechen. Cash-
Rundungstoleranz 1e-10 Währung, Greek-Handreferenz 1e-12 Aktienäquivalente.
