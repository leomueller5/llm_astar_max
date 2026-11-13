# LLM-A*: bisherige Erkenntnisse und Entwicklungsstand

Stand: 11. November 2026. Arbeitsnotiz zur späteren Projektdokumentation.
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
