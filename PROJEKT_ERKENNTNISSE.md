# LLM-A*: bisherige Erkenntnisse und Entwicklungsstand

Stand: 16. November 2026 (historische Abschnitte zeitlich eingeordnet). Arbeitsnotiz zur späteren Projektdokumentation.
Historische Ergebnisse und der aktuelle Implementierungsstand werden getrennt.
Die Zahlen stammen aus Codeinspektion und tatsächlich ausgeführten lokalen
Offline-Tests; sie sind keine erfundenen oder auf unbekannte Karten übertragbaren
Leistungsversprechen.

## 1. Projektziel und Rahmenbedingungen

- AI-Universitätsprojekt an der Sungkyunkwan University, Team aus drei Studierenden.
- Abgabe laut Projektvorgabe: 22. November 2026.
- Grundlage: [LLM-A*: Large Language Model Enhanced Incremental Heuristic Search on Path Planning](https://arxiv.org/pdf/2407.02511).
- [Originalrepository](https://github.com/SilinMeng0510/llm-astar).
- Ziel: Originalergebnisse reproduzieren und eine eigenständige algorithmische
  Verbesserung entwickeln, die auch auf unbekannten Karten funktioniert.
- Vom Professor vorgegebenes primäres Evaluationsmodell: GPT-4o mini.
- Das Team berichtete bereits über Reproduktionsarbeiten zu Tabelle 1. Diese
  Ergebnisse und echten GPT-4o-mini-Caches lagen bei unserer Untersuchung nicht
  im Workspace; wir haben sie daher nicht als selbst verifizierte Resultate verwendet.
- Die ursprüngliche Tabelle 1 nutzt GPT-3.5 und Llama 3. Ergebnisse mit GPT-4o mini
  sind eine Reproduktion unter einer anderen Modellbedingung, keine identische
  Wiederholung der ursprünglichen Modellkonfiguration.

Während der hier dokumentierten Entwicklungs- und Testschritte wurden keine
kostenpflichtigen Modellanfragen und keine zusätzlichen LLM-Aufrufe während der
Suche ausgeführt. Prompts und Waypoint-Generierung wurden nicht verändert.

## 2. Aufbau und Funktionsweise des vorhandenen Codes

Die Originalkopie liegt unter [`llm-astar/`](llm-astar/). Implementiert wird in
[`improving_llm_star/`](improving_llm_star/). Beide exportieren den Python-Paketnamen
`llmastar`; bei Experimenten muss deshalb die tatsächlich importierte Kopie
kontrolliert werden. Die Originalkopie wurde für diese Änderungen nicht bearbeitet.

Zentrale Dateien:

| Bereich | Datei / zentrale Funktionen |
|---|---|
| Klassisches A* | [a_star.py](llm-astar/llmastar/pather/a_star/a_star.py): `searching`, `cost`, `heuristic` |
| Verbesserter LLM-A*-Planner | [llm_a_star.py](improving_llm_star/llmastar/pather/llm_a_star/llm_a_star.py): `searching`, `heuristic`, `_update_target`, `_update_queue` |
| Prompts | [prompt.py](improving_llm_star/llmastar/pather/llm_a_star/prompt.py) |
| Modelladapter | [chatgpt.py](improving_llm_star/llmastar/model/chatgpt.py), [llama3.py](improving_llm_star/llmastar/model/llama3.py) |
| Bewegungen / Hindernismenge | [env.py](improving_llm_star/llmastar/env/search/env.py) |
| Segmentkollisionen | [filter.py](improving_llm_star/llmastar/utils/filter.py): `is_lines_collision` |
| Antwortverarbeitung | [utils.py](improving_llm_star/llmastar/utils/utils.py): `list_parse` |
| Datengenerierung | [dataset.py](improving_llm_star/llmastar/dataset/dataset.py) |

### Klassisches A*

Die Karte wird als Gitter mit acht möglichen Bewegungen durchsucht. Gerade
Schritte kosten 1, diagonale Schritte sqrt(2). Die ursprüngliche Heuristik ist
der euklidische Abstand zum Ziel:

$$f(n)=g(n)+h(n).$$

Kollisionen werden für einzelne Bewegungskanten gegen geschlossene
Hindernis-/Grenzsegmente mit Shapely geprüft. OPEN ist ein Min-Heap; PARENT
ermöglicht die spätere Pfadrekonstruktion.

### Ursprüngliches LLM-A*

Ein initialer Modellaufruf erzeugt Waypoints. Bei Texteingaben kann ein
zusätzlicher initialer Parsing-Aufruf nötig sein; strukturierte Dictionaries
vermeiden diese Fehler- und Kostenquelle. Der Planner verarbeitet die Antwort,
filtert bestimmte Punkte und ergänzt Start und Ziel. Ein Waypoint ist jeweils
das aktive Target t.

$$f(n)=g(n)+h(n)+d(n,t).$$

Die Waypoints sind **weiche Suchführung**. Der resultierende Pfad muss sie nicht
alle besuchen. Es werden keine unabhängigen Teilpfade zwischen allen Waypoints
aneinandergehängt. Der globale Zielknoten kann die Suche auch beenden, bevor die
gesamte Targetliste abgearbeitet ist.

Der vorhandene Code schaltet das Target schon beim Erzeugen eines passenden
Nachbarn um, vor dessen Kollisionsprüfung und vor seiner tatsächlichen Expansion.
Dieses Verhalten wurde bisher zur Vergleichbarkeit beibehalten.

## 3. Bei der Codeinspektion bestätigte Schwächen

| Befund | Bedeutung / aktueller Status |
|---|---|
| Zusätzliche Waypoint-Distanz ist allgemein nicht zulässig/admissible | Keine allgemeine Kürzestpfadgarantie; gilt auch für positive adaptive Gewichte |
| Target wird schließlich zum Ziel | Ursprünglich gilt dann g+2h statt klassischem A* |
| Historische CLOSED-Behandlung öffnet bessere Pfade nicht wieder | Im Legacy-Modus erhalten; im korrigierten Engine-Modus behoben |
| Alte Heap-Einträge werden nach einer Verbesserung nicht entfernt und beim Pop nicht verworfen | Historisch redundante Expansionen; korrigierte Engine erkennt und überspringt sie |
| CLOSED ist ursprünglich eine Liste | Lineare Mitgliedschaftsprüfung; korrigierte Engine verwendet zusätzlich ein Kosten-Dictionary |
| Ursprünglicher Heap-Neuaufbau mit vielen `heappush`-Aufrufen | Jetzt `heapify` mit O(Q) beim Neuaufbau; Legacy-Zustandsauswahl wurde gegen das Original geprüft |
| `Env.obs_map()` nutzt halboffene `range`-Intervalle | Hindernisendpunkte können im Filter fehlen, obwohl Shapely sie als blockiert behandelt; noch nicht geändert |
| Waypoint-Filter verwirft auch gültige randnahe Punkte | Noch nicht geändert |
| Keine vollständige Prüfung der Waypoint-Lattice-Zugehörigkeit | Dezimalpunkte können akzeptiert werden, ohne erreichbar zu sein; noch nicht geändert |
| Initialisierung verändert übergebene Range-Listen | Vergleichsrunner kopieren Eingaben tief; ursprüngliche Initialisierung bleibt bestehen |
| Visualisierung erfolgt innerhalb des öffentlichen Suchaufrufs | Experimentelle Suchzeit wird vor Plotting gemessen; Plotting wird in Vergleichen ersetzt |
| Fehlgeschlagene Pfadrekonstruktion setzt ursprünglich ein erreichtes Ziel voraus | Verbesserungskopie meldet jetzt explizit keinen gültigen Pfad; Original bleibt unverändert |
| `list_parse` kann verschiedene Rückgabetypen liefern | Nicht Gegenstand der Alpha-Änderung; weiterhin offene Robustheitsfrage |

Zu Beginn war die Verbesserungskopie im Planner noch identisch mit der
Originalkopie. In `model/__init__.py` stand zusätzlich der Syntaxfehler
`from .llama3 import * kdkd.`. Der überflüssige Text wurde entfernt.

Diese Befunde sind von anfänglichen **Hypothesen** zu unterscheiden: Wie häufig
schlechte Waypoints auftreten, wie stark einzelne Codeprobleme echte Benchmarks
beeinflussen und welche Strategie auf unbekannten Karten gewinnt, war durch die
Codeinspektion allein nicht bekannt.

## 4. Diskutierte Verbesserungen und getroffene Entscheidung

Untersucht wurden adaptive Gewichtung, intelligentes Filtern und erneute
LLM-Planung. Als zusätzliche stärkere theoretische Alternative wurde Focal Search
mit expliziter Pfadkostenschranke vorgeschlagen.

| Ansatz | Motivation | Einordnung |
|---|---|---|
| Geometrisch geprüfte Waypoint-Ausdünnung | Unnötige / schädliche Zwischenpunkte ohne weitere Modellaufrufe entfernen | Ursprüngliche Empfehlung mit geringem Implementierungsrisiko |
| Adaptive Waypoint-Gewichtung | Stärke der LLM-Führung anhand beobachteten Suchfortschritts ändern | Vom Team als Projektschwerpunkt ausgewählt |
| Qualitätsbeschränkte Focal Search | LLM-Führung innerhalb einer durch zulässige Heuristik bestimmten Kostengrenze nutzen | Theoretisch attraktiv, höherer Implementierungsaufwand; nicht implementiert |
| Adaptive LLM-Neuplanung | Bei Schwierigkeiten neue Waypoints anfordern | Zurückgestellt: zusätzliche Kosten, Latenz und experimentelle Störgröße |

Die Entscheidung zugunsten von Adaptive Alpha ist eine Projektentscheidung,
kein bereits nachgewiesener Leistungsgewinn. Eine globale wissenschaftliche
Neuheit wurde nicht behauptet.

## 5. Bisherige Implementierungsschritte

### Schritt 1: konstantes Alpha

Der Konstruktor erhielt `alpha=1.0`, und die Bewertung wurde zu:

$$f(n)=g(n)+h(n)+\alpha d(n,t).$$

`alpha=1` erhält den ursprünglichen Score. `alpha=0.5` halbiert den Waypoint-Term.
Bei `alpha=0` lautet der Score g+h, aber die sonstige Legacy-Suchverwaltung ist
dadurch noch nicht zu einer bereinigten Standard-A*-Engine geworden.

Die erste isolierte Prüfung verglich 12.789 Prioritäten und neun Queue-Neuaufbauten
für alpha=1 mit der bisherigen Implementierung. Die Werte stimmten überein.

### Schritt 2: Fortschrittsmessung ohne automatische Anpassung

`track_progress=True` protokolliert pro aktivem Target unter anderem
Anfangsentfernung, beste Entfernung, Anzahl Verbesserungen sowie aktuelle und
längste Serie ohne Verbesserung. Die Messung veränderte in den geprüften Fällen
weder Suchreihenfolge noch Pfad.

Als Fortschritt gilt eine Verringerung gegenüber der bisher besten akzeptierten
euklidischen Target-Distanz um mehr als `progress_epsilon`. Die erste Beobachtung
legt den Ausgangswert fest. Mehrere kleine Fortschritte können sich gegenüber
dem letzten akzeptierten Bestwert aufsummieren.

Wichtig: Expandierte Zustände sind untersuchte Suchkandidaten. Ein Roboter fährt
nicht automatisch die Reihenfolge aller expandierten Knoten ab.

### Schritt 3: ausführbare Projektumgebung

Eine lokale `.venv` mit Python 3.12.13 wurde eingerichtet und die Projektbibliotheken
sowie pytest installiert. `pip check` meldete keine Konflikte. Echte Imports,
Shapely-Kollisionen, eine Tensoroperation und Grafikexport wurden getestet.
Die Versionen sind in der [Lockdatei](improving_llm_star/requirements-lock-macos-arm64-py312.txt)
festgehalten; Einrichtung: [ENVIRONMENT.md](improving_llm_star/ENVIRONMENT.md).

Die ersten Messungen wurden mangels Bibliotheken und wegen des Importfehlers
isoliert mit einem geschlossenen Segmenttest ausgeführt. Nach der Installation
bestätigten Wiederholungen mit den echten Bibliotheken dieselben Ergebnisse.

Die bestehende OpenAI-Anbindung verwendet weiterhin das ursprüngliche SDK und
GPT-3.5-Modellnamen. Eine neue GPT-4o-mini-Anbindung wurde nicht implementiert.
Der Llama-Konstruktor enthält weiterhin `cuda:3`; Modellgewichte wurden nicht
heruntergeladen. Erfolgreiche Offline-Tests bedeuten keinen getesteten lokalen
Llama-Inferenzbetrieb und keinen getesteten Live-API-Aufruf.

### Schritt 4: erste adaptive Version

Die erste Version passte Alpha auch dann weiter an, wenn das aktive Target schon
das endgültige Ziel war. Sie verwendete die alte CLOSED-/Duplikatbehandlung.
Diese Version ist inzwischen als historischer Ablationsmodus `adaptive_before`
reproduzierbar; ihre Ergebnisdateien wurden nicht überschrieben.

### Schritt 5: Diagnose und Korrekturen

Die 133 Operationen der ersten adaptiven Version wurden anhand von Alpha-Historie,
Expansionsfolge und Queue-Neuaufbauten analysiert. Anschließend wurden auf Auftrag
des Teams Zwischenziel-Adaption und Zielsuche getrennt sowie eine korrigierte
Such-Engine mit veralteten Einträgen und Wiederöffnung implementiert.

## 6. Aktuelle adaptive Regel und ihre Parameter

| Parameter | Experimenteller Standardwert |
|---|---:|
| `stagnation_threshold` | 30 akzeptierte Expansionen ohne Fortschritt |
| `alpha_update_interval` | 10 akzeptierte Expansionen |
| `alpha_decrease` | 0.2 |
| `alpha_increase` | 0.1 |
| `alpha_min` / `alpha_max` | 0.2 / 1.0 |
| `progress_epsilon` | 1e-9 |

Bei einem Zwischenziel wird im Intervall geprüft:

1. Bei ausreichender Stagnation Alpha um den Absenkschritt verringern.
2. Andernfalls bei neuem Fortschritt seit der letzten Prüfung Alpha erhöhen.
3. Andernfalls Alpha beibehalten.
4. Auf die Grenzen begrenzen und nur bei tatsächlicher Änderung OPEN aktualisieren.

Alpha beginnt mit dem Maximum und wird bei einem neuen Zwischenziel darauf
zurückgesetzt. Standardmäßig ist das 1.0. Am finalen Ziel stoppt die Adaption;
der zusätzliche Target-Term entfällt ausdrücklich nur in der verbesserten Variante.

Die Werte sind Ausgangshypothesen. `1e-9` ist eine numerische Toleranz und kein
validierter semantischer Fortschrittsbegriff. Die rein euklidische Metrik kennt
keine Hindernistopologie und kann notwendige Umwege als Stillstand missverstehen.

## 7. Historische Diagnose: warum 133 statt 74 Operationen?

### Testkarte

- Start `(5,10)`, Ziel `(25,10)`.
- Vertikale Wand bei x=15 von y=0 bis einschließlich 14.
- Zwischenziel `(14,5)`; die notwendige Umgehung liegt dagegen oberhalb der Wand.
- Identische vorgegebene Waypoints für alle verglichenen Verfahren.

### Ergebnis vor den Korrekturen

| Größe | Konstant alpha=0.5 | Erste adaptive Version |
|---|---:|---:|
| Heap-Pops / damalige Operationen | 74 | 133 |
| Verschiedene expandierte Zustände | 55 | 90 |
| Wiederholt verarbeitete Zustände | 19 | 43 |
| Pfadlänge | 24.1421 | 24.1421 |
| Alpha-Änderungen | 0 | 5 |
| OPEN-Neuaufbauten | 1 | 6 |

Die Differenz von 59 setzt sich rechnerisch aus 35 zusätzlichen verschiedenen
Zuständen und 24 zusätzlichen Wiederholungen zusammen. Das ist eine Aufteilung
des Zählers, keine additive kausale Zerlegung voneinander unabhängiger Effekte.

### Alpha-Verlauf

| Operation | Ereignis | Alpha danach |
|---:|---|---:|
| 9 | Wechsel vom falschen Zwischenziel zum globalen Ziel | 1.0 |
| 17 | Beste Zielentfernung erreicht 11 bei `(14,10)` | 1.0 |
| 49 | 32 Pops ohne neue beste Distanz | 0.8 |
| 59 / 69 / 79 | weitere Absenkungen | 0.6 / 0.4 / 0.2 |
| 123 | Erster expandierter Zustand hinter der Wand: `(15,15)` | 0.2 |
| 129 | Erholung wegen neuem Fortschritt | 0.3 |
| 133 | Globales Ziel erreicht | 0.3 |

Alle Alpha-Absenkungen wirkten bereits auf das **globale Ziel**, nicht auf den
falschen LLM-Zwischenpunkt. Weil d dann gleich h ist, änderte sich das Gewicht
der Zielheuristik von 2.0 auf 1.2. Die Suche wurde dadurch breiter.

Der Umweg muss die Zielentfernung zwischenzeitlich erhöhen: Von `(14,10)` mit
Abstand 11 geht es etwa über `(14,15)` mit Abstand 12.08 und `(15,15)` mit 11.18.
Die Metrik registrierte deshalb zwischen Operation 17 und 124 keinen neuen
Bestwert, obwohl eine korrekte Umgehung erarbeitet wurde.

Die konstante Variante überquerte die Wand bei Pop 64, die erste adaptive erst
bei 123. Beide benötigten danach genau zehn weitere Pops. Die gesamte Differenz
entstand damit vor der Überquerung.

Die Intervallprüfung verzögerte die erste Reaktion nur um zwei Pops: Die
30er-Grenze war bei 47 erreicht, die nächste Prüfung erfolgte bei 49.

### Einfluss der Engine

Die neu berechneten OPEN-Prioritäten waren korrekt. Dennoch blieben alte
Duplikate im Heap. Neuaufbauten konnten sie mit aktuellen g-Werten nach vorn
holen; der alte Suchloop verwarf bereits geschlossene Zustände beim Pop nicht.
Beispiel: `(10,10)` wurde bei 60, 62 und 63 verarbeitet. Solche Wiederholungen
erhöhten zusätzlich den Stillstandszähler.

Die adaptive Variante bewertete über sechs Neuaufbauten 377 Heap-Einträge neu,
die konstante über einen Neuaufbau 35. Diese Neubewertungen zählen selbst nicht
als Operationen, verursachen aber Laufzeitaufwand.

Schon die frühe Expansionsfolge unterschied sich: Bei Pop 2 wählte Alpha=1
`(6,9)`, Alpha=0.5 dagegen `(6,10)`. Der adaptive Lauf schloss später `(14,10)`
mit g ungefähr 12.66, der konstante mit g=9. Die permanente CLOSED-Behandlung
erschwerte die spätere Korrektur dieser frühen Kostenentscheidungen.

### Temporäre diagnostische Replays vor den Korrekturen

| Veränderung im Diagnose-Harness | Operationen | Befund |
|---|---:|---|
| Erholung deaktivieren | 133 | Gleiche vollständige Popfolge und gleicher Pfad; letzter Anstieg verursachte die Mehrarbeit nicht |
| Alpha-Untergrenze auf 0.5 | 107 | Starkes Abschwächen unter 0.5 trug zur breiteren Suche bei |
| Stagnationsgrenze 10 | 134 | Einfach früher reagieren half in diesem Fall nicht |
| Update-Intervall 1 | 133 | Häufigeres Prüfen allein löste das Problem nicht |
| Konstant 0.5 mit zusätzlichen Neuaufbauten | 91 | Weiterhin exakt dieselben 55 verschiedenen Zustände in derselben Reihenfolge; zusätzliche Duplikat-Pops |
| Zunächst 1, ab Targetwechsel konstant 0.5 | 92 | Frühe Suchhistorie spielt zusätzlich eine Rolle |
| Konstant 0.2 | 147 | Ein kleineres Gewicht war hier keineswegs automatisch effizienter |

Das sind Einzelfall-Diagnosen, keine optimale Parametersuche. Archivierte
Rohtraces: [diagnosis.json](improving_llm_star/experiments/results/adaptive_alpha_diagnosis/diagnosis.json).

## 8. Aktuelle Korrekturen und ausdrücklich verschiedene Scores

| Hauptkonfiguration | Score bei Zwischenziel | Score bei finalem Ziel | Engine |
|---|---|---|---|
| Original alpha=1 | g+h+d | g+2h | Legacy |
| Konstant alpha=0.5 | g+h+0.5d | g+1.5h | Legacy |
| Adaptiv korrigiert | g+h+alpha*d | g+h | Korrigiert |
| Standard-A*-Referenz | g+h | g+h | Eigenständige Standardimplementierung |

Die korrigierte Engine speichert `(Priorität, Zustand, g-Snapshot)` und verwirft
vor dem Verarbeiten Einträge mit veraltetem Snapshot oder nicht verbessertem
bereits expandiertem Zustand. Bessere g-Werte dürfen geschlossene Zustände
erneut öffnen. Diese Wiederöffnungen sind echte zusätzliche Arbeit und werden
separat von verworfenen Duplikaten gezählt.

Bei Neuaufbauten werden veraltete Versionen und Duplikate entfernt. Noch nicht
verarbeitete bessere Pfade zu geschlossenen Zuständen bleiben erhalten. Danach
werden die Prioritäten aktualisiert und mit `heapify` sortiert. Verworfene Pops
erhöhen weder Fortschritts- noch Stagnationszähler.

`robust_search=None` wählt standardmäßig die korrigierte Engine für adaptive
Aufrufe und Legacy für konstante. Konstante Kontrollen können explizit mit
`robust_search=True` ausgeführt werden. `final_goal_weight=0` ermöglicht eine
Kontrolle mit gleichem finalem Score. `intermediate_only=False` dient nur zur
expliziten Reproduktion der früheren adaptiven Ablation.

Der weiter bestehende Targetwechsel vor Kollisionsprüfung wurde nicht in diese
Änderung gemischt. Ebenso unverändert: Prompts, Waypoint-Generierung und Filter.

### Wiederholung des Wrong-Direction-Falls

| Größe | Original | Konstant 0.5 | Adaptiv korrigiert | Standard A* |
|---|---:|---:|---:|---:|
| Raw Heap-Pops | 66 | 74 | 185 | 175 |
| Tatsächlich verarbeitete Expansionen | 66 | 74 | 153 | 153 |
| Verschiedene expandierte Zustände | 54 | 55 | 153 | 153 |
| Duplikat-Pops | 12 verarbeitet | 19 verarbeitet | 32 verworfen | 22 verworfen |
| Pfadlänge | 26.9706 | 24.1421 | 24.1421 | 24.1421 |
| Alpha-Änderungen | 0 | 0 | 0 | 0 |
| OPEN-Neuaufbauten | 1 | 1 | 1 | 0 |

Laufzeiten der Wiederholungen stehen mit vollständiger Konfiguration in der
[aktuellen CSV](improving_llm_star/experiments/results/adaptive_alpha_corrected/summary.csv).

**Es gibt hier keinen Effizienzgewinn der korrigierten adaptiven Variante.**
Das unbeabsichtigte Verändern der Zielheuristik und das redundante Verarbeiten
alter Zustände wurden behoben, aber g+h expandiert in dieser Karte mehr Zustände.
Die 32 verworfenen Einträge bleiben als billige Heap-Extraktionen im Rohzähler
sichtbar. Korrekte Duplikatbehandlung bedeutet nicht, dass keine alten Einträge
mehr aus einem Heap entnommen werden können.

Wichtig für die Attribution:

- Nur die Finalzielkorrektur, mit Legacy-Engine: ebenfalls 185 Pops, aber 185
  tatsächliche Verarbeitungen einschließlich 32 Duplikaten.
- Beide Korrekturen: dieselben 185 Pops, aber nur 153 Verarbeitungen.
- Nur korrigierte Engine bei früherer Adaption: 177 Pops, 144 Verarbeitungen,
  86 verschiedene Zustände und 58 sinnvolle Wiederöffnungen.
- Feste Zwischenzielgewichtung 1 mit korrigierter Engine und g+h am Ende:
  exakt dasselbe Verhalten wie die korrigierte adaptive Variante in diesem Fall.
  Denn während des kurzen Zwischenzielabschnitts trat keine Anpassung auf.

Damit ist dieser Fall ungeeignet, einen Nutzen tatsächlicher Zwischenziel-
Adaption nachzuweisen. Im öffentlichen Prompt-Beispiel treten dagegen echte
Zwischenzielanpassungen auf; auch das ist noch kein Generalisierungsnachweis.

## 9. Metriken, Fairness und Grenzen der bisherigen Versuche

### Daten und Versuchsumfang

Der öffentliche Datensatz enthält 100 Karten mit je zehn Start-Ziel-Paaren,
also 1.000 Queries. Alle liegen im gleichen Größenbereich; die Datengenerierung
enthält eine manuelle Kartenauswahl. Die Prompts überschneiden sich mit Teilen
des öffentlichen Datensatzes. Diese Punkte begrenzen die Aussagekraft öffentlicher
Ergebnisse für unbekannte Karten.

Unsere bisherigen Vergleiche nutzten **sechs feste Fälle**, davon fünf
handgeschriebene und ein Beispiel aus dem Repository-Prompt. Es wurden nicht
alle 1.000 Queries und keine unabhängigen echten GPT-4o-mini-Stichproben evaluiert.

Der erste adaptive Vergleich enthielt 72 zeitlich erfasste Läufe:
6 Fälle × 4 Varianten × 3 Wiederholungen. Der korrigierte Vergleich einschließlich
sieben Zusatzkontrollen enthält 198: 6 × 11 × 3. Warmups und Original-Audits
kommen hinzu. Das sind keine 198 unabhängigen Karten oder Modellantworten.

### Bedeutung der Kennzahlen

- `operation` / `heap_pops`: alle Pops, auch verworfene, einschließlich Ziel-Pop.
- `expanded_nodes`: tatsächliche Verarbeitungen; legitime Reopens zählen erneut.
- `unique_expanded_nodes`: verschiedene tatsächlich expandierte Zustände.
- `duplicate_pops`: alte Wiederholungen; im Legacy-Modus verarbeitet, korrigiert
  verworfen. Sinnvolle Reopens werden gesondert gezählt.
- `stale_pops` und `closed_pops`: Anzahl übersprungener Einträge; null im
  Legacy-Modus bedeutet keine aktivierte Prüfung, nicht Abwesenheit alter Einträge.
- `storage`: Anzahl g-Dictionary-Einträge, historisch auch mit unendlichen Kosten.
  Das ist keine direkte Spitzen-RAM-Messung. Zusätzliche Dictionaries und
  Logging können selbst Speicher benötigen.
- Pfadkosten: Summe der tatsächlichen Kantenlängen des rekonstruierten Pfads.
- Gültigkeit: Start/Ziel, erlaubte Bewegungen, Grenzen und Kollisionen werden geprüft.
- Suchzeit: Suchloop, Queue-Verwaltung, Rekonstruktion und Validierung; ohne
  Modellanfrage, Umgebungsaufbau und Visualisierung. Keine End-to-End-API-Latenz.

Beim alten Standard-A*-Report waren dessen Operationen nur nicht veraltete Pops.
Der neue Report weist für alle Modi Raw Pops und echte Expansionen getrennt aus.
Eine Änderung dieses Zählers darf nicht als Algorithmusverschlechterung ausgegeben
werden. Die Standardreferenz speichert außerdem keine unendlichen Kosten für
blockierte Nachbarn; Storage-Zahlen sind entsprechend vorsichtig zu vergleichen.

### Fairer Vergleich

Die Runner verwenden identische Karten, Start-/Zielpunkte und rohe Antworten.
Eingaben werden tief kopiert. Alle LLM-Varianten durchlaufen dieselbe unveränderte
Antwortverarbeitung und erhalten dieselbe Fortschrittsinstrumentierung. Die
Reihenfolge der Modi wird pro Wiederholung mit dokumentiertem Seed gemischt.
Ausgewiesen werden alle Messungen und Mediane, keine ausgesuchten Bestläufe.

Die Originalkontrolle wird außerhalb der Zeitmessung gegen den unberührten
Originalcode auf Operationszahl, Storage, Pfadlänge und exakten Pfad geprüft.
Zusatzkontrollen trennen Such-Engine, finalen Score und dynamische Adaption.

Kurze lokale Laufzeiten sind verrauscht. Wiederholte Verwendung derselben
Antwort prüft Rechenzeitstreuung, nicht die Stochastik des LLM.

### Optimalität

Positive Zwischenzielterme können wahre Restkosten überschätzen. Dynamische
Gewichte können zusätzlich inkonsistent sein. Die neue Wiederöffnung behebt
eine Suchverwaltungs-Schwäche, beweist aber keine allgemeine Optimalität des
LLM-geführten Gesamtverfahrens: Das Ziel kann schon während einer noch aktiven
unzulässigen Zwischenzielheuristik ausgewählt werden.

Die Standard-A*-Referenz verwendet euklidische, zulässige Zielheuristik und
dieselben legalen Kanten. Sie dient als Pfadkostenreferenz. Für weitere
Korrektheitsprüfungen ist Dijkstra auf kleinen Karten sinnvoll.

## 10. Tests, Artefakte und Ausführung

Chronologischer Teststand: zuerst 10 Umgebungstests; nach erster Adaption 37
Tests; nach den beiden Korrekturen 45 bestandene Tests. Diese Zahlen bezeichnen
die jeweiligen Entwicklungsstände und keine unabhängigen wissenschaftlichen
Experimente.

Abgedeckt werden unter anderem Alpha-Absenkung und Erholung, Grenzen, Intervalle,
Zwischenzielreset, keine finalen Updates, korrektes Repriorisieren, Duplikate,
veraltete Kostenversionen, bessere Pfade mit Wiederöffnung, gültige/konsistente
Pfadkosten, unerreichbare Ziele, unveränderte konstante Varianten sowie Caching.
Netzwerkverbindungen sind in den Tests blockiert.

```sh
source .venv/bin/activate
python -m pytest improving_llm_star/tests -q
python improving_llm_star/experiments/compare_adaptive_alpha.py \
  --include-controls --repeats 3 --warmups 1
```

Echte gespeicherte Modellantworten können mit `--cache pfad/zum/cache.json`
eingespielt werden. Das Format steht in der Implementierungsdokumentation.

Wichtige Artefakte:

- [Ursprüngliche Analyse als PDF](LLM_AStar_Algorithm_Improvement_Analysis.pdf).
- [Adaptive-Alpha-Dokumentation](improving_llm_star/experiments/ADAPTIVE_ALPHA.md).
- [Korrekturen und Ablationsdefinitionen](improving_llm_star/experiments/SEARCH_CORRECTIONS.md).
- [Vergleichsrunner](improving_llm_star/experiments/compare_adaptive_alpha.py).
- [Historischer erster Vergleich](improving_llm_star/experiments/results/adaptive_alpha/report.md).
- [Aktueller korrigierter Vergleich](improving_llm_star/experiments/results/adaptive_alpha_corrected/report.md).
- [Aktuelle vollständige Messungen](improving_llm_star/experiments/results/adaptive_alpha_corrected/comparison.json).
- [Aktuelle Alpha-Ereignisse](improving_llm_star/experiments/results/adaptive_alpha_corrected/alpha_events.csv).

Die JSON-Ausgaben enthalten Konfigurationen, Inputs und Quellcode-Hashes. Alte
Ergebnisse werden als historischer Stand erhalten und nicht mit neuen Algorithmen
oder geänderten Metrikdefinitionen vermischt.

## 11. Offene Forschung und sinnvolle nächste Schritte

1. Gespeicherte GPT-4o-mini-Antworten des Teams in das Replay-Format übernehmen.
2. Nach ganzen Karten aufteilen: Development, Validation und Test. Start-Ziel-Paare
   derselben Karte nicht auf beide Seiten der Aufteilung verteilen.
3. Neue unabhängige Kartenfamilien hinzufügen: U-förmige Fallen, schmale Durchgänge,
   wechselnde Wände, offene Karten, größere Dimensionen und unlösbare Fälle.
4. Parameter auf Entwicklungskarten untersuchen; vor dem finalen Test einfrieren.
   Keine Einstellung nur auf den sechs öffentlichen/handgeschriebenen Fällen auswählen.
5. Adaption gegen feste Gewichte mit gleicher Engine und gleichem finalem Score
   vergleichen. Sonst wird möglicherweise ein Engine- oder Scoring-Effekt als
   Alpha-Erfolg ausgegeben.
6. Fortschrittsmaß untersuchen: euklidischer Bestwert versus sinnvollere
   topologische oder kostenbezogene Signale. Notwendige Umwege berücksichtigen.
7. Ablationen: Erholung, Absenkung, Intervall und Grenzen getrennt bewerten.
8. Operation/Storage/relative Länge später pro Query normieren und wie im Paper
   geometrisch aggregieren. Aktuelle Reports zeigen noch Falltabellen und
   Wiederholungsmediane, keine vollständige Tabelle-1-Aggregation.
9. Fehler, Timeouts, Verteilungen und schlechte Extremfälle mit ausweisen.
   Pfadkosten nur für ausdrücklich bezeichnete erfolgreiche Vergleiche berechnen;
   gescheiterte Pfade nicht als Länge null behandeln.
10. Für LLM-Robustheit mehrere unabhängig generierte Antworten pro ausgewähltem
    Problem nutzen. Gleiche rohe Antworten zwischen Algorithmusvarianten cachen.
    Tokenverbrauch, API-Latenz und tatsächlich abgerechnete Kosten dann separat
    dokumentieren; diese wurden in unseren Offline-Läufen nicht gemessen.

**Gesicherter aktueller Beitrag:** Eine experimentell konfigurierbare
Zwischenzielgewichtung, eine überprüfte Fortschrittsinstrumentierung, eine
korrigierte optionale Such-Engine und ein kontrollierter Vergleichsaufbau sind
implementiert. Ein allgemeiner Geschwindigkeits-, Speicher- oder
Generalisierungsvorteil ist bislang nicht nachgewiesen.

---

## Autonome Forschungsphase am 13.11.2026

Experimenteller Branch: `research/waypoint-guidance`; kein Push, kein Merge in
`main`, keine bezahlten API-Aufrufe. Die alten Baselines und historischen Resultate
bleiben erhalten. Nach dem zwischenzeitlichen Repository-Abgleich sind nun 3.000
gecachte Antworten (Standard/CoT/RePE) vorhanden; frühere Aussagen über fehlende
Caches beziehen sich auf den damaligen Stand. Das Notebook bezeichnet das Modell
als GPT-4o mini; die Rohantworten allein belegen Modellversion/Parameter nicht.

### Warum die bisherige Alpha-Regel oft zu spät reagiert

600 Entwicklungsfälle auf 60 ganzen Karten untersucht: Der Originalalgorithmus
wechselt bereits bei einem **generierten Nachbarn**, noch vor Kollisions- und
CLOSED-Prüfung. Median der aktiven Waypoint-Lebensdauer: ein Queue-Pop, p90: 15;
93,45 % der gewechselten Ziele leben weniger als 30 Pops. 298 Zielwechsel haben
Lebensdauer null; mehrere Ziele können in einer Nachbarschleife wechseln.
1,15 % der Wechsel wurden durch eine blockierte Kante ausgelöst. Die korrigierte
adaptive Variante verändert Alpha in 205/600 Fällen tatsächlich. Ihre finale
`g+h`-Suche und die originale `g+2h`-Suche müssen als weiterer Unterschied getrennt
betrachtet werden; höhere Expansionen sind nicht allein Alpha zuzuschreiben.

Von 5.118 unterschiedlichen Zwischenpunkten sind 14,91 % ungültig/unerreichbar.
41,62 % sind ungültig/unerreichbar oder würden bei erzwungenem Durchlaufen einen
optimalen Umweg >10 % erzeugen. Dieses Offline-Label ist ein Risikomaß und kein
kausaler Beweis für Schaden durch weiche Heuristiklenkung.

### Mehrere untersuchte Forschungsrichtungen

Geprüft wurden Wechsel erst beim Expandieren, Zielbudgets, geometrische Konfidenz,
Waypoint-Ausdünnung, bounded Focal Search, eine attraktive statt strafende
Heuristikkomponente, verifizierte Waypoint-Routen mit verschiedenen Stopregeln,
lokale Punktreparatur und geometrische Zertifikate. Negative Ergebnisse sind im
[Experimentprotokoll](improving_llm_star/experiments/research/EXPERIMENT_LOG.md)
aufgehoben. Einfacher späterer Zielwechsel erhöhte die Expansionen deutlich;
Focal Search verursachte zusätzliche Heap-Arbeit; Konfidenz/Ausdünnung schlug die
vergleichbare zielbasierte Weighted-A*-Kontrolle nicht überzeugend.

### Stärkste belegte Variante: Certificate-First Waypoint Search

Neue Klasse `CertifiedLLMAStar`, bestehende Klasse unverändert weiter nutzbar.
Aus jedem rohen Zwischenpunkt entstehen höchstens fünf freie Kandidaten (Punkt
und vier axiale Nachbarn). Ein kleiner gerichteter Graph verbindet passende
Schichten über vollständig kollisionsgeprüfte Gitterpfade. Kandidaten und Kanten
werden anhand optimistischer Octile-Kosten vorgefiltert. Maximal 4.096 tatsächliche
Kantenprüfungen einschließlich fehlgeschlagener Versuche. Eine zulässige untere
Schranke kombiniert Octile-Distanz mit dem **Maximum**, nicht der Summe,
unabhängiger Einzelwand-Umwegschranken.

Ein Kandidatenpfad wird nur direkt übernommen, wenn seine Kosten die zulässige
untere Schranke erreichen: Dann ist er optimal bis auf numerische Toleranz.
Andernfalls wird er verworfen und exakt die gleiche robuste Weighted-A*-Suche
mit Gewicht 2 wie im Kontrollfall ausgeführt. Damit keine universelle
Optimalitätsgarantie: akzeptiertes Zertifikat optimal, sonst gewichtete Suche
mit Faktor-2-Schranke. Kein zusätzliches LLM während der Suche.

### Zurückgehaltene Tests und ehrliche Einordnung

Auswahl nach 600 Entwicklungs- und 200 Validierungsfällen, Parameter vor Test
festgeschrieben. Reale Testcaches: 20 ungesehene Karten, 200 Start/Ziel-Paare,
je drei Promptvarianten = 600 Beobachtungen. Ganze Karten bilden die statistischen
Cluster; Promptvarianten sind keine unabhängigen Modellwiederholungen.

| Messgröße | Original | Neue Variante |
|---|---:|---:|
| Mittlere unterschiedliche expandierte Zustände | 215,98 | 168,99 |
| Mittlere Heap-Pops | 343,92 | 365,68 |
| Geometrisches Mittel Kosten / Optimum | 1,02254 | 1,01035 |
| Gültige gefundene Pfade | 600/600 | 600/600 |

21,76 % weniger unterschiedliche Expansionen; 95%-Cluster-Bootstrap-Intervall
für das Verhältnis etwa [0,696; 0,851]. **6,33 % mehr Heap-Pops**; daher keine
pauschale Operationsverbesserung behaupten. Gegen identische WA2-Kontrolle nur
5,36 % weniger unterschiedliche Expansionen, gegen direkte geometrische
Abkürzung allein 3,25 %: Das ist der sauberer isolierte zusätzliche Waypoint-Effekt.
137 optimale Frühzertifikate gegenüber 75 ohne Waypoints. Ohne lokale Reparatur
105, ohne Wand-Schranke 79; beide Komponenten tragen bei, aber nicht unabhängig.

Auf 192 prozeduralen Tests aus acht Kartenfamilien: 168/168 lösbare Fälle gültig,
24/24 unerreichbare Fälle korrekt abgelehnt. Bei lösbaren Fällen 19,33 % weniger
unterschiedliche Expansionen als Original. Zusätzlicher Waypoint-Vorteil gegenüber
direktem Shortcut nur in zwei Fällen; schwächere Evidenz für breiten synthetischen
Nutzen, kleine Regression in der Maze-Familie. Fixtures sind deterministisch
synthetisch, keine echten LLM-Antworten; hilfreiche Fixture-Punkte verwenden den
Referenzpfad ausschließlich bei der Benchmark-Erstellung.

Native Laufzeitmessung mit frischer Geometrie (40 feste Testanfragen, drei
randomisierte Wiederholungen): Median Original 38,57 ms, identische WA2-Kontrolle
1,57 ms, direkter Shortcut 1,42 ms, neue Variante 2,24 ms. Der große Gewinn gegenüber
Original enthält Engine-/Geometrieoptimierungen. Waypoint-Zertifizierung selbst
kostet gegenüber effizienten Kontrollen zusätzliche CPU-Zeit. Speicherzähler
sind keine bytegenaue RAM-Messung und erfassen nicht alle Hilfsstrukturen.

113/600 Fälle expandieren mehr und 45/600 haben längere Pfade als das Original;
das maximale Kostenverhältnis ist trotz besserem Mittel/p95 etwas schlechter.
Keine solchen Rückschritte gegenüber identischer WA2-/Shortcut-Kontrolle.
Unabhängige Shapely-Prüfung aller 768 erfolgreichen Testpfade; alle 219 Zertifikate
optimal; Originalzahlen für alle 600 gecachten Testbeobachtungen identisch zu
bestehenden Table-1-Aufzeichnungen. 65 automatisierte Tests bestehen.

[Algorithmus, Pseudocode und exakte Befehle](improving_llm_star/experiments/research/README.md),
[Tabellen und Statistik](improving_llm_star/experiments/results/research/REPORT.md),
[exportierbare Grafik](improving_llm_star/experiments/results/research/expansions.pdf).
Für die Abgabe eignet sich der belegte Wechsel von reaktiver Alpha-Steuerung zu
selektiver zertifizierter Guidance als Forschungsbeitrag. Etablierte Einzelteile
(Weighted A*, untere Schranken, DAG) nicht als neue Algorithmen ausgeben. Weitere
ungesehene Karten und RAM-Messungen bleiben sinnvoll; Testkarten nicht nachträglich
zur Parametertuning-Menge machen.

---

## Zweite autonome Forschungsphase am 16.11.2026

Der Forschungsbranch bleibt `research/waypoint-guidance`; kein Push/Merge, keine bezahlten Modellaufrufe. Alte Baselines und historische Resultate bleiben unverändert. Die Auswahl wurde in Commit `87c3310` vor Erzeugung der frischen Testkarten festgeschrieben.

### Tatsächlicher Laufzeitengpass und neue Verfahren

Das Ausgangsprofil auf 120 Entwicklungsfällen zeigt: Nachbarerzeugung und Kollisionsprüfung dominieren. Die untere Schranke kostet etwa 0,1 % der instrumentierten Gesamtzeit; Heap-Primitive zusammen unter 1 %. Kumulative Profilerzeiten überlappen und werden nicht addiert.

Implementiert: Zeilen-/Spaltenindex für ganzzahlige Wände, direkte Einzelkantenabfragen, exakte Prüfung kurzer Gitterrouten als zwei gerade Teilstücke, erreichbarkeitsbasierter DAG, kollineare Waypoint-Kompression und schlankere robuste Fallback-Suche. Nichtganzzahlige Geometrie und degenerierte Wände behalten die tatsächlichen Einzelschritt-Kollisionsregeln. Alle Indizes/Caches werden pro Anfrage frisch bezahlt.

**Entscheidender neuer Ansatz:** Aus der zulässigen Einzelwand-Schranke lassen sich Wandend-Kandidaten ableiten. Ein vollständig geprüfter Weg durch einen solchen Punkt wird nur übernommen, wenn seine Kosten die zulässige untere Schranke erreichen. Sonst läuft Weighted A* mit Gewicht 2. Optional folgt davor ein exakter Waypoint-DAG oder eine separate Variante mit verifizierter Waypoint-Route als oberer Schranke.

**Der stärkste Laufzeitgewinn ist geometrisch, nicht LLM-spezifisch.** `WitnessFirstLLMAStar(use_waypoints=False)` benötigt keinen Modellaufruf. Die Waypoint-Ergänzung muss gegen genau diese Variante verglichen werden, nicht nur gegen das Original.

### Festgelegte Abschlussauswertung

Frisch: 80 neue Karten, 640 Fälle, zehn Familien einschließlich großer Zufalls-/Labyrinthkarten, elf Wiederholungen je Verfahren. 576 Fälle lösbar, 64 absichtlich unerreichbar. Hilfreiche Hinweise sind optimale Referenzpfad-Ecken ausschließlich als synthetische Fixtures; keine echten neuen LLM-Ausgaben. Seed660000 ist von Entwicklung440000 und Validierung550000 sowie allen alten Seeds getrennt.

Zusätzlich: 600 bereits in Sitzung 1 geöffnete Modellcache-Beobachtungen auf 20 Karten, drei Promptvarianten, sieben Wiederholungen. Diese Wiederholung heißt ausdrücklich **geöffnete Bestätigung**, nicht neuer unabhängiger Holdout. Wiederholungen werden pro Fall per Median reduziert; Konfidenzintervalle resampeln ganze Karten.

| Variante | Frische Fälle: mittlere Fallmedian-ms | Geöffnete Modellcaches: mittlere Fallmedian-ms | Cache: unterschiedliche Expansionen | Cache: Kosten / Optimum (geom.) |
|---|---:|---:|---:|---:|
| original_indexed | 53.5733 | 7.8036 | 215.98 | 1.02254 |
| old_cf | 12.1143 | 3.1204 | 168.99 | 1.01035 |
| scheduled_wa2 | 1.7073 | 0.9223 | 178.56 | 1.01447 |
| witness_only | 1.6356 | 0.5421 | 100.66 | 1.00496 |
| witness_cf | 1.6531 | 0.5662 | 100.66 | 1.00496 |
| witness_chain | 1.5383 | 0.5481 | 100.49 | 1.00520 |
| witness_frontier | 1.6062 | 0.5643 | 99.77 | 1.00463 |

`original_indexed` bewahrt die originale Suchlogik, verwendet jedoch dieselbe neue Geometrie. Native Originalmessungen stehen separat im Report; diese Kontrollen nicht vermischen. Alle Vorverarbeitungskosten sind in den End-to-End-Kernzeiten enthalten.

Witness-only gegenüber identisch optimierter WA2-Kontrolle auf frischen Fixtures: Zeitverhältnis 0.9580, 95%-Karten-Bootstrap [0.9051; 0.9873].
Witness-only gegenüber identisch optimierter WA2-Kontrolle auf geöffneten Modellcaches: Zeitverhältnis 0.5878, 95%-Karten-Bootstrap [0.4276; 0.7312].

Zusätzliche exakte LLM-Stufe auf Modellcaches: Zeitverhältnis zu Witness-only 1.0445 [1.0337; 1.0587], 0 tatsächlich übernommene Waypoint-Routen. Die stärkeren geometrischen Gewinne dürfen ihr nicht zugeschrieben werden.

Die Raw-Chain/Frontier-Variante kann sehr gute synthetische Routen nutzen. Das belegt bedingtes Potenzial bei hochwertigen Hinweisen, nicht dieselbe Wirksamkeit realer Modellantworten. Frontier-Routen sind nur Faktor-2-beschränkt und können gegenüber der Kontrolle länger sein. Exakte Zertifikate bleiben optimal; das gesamte Verfahren ist wegen des Weighted-A*-Fallbacks nicht generell optimal.

### Korrektheit, Speicher und Messgrenzen

82 automatisierte Tests bestanden nach den neuen Geometrie-, Bound-, Schnittstellen- und Budgettests. Eine zusätzliche unabhängige Shapely-Prüfung aller ausgewählten Abschlussvarianten sowie Kosten-/Zertifikatprüfung gegen A* ist im Verification-Artefakt gespeichert. Originaloperationen und -kosten werden erneut gegen die vorhandenen Table-1-Daten geprüft.

Python-tracemalloc auf 24 festen Entwicklungsfällen: mittlerer Peak ungefähr 225 kB alte Zertifikatsvariante, 138 kB Witness-only, 188 kB schlanke WA2-Kontrolle. Importierte Bibliotheken und native GEOS-Allokationen fehlen; keine vollständige RAM-/RSS-Aussage. Historische Storage-Zähler erfassen nicht alle Hilfsstrukturen.

Die erste native Testmessung wurde wegen einer falschen Einordnung gepufferter Statusausgabe unterbrochen; daraus werden keine Zahlen berichtet. Der vollständige Kernvergleich blieb erhalten. Wiederholung mit Journal pro Durchlauf und **einheitlichem Zwei-Sekunden-Limit für alle nativen Verfahren**: zensierte Originalzeiten werden nur als untere Laufzeitschranken ausgewiesen. Keine exakten vollständigen Originalmittelwerte daraus ableiten. Verfahrensparameter wurden dabei nicht geändert.

Negative Ergebnisse: einfache Stagnations-/Dichtegates und spätere Zertifizierung brachten keinen überzeugenden Zusatzgewinn; enge Waypoint-Korridore erhöhten Aufwand und teilweise Pfadlängen. Unzertifizierte Incumbents können helfen, kosten auf realen Caches aber häufig mehr als sie sparen. Frühere Source-Hash-/JSON-Probleme sind mit separaten Hinweisen archiviert; finale Läufe sichern Source-Snapshots zu Beginn.

### Empfehlung für die Abgabe

Die Arbeit als evidenzgeleitete Untersuchung selektiver Guidance darstellen: ursprüngliche Adaptive-Alpha-Hypothese, gemessene kurze Waypoint-Lebensdauer, verifizierte Routen, dann schnelle geometrische Zertifikate mit sauberer LLM-Ablation. Nicht behaupten, dass der große Laufzeitgewinn von LLM-Intelligenz stammt. Für den stärksten Laufzeitstand Witness-only; die exakte LLM-Ergänzung und Raw-Chain-Incumbents als unabhängig bewertete Optionen zeigen. Weitere Modelle/Antworten und schwierigere Karten sind nötig, bevor ein echter LLM-Laufzeitvorteil behauptet werden kann.

[Algorithmus, Pseudocode und exakte Befehle](improving_llm_star/experiments/research/session2/README.md), [Tabellen und Konfidenzintervalle](improving_llm_star/experiments/results/research_session2/REPORT.md), [Forschungslog](improving_llm_star/experiments/research/session2/EXPERIMENT_LOG.md), [Grafiken als PDF](improving_llm_star/experiments/results/research_session2/runtime.pdf).

---

## Dritte autonome Forschungsphase am 16.11.2026

Ziel: tatsächlichen Beitrag echter LLM-Waypoints gegenüber gleicher Geometrie und gleichem Suchkern nachweisen. Neue Verfahren vor der Validierung in Commit `79b96f3` eingefroren. Keine alten Testkarten für Auswahl verwendet, keine bezahlten API-Aufrufe, kein Push/Merge. Baselines und historische Resultate bleiben erhalten.

### Neue Strategie und geprüfte Alternativen

**Verifizierte Präfix-Seeds:** Ein vollständiger Waypoint-Pfad muss nicht gelingen. Ein tatsächlich kollisionsfreier Gitterpfad vom Start zu einem ausgewählten Zwischenpunkt liefert dessen echten g-Wert in OPEN; der normale Start bleibt verfügbar. Rangfolge nach `octile(s,t)+2*h(t)`, Belegung/Umwegfilter, primär `octile(s,t)+octile(t,g)<=1.1*L` mit zulässiger geometrischer Schranke L. Sortierte Kandidaten werden lazy geprüft; erster gültiger Link liefert denselben Seed wie die vollständige Prüfung. Bei besseren Pfaden wird ein alter Makro-Elternpfad ersetzt, Zustände werden wieder geöffnet.

Der normale Score bleibt exakt `g+2*h_goal`; keine versehentliche Abschwächung der finalen Zielheuristik. Tatsächlich ausgegebene Makros bestehen aus originalen Einzelschritten mit echten Kosten. Damit Faktor-2-Schranke, keine allgemeine Optimalitätsgarantie. Als weitere Richtungen geprüft: mehrere Seeds, Präfixketten, unmittelbare Konfidenzgewichtung, begrenztes sichtbares Waypoint-Potenzial und Tie-Breaking.

### Warum wenig nutzbare Information übrig bleibt

Von 600 Entwicklungsfällen löst Witness bereits 467 ohne Suche. Von den verbleibenden 133 besitzen 99 einen geometrisch brauchbaren Zwischenpunkt. Die alte matched Guidance verbessert dennoch nur bei 15 die Expansionen, bei 22 die Pfadlänge und bei drei beides. Originalziele leben im Median einen Pop; 93,45 % wechseln vor 30 Pops. Ein brauchbarer Punkt ist daher weder ein Beweis für Suchnutzen noch für rentablen Zusatzaufwand.

### Kontrollierte Abschlussauswertung

600 echte gecachte Validierungsbeobachtungen, 20 ganze Karten, Standard/CoT/RePE, neun interleavte Wiederholungen. Dieser historische Validierungssplit wurde schon in früheren Sitzungen verwendet; kein neuer unabhängiger Realmodell-Holdout. Zusätzlich 30 neue kanonisch geometrisch disjunkte Karten, 240 Fälle aus zehn Familien, sieben Wiederholungen. Hilfreiche neue Fixtures sind oracle-basiert und keine echten LLM-Ausgaben. Unabhängige Prüfung auf Überschneidung mit bisherigen gespeicherten Geometrien bestanden.

| Variante | Echte Validierung: mittlere Fallmedian-ms | Unterschiedliche Zustände | Kosten/Optimum (geom.) | Frische Fixtures: ms |
|---|---:|---:|---:|---:|
| original_indexed | 5.5859 | 165.70 | 1.02698 | 138.0725 |
| scheduled_wa2 | 0.6827 | 127.70 | 1.01607 | 4.0195 |
| witness_only | 0.3378 | 59.88 | 1.00362 | 3.8710 |
| witness_cf | 0.3572 | 59.70 | 1.00362 | 3.8974 |
| guide_off | 0.3436 | 59.88 | 1.00362 | 3.9199 |
| seed_cut | 0.3434 | 58.87 | 1.00451 | 3.9182 |
| seed_lazy | 0.3412 | 58.67 | 1.00465 | 3.9244 |
| geometry_lazy | 0.3469 | 58.04 | 1.00527 | 4.0030 |
| seed_cut_wrong | 0.3393 | 58.30 | 1.00487 | 3.9627 |
| seed_cut_random | 0.3443 | 58.58 | 1.00526 | 3.7706 |
| potential_visible | 0.4338 | 78.07 | 1.00276 | 3.9522 |
| potential_geometry | 0.5276 | 97.36 | 1.00196 | 3.5588 |
| potential_random | 0.4645 | 82.19 | 1.00308 | 3.9030 |
| uniform15 | 0.3708 | 68.98 | 1.00135 | 3.7244 |

Primärvariante gegenüber identischem Kern ohne Guidance: Zeitverhältnis 0.9993, 95%-Karten-Bootstrap [0.9680; 1.0253]. Kein abgesicherter Laufzeitgewinn. 22 Fälle mit weniger und 11 mit mehr Zuständen; 2 kürzere und 14 längere Pfade. 58/600 Anfragen übernehmen einen Seed; das bedeutet nicht, dass der Seed im Endpfad verwendet wird.

**LLM-Beitrag nicht nachgewiesen:** Falsche Anfragen derselben Karte, zufällige freie Punkte und geometrische Seed-Kandidaten sind insgesamt konkurrenzfähig. Shuffle verändert bei der absichtlich reihenfolgeunabhängigen Rangfolge weder Kosten noch Zähler. Einzelne weniger expandierte Zustände reichen daher nicht als Beweis für nützlichen semantischen LLM-Inhalt.

Das sichtbare Waypoint-Potenzial verbessert einige Pfade, kostet aber deutlich mehr Laufzeit. Die einfache reine Zielgewichtung 1,5 erzielt auf realer Validierung kürzere Pfade bei weniger Laufzeit als dieser LLM-Qualitätskandidat. Die scheinbare Qualitätsverbesserung ist damit kein überzeugender spezifischer LLM-Vorteil.

Öffentliche Schnittstelle, 40 feste Validierungsanfragen, sieben Wiederholungen, Warmup ausgeschlossen: Seed ohne Guidance rund 0,371 ms, mit echten Hinweisen 0,435 ms, Witness ohne LLM 0,374 ms. Parsing, Kopieren und gesamte Vorverarbeitung zählen hier mit; kein Netzwerk. Ein im Kern kaum messbarer Vorteil verschwindet somit im vollständigen Aufruf.

98 Tests bestehen. Unabhängige Shapely-/Kosten-/Faktor-2-Prüfung für drei Kandidaten auf allen 600 echten und 216 lösbaren frischen Fällen; 24 unerreichbare frische Fälle korrekt gemeldet. Gegen alle A*-Referenzen stimmt die Erreichbarkeit. Ganze Karten werden gebootstrappt; sekundäre Mehrfachvergleiche sind explorativ und nicht adjustiert.

### Empfehlung

Witness-First als stärksten bisherigen Laufzeitstand behalten. Präfix-Seeding als sauber implementierte, aber nicht erfolgreich bestätigte LLM-Erweiterung dokumentieren. Für weitere Arbeit braucht es vor allem hochwertige echte Hinweise auf komplexen, nicht geometrisch trivialen Karten und eine neue unverbrauchte reale Testmenge. Nicht weiter ausschließlich Stagnationstimer oder Schwellen auf denselben öffentlichen Antworten optimieren. Negative Resultate, Zufalls-/Falschantwort-Kontrollen und der Vergleich mit einfacher Zielgewichtung gehören ausdrücklich in die Abgabe.

[Session-3-Algorithmus und Befehle](improving_llm_star/experiments/research/session3/README.md), [Messwerte und Konfidenzintervalle](improving_llm_star/experiments/results/research_session3/REPORT.md), [Forschungslog](improving_llm_star/experiments/research/session3/EXPERIMENT_LOG.md), [Vergleich als PDF](improving_llm_star/experiments/results/research_session3/comparison.pdf).

## Forschungssitzung 4 – Zwischenstand (17.11.2026)

Oracle-Kontrolle auf 120 Entwicklungsanfragen: vollständige, tatsächlich gute
Koordinatenrouten haben erhebliches Potenzial. Verifizierte Ketten mit optimalen
Referenzpunkten benötigen im Pilot 0,071 ms gegenüber Witness 0,322 ms; echte
Cache-Antworten 0,330 ms. Oracle-Erzeugung ist ausdrücklich ausgeschlossen und
kein gemessener LLM-Erfolg. Eine uneingeschränkte lokale Routennachführung mit
echten Punkten verschlechtert dagegen die Pfadqualität deutlich. Qualität der
Hinweise **und** bisherige Integrationsbeschränkungen spielen eine Rolle.

Eine neue Komponenten-/Portalhierarchie mit abgesichertem Korridor-Fallback
reduziert Suchzustände, kostet bisher mehr reale Zeit. Auf 32 neuen Pilotfällen
liegen geometrischer und Oracle-Korridor fast gleichauf. Engere Punktportale
liefern bessere Schranken, rechtfertigen aber ihre Vorverarbeitung nicht.
Strategische JSON-Schemata, robuste Legacy-Verarbeitung und simulierte,
ereignisgesteuerte Provider sind implementiert; keine bezahlten API-Aufrufe.
Aktueller Versuch: günstigere notwendige Wanddurchquerungen als zulässige
Schranke, kombiniert mit unabhängig verifizierten Routenhinweisen.

Details und fortsetzbarer Stand:
[Session-4-Log](improving_llm_star/experiments/research/session4/EXPERIMENT_LOG.md),
[Checkpoint](improving_llm_star/experiments/research/session4/CHECKPOINT.md).

### Session 4: Informationsqualität und neue Architektur

Die Prüfung aller 1.800 Entwicklungsantworten (600 Anfragen, drei Prompt-Stile)
zeigt eine wichtige Selektionswirkung: Witness löst bereits 467/600 Anfragen;
bei den verbleibenden 133 ergeben nur 2/4/4 Standard-/CoT-/Repe-Antworten eine
vollständig geometrisch verifizierte Routenkette. Die Ketten sind nicht
notwendigerweise optimal. Hindernispunkte betreffen 11,10/14,35/8,73 Prozent
aller generierten Koordinaten. Rohe Geradenkollisionen sind ein Qualitätsindikator,
aber kein Beweis, dass zwischen zwei Punkten kein Umweg existiert.

Die neue zulässige Schnittschranke mit vollständigem Weighted-A*-Fallback ist
auf 132 neuen Entwicklungsanfragen (11 Familien, Größen 64/128/256) deutlich
stärker: bei Qualitätsfaktor 1,1 rund 20,75 ms gegenüber 43,26 ms Weighted A*
und 46,15 ms Witness, mit 120/120 gültigen erreichbaren Fällen und 12 korrekt
unerreichbaren Fällen. Diese Verbesserung ist bisher **klassisch-geometrisch**.
Oracle-Hinweise reduzieren weitere Expansionen, waren vor Beseitigung gemessener
quadratischer Interpretations-/Präfixarbeit im Mittel langsamer. Echte Cache-
Hinweise zeigen weiter keinen gesicherten zusätzlichen Gewinn.

Weitere Implementierungen: lazy validierter Endpoint-Roadmap, Primal-First mit
verzögerter Zertifizierung, strukturierte geordnete Hindernisumgehungen und
budgetierte lokale A*-Verfeinerung. Kein Kandidat darf allein aufgrund einer
LLM-Behauptung akzeptiert werden. Gültige Routen und zulässige Schranken bleiben
getrennt; Faktoren größer 1 garantieren höchstens begrenzte Suboptimalität.

### Session 4 – eingefrorenes Endergebnis

Die Kandidaten wurden mit Commit `0c462d6` vor Erzeugung der frischen Karten
eingefroren. Auf 44 Anfragen aus 22 neuen Karten (11 Familien, Größen 96/192,
sieben Wiederholungen) ergibt sich:

| Verfahren | Zeit ms | Eindeutige Zustände inkl. lokaler Suche | Pfadkosten/Optimum, geom. Mittel |
|---|---:|---:|---:|
| Weighted A*, Faktor 2 | 45,137 | 4614,93 | 1,00854 |
| Witness ohne LLM | 40,287 | 4486,82 | 1,00854 |
| Neue Schnittsuche ohne Hinweise | 18,152 | 1814,07 | 1,00798 |
| Schnittsuche + lokale geometrische Kontrolle | 19,631 | 1827,55 | 1,00798 |
| Gute unvollkommene **synthetische** Route + lokale Verfeinerung | 14,458 | 1402,36 | 1,01414 |
| Drei synthetische Alternativen + Verfeinerung | 15,815 | 1353,91 | 1,01177 |
| Optimale Oracle-Route | 11,981 | 1033,86 | 1,00000 |

Alle 40 erreichbaren Anfragen werden gelöst, alle vier unerreichbaren korrekt
zurückgewiesen. Der zusätzliche synthetische Hinweisgewinn gegenüber derselben
Schnittsuche beträgt im Mittel 20,35 % Zeit, bei leicht schlechteren Pfaden.
Zeitverhältnis 0,7965, exploratives 95%-Karten-Bootstrap [0,5160; 0,9304]. Gegen
dieselbe lokale Verfeinerung ohne LLM beträgt das Verhältnis 0,7365
[0,4256; 0,9029]. Zufalls-, Shuffle- und Falschantwort-Kontrollen sind im
synthetischen Zusatzversuch langsamer; das unterstützt einen Nutzen korrekter
Routeninformation, **nicht einen nachgewiesenen Nutzen eines realen LLMs**.

Die geometrische Verbesserung ist nicht universell: Baum-/verflochtene Labyrinthe
und Räume können langsamer werden. Starke Gewinne liegen bei Serpentinen,
Engpässen und dem Nachweis der Unerreichbarkeit. Der maximale beobachtete
Pfadfaktor der Schnittsuche ist höher als beim Weighted-Kontrollverfahren,
obwohl das geometrische Mittel etwas besser ist. Faktor 2 ist eine Schranke,
kein Optimalitätsversprechen. Die Drei-Routen-Variante gewinnt auf Entwicklung,
ist auf frischen Karten aber langsamer als die einzelne reparierte Route.

**Reale Cache-Validierung bleibt negativ:** 600 Beobachtungen = 200 verschiedene
Anfragen × drei Prompt-Stile auf 20 bereits bekannten Validierungskarten.
Schnittsuche ohne Hinweise 0,3215 ms, mit tatsächlichen Hinweisen 0,3185 ms;
Verhältnis 0,9904 [0,9630; 1,0168]. Falschantworten 0,3191 ms. Lokale
Verfeinerung echter Antworten 0,3398 ms, also zusätzliche Zeit. Zufall und
Falschantwort sind auch bei identischer lokaler Verfeinerung konkurrenzfähig.
Kein zusätzlicher Laufzeitnutzen echter LLM-Semantik ist damit belegt.

Die tatsächliche Flaschenhalskorrektur: keine teure Wand-/Punktpaar-Auswertung
nach schon gültigen Routen; optionale Legacy-Inferenz budgetieren; Präfixkosten
inkrementell berechnen und Teilstrecken gemeinsam speichern. Vorher-/Nachher-
Profile sind mit archiviertem Quelltext reproduzierbar. Zusätzliche Hierarchie-,
Roadmap-, Primal-First-, strukturierte Umgehungs- und dynamische Provider-
Varianten bleiben separat ausführbar. Neue strategische Prompts wurden **nicht**
mit einem Live-Modell getestet.

118 automatische Tests bestehen. Unabhängige Shapely-/Dijkstra-Prüfung: 44
Referenzdistanzen, 833.196 zulässige Zustands-Schranken, 4.480 gültige zurückgegebene
Pfade mit 949.396 Kanten. Zusätzliche Heap-/Speichermessung erfolgt getrennt von
den Laufzeitmessungen. Mittlerer gemessener Speicher sinkt auf der kleinen
Speicherstichprobe, das Maximum steigt; keine pauschale Speicherersparnis.
Original-LLM-A* bleibt unverändert; native und geometrisch angepasste Original-
Kontrollen haben auf großen Karten teilweise Zeitlimits, die als zensiert
gekennzeichnet sind. `main` wurde nicht verändert, nichts gepusht/zusammengeführt.

Empfehlung für die Abgabe: zulässige Schnittschranke und verifizierte strategische
Verfeinerung als Forschungsbeitrag präsentieren; geometrischen Gewinn,
synthetisches Informationspotenzial und echten negativen LLM-Befund trennen.
Für einen tatsächlichen LLM-Nachweis braucht es separat autorisierte neue
strategische Antworten auf neuen Karten. Schon beim synthetischen Gewinn liegt
das amortisierbare Modell-Latenzbudget nur bei etwa 6,25 ms pro angefragter Antwort;
volle API-Latenz kann den Suchgewinn deutlich übersteigen. Keine bezahlten Aufrufe.

[Abschlussbericht](improving_llm_star/experiments/results/research_session4/REPORT.md),
[exakte Befehle und Offline-Schnittstelle](improving_llm_star/experiments/research/session4/README.md),
[Tabellen und Konfidenzintervalle](improving_llm_star/experiments/results/research_session4/final_analysis/TABLES.md),
[PDF: Laufzeit/Pfadqualität](improving_llm_star/experiments/results/research_session4/final_analysis/final_fresh_comparison.pdf),
[PDF: Gewinne und Regressionen pro Kartenfamilie](improving_llm_star/experiments/results/research_session4/final_analysis/families.pdf).

## Forschungssitzung 5 – laufender Stand (18.11.2026)

Live-Aufrufe sind jetzt bis maximal 3 USD autorisiert. Nach Modellklarstellung
wird ausschließlich `gpt-4o-mini-2024-07-18` verwendet. Das Reproduktionsnotebook
nennt den Alias `gpt-4o-mini`; die alten Cache-Dateien enthalten keinen sicheren
Snapshot-Nachweis. Neue Versuche haben für Original und Verbesserungen identische
Modellparameter. API-Schlüssel werden nur im Prozess geladen, nie protokolliert.
Persistente Kostenreservierungen vor jedem Aufruf verhindern Budgetüberschreitung.

Erster neuer Pilot: 40 echte Antworten auf zehn Entwicklungskarten mit Original-,
kompaktem Koordinaten-, Endpoint-ID- und ASCII-Prompt. IDs verhindern ungültige
Koordinaten, führen aber häufig zu irrelevanten Umgehungen. Die neue Idee,
Wegpunktfortschritt pro tatsächlichem Elternpfad statt global zu führen, ist
korrekt implementiert, erhöht bisher aber die Sucharbeit. Kein positiver Befund
wird aus bloßem Verwerfen schlechter Hinweise abgeleitet. Nächste Tests: gezieltes
externes Fehlerfeedback gegen gleich teure Selbstprüfung; Auswahl eines einzelnen
bereits geometrisch erreichbaren Kandidaten. Original und alte Ergebnisse bleiben
unverändert. Details im neuen Session-5-Log und Checkpoint.
