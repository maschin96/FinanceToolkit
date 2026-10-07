# Verifikation und Validierung

Verifikation prüft, ob die implementierten Gleichungen korrekt gelöst werden.
Validierung prüft die Eignung gegenüber beobachteten Marktdaten. M1 verpflichtet
sich zur Verifikation; eine empirische Validierung ist nicht Teil dieses Umfangs.

| Bereich | Unabhängige Erwartung |
| --- | --- |
| GBM | sigma=0: S(t)=S0 exp(mu t); log(S(t)/S0) hat Mittel (mu-sigma²/2)t und Varianz sigma²t |
| Korrelation | Kreuzkovarianz der Logreturns aus sigma_i sigma_j rho_ij t |
| Optionen | Put-Call-Parität C-P=S exp(-qT)-K exp(-rT), bekannte Referenzpreise, Payoff bei T=0 |
| Anleihen | Summe diskontierter Kupons und Tilgung; Nullkupon N exp(-rT); Clean+Stückzins=Dirty |
| Portfolio | Cash plus Marktwerte; entgegengesetzte Positionen heben sich auf; keine doppelte Auszahlung |
| Analyse | Handgerechnete Verluste, Quantile, Tail-Mittel und Drawdown |

Tests verwenden feste Seeds, keinen Netzwerkzugriff und keine Systemzeit.
Numerische Referenzen nennen Quelle/Herleitung, Parameter und Einheit.
Für deterministische Analytik werden absolute und relative Toleranzen vorab
begründet; für Monte Carlo hängen Toleranzen von Stichprobengröße und
analytischem Standardfehler ab. Keine nachträgliche Toleranzerweiterung, um Fehler
zu verdecken. Reproduzierbarkeit gilt innerhalb dokumentierter Abhängigkeitsversionen.

TDD-Nachweis pro ausführbarem Verhalten: Test zunächst wegen fehlendem Verhalten
rot, minimale Implementierung grün, Refactoring mit erneuter Prüfung.
Exakte GBM-Schritte benötigen keinen Euler-Konvergenznachweis; statistische
Konvergenz und Portfolio-Rastergrenzen müssen dennoch geprüft werden.
Die Paketbasis konfiguriert pytest, ruff und mypy sowie die CI-Matrix für
Python 3.11–3.13. Installationstests prüfen Versionsmetadaten und den ausgelieferten
Typing-Marker auch im gebauten Wheel. Numerische Verifikation folgt erst in M1.
