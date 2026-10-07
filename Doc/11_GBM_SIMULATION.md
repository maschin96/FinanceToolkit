# GBM-Simulation

API: `finance_toolkit.simulation.simulate_gbm`, Ergebnis `GBMPaths`.
Für dS_i = mu_i S_i dt + sigma_i S_i dW_i gilt die exakte Lösung

S_i(t) = S_i(0) exp((mu_i - sigma_i²/2)t + sigma_i W_i(t)).

Die Simulation erzeugt unabhängige normale Inkremente je Zeitschritt und Pfad,
mit Kovarianz rho_ij dt zwischen Aktien. Ein Eigenwert-Faktor der Korrelationsmatrix
unterstützt auch singuläre Matrizen (rho=+1 oder -1). Der Zeitraster ist gleichmäßig;
Anfang und Ende sind enthalten. Der Preisarray hat immer drei Achsen, auch bei
einer Aktie. Bei Horizont null sind alle Zeitpunkte null und alle Preise konstant.

Positive Anfangspreise; endliche Drift; nichtnegative Volatilität und Laufzeit;
positive ganzzahlige Pfad- und Schrittzahlen. Drift/Volatilität sind entweder
Skalare oder 1D-Vektoren mit genau einem Wert pro Aktie. Die Korrelation muss
endlich, symmetrisch, positiv semidefinit und auf der Diagonale eins sein.
Seed ist eine nichtnegative ganze Zahl; Seed und Generator sind gegenseitig
exklusiv. Die Arrays im Ergebnis sind beschreibbar und gehören dem Aufrufer.
Kurse werden vollständig im logarithmischen Raum berechnet; ein Decimal-
Referenztest prüft einen extremen Anfangskurs mit stark negativer Drift.
Overflow oder ein auf null unterlaufener Kurs wird als ValueError abgelehnt.
Für astronomische Pfadgrößen können normale Speicherfehler entstehen; die API
verspricht keine Streaming-Verarbeitung.

## Unabhängige Referenzen und Toleranzen

Die Referenzen folgen direkt aus der obigen analytischen Lösung und den Momenten
einer Normal- bzw. Lognormalverteilung, ohne gespeicherte Simulationsreferenzwerte.

- sigma=0: S0 exp(mu t), relative Toleranz 1e-13 und absolute 1e-12 in den
  verwendeten Kursgrößen 80–110; deutlich oberhalb weniger Float64-Rundungsfehler.
- Terminaler Logreturn: Mittel (mu-sigma²/2)T und Varianz sigma²T.
  Tests für 4.000 und 40.000 Pfade, Seed 51. Toleranz jeweils sechs analytische
  Standardfehler: sqrt(v/n) für das Mittel, v sqrt(2/(n-1)) für die Stichprobenvarianz.
  Der zulässige Stichprobenfehler schrumpft mit n; einzelne Fehler müssen nicht
  monoton schrumpfen. Sechs Standardfehler halten deterministische Tests robust,
  ohne fehlende Drift-/Varianzterme zu verdecken.
- Kreuzkovarianz c_ij=sigma_i sigma_j rho_ij T: 60.000 Pfade, Seed 9,
  rho=0 (Standard) und 0,65. Toleranz sechs sqrt((c_ij²+c_ii c_jj)/(n-1)),
  aus der Kovarianz normaler Stichproben.
- Kursmittel: S0 exp(mu T), Varianz Mittel² (exp(sigma²T)-1).
  40.000 Pfade, Seed 191, sechs Standardfehler; unabhängige Zeitinkremente
  haben Kreuzkorrelation null, Toleranz 6/sqrt(n).
- Perfekte positive/negative Korrelation: Logreturns gleich/entgegengesetzt bei
  mu=sigma²/2. Absolute Toleranz 1e-14 für die kleinen Logreturns.
- Matrixprüfung: absolute Toleranz 1e-12 (dimensionslose Korrelation).
  Minimale negative Eigenwerte innerhalb dieser Rundungstoleranz werden auf null
  abgeschnitten; echte indefinite Matrizen werden abgelehnt.

Weitere Tests: gleiche Seeds, unterschiedliche Seeds, positive Preise, null
Laufzeit, Generatorzustand und unveränderte globale NumPy-Zufallsquelle,
Parametergrenzen und nicht darstellbare Ergebnisse. Das gebaute Wheel wird in CI
außerhalb des Quellbaums mit der gesamten Suite getestet.

Exakte GBM-Schritte erzeugen an Rasterpunkten keinen Euler-Diskretisierungsfehler;
Monte-Carlo-Momentprüfungen mit unterschiedlich großen Stichproben ersetzen hier
einen nicht anwendbaren Euler-Konvergenztest. Das ist Verifikation, keine
empirische Validierung gegen Marktdaten.
