# LLM-A*-WW – Erklärung des Ablaufs

Dieses Dokument erklärt das Notebook [`LLM_AStar_WW.ipynb`](LLM_AStar_WW.ipynb), die überarbeitete
Fassung unseres ersten Colab-Notebooks `Improve.ipynb`. Der Algorithmus steht in
[`llm_astar_ww/llmastar/pather/llm_a_star_ww/llm_a_star_ww.py`](llm_astar_ww/llmastar/pather/llm_a_star_ww/llm_a_star_ww.py) und hat
dieselbe Ein- und Ausgabe wie `LLMAStar`; das Notebook importiert ihn und enthält das komplette
Experiment und die Auswertung. Die Abbildungen für den Report erzeugt
[`make_figures.py`](make_figures.py) aus den Ergebnisdateien des Notebooks.

---

## 1. Worum geht es?

**A\*** sucht einen kürzesten Weg auf einem Gitter. Es erweitert immer die Zelle mit dem kleinsten Wert

```
f(s) = g(s) + h(s)
```

- `g(s)`: bisherige Kosten vom Start bis zur Zelle `s`
- `h(s)`: geschätzte Restkosten, hier die Luftlinie (euklidische Distanz) von `s` zum Ziel

**LLM-A\*** (Meng et al., 2024) fragt vor der Suche ein Sprachmodell (hier GPT-4o mini) nach
**Wegpunkten** zwischen Start und Ziel. Die Suche steuert diese Wegpunkte nacheinander an. Der aktuell
angesteuerte Wegpunkt heißt `t`; sein Abstand wird zur Heuristik addiert:

```
LLM-A*:  f(s) = g(s) + h(s) + cost(t, s)
```

**Problem:** LLM-A\* vertraut jedem Wegpunkt gleich stark. Liegt ein Wegpunkt hinter einer Wand oder
ist er nur ein Umweg, wird die Suche in die falsche Richtung gezogen. Dann werden viele unnötige Zellen
erweitert, manchmal sogar mehr als bei normalem A\*.

## 2. Unsere Verbesserung: LLM-A\*-WW („Weighted Waypoints“)

Jeder Wegpunkt `t` bekommt ein **Gewicht** `alpha_t` zwischen 0 und 1:

```
LLM-A*-WW:  f(s) = g(s) + h(s) + alpha_t * cost(t, s) + (1 - alpha_t) * h(s)
```

| `alpha_t` | Bedeutung |
|---|---|
| 1 | Wegpunkt wird voll genutzt, genau wie bei LLM-A\* |
| 0 | Wegpunkt wird ignoriert: `f = g + 2h`, also gewichtetes A\* mit w = 2 (so verhält sich LLM-A\* auch ohne Wegpunkte) |

Die Gewichte werden **nur aus der Karte** berechnet; es braucht keinen zusätzlichen LLM-Aufruf.

### Gewichtung „los“ (Line-of-Sight, Standard)

1. Start, LLM-Wegpunkte und Ziel bilden eine Kette (Polylinie).
2. Vom aktuellen Punkt aus wird der **am weitesten hinten liegende** Punkt der Kette gesucht, der in
   gerader Linie erreichbar ist (die Strecke berührt keine Wand und nicht den Kartenrand).
3. Dorthin wird gesprungen; dieser Punkt bleibt als Wegpunkt erhalten (`alpha = 1`). Alle
   übersprungenen Punkte waren unnötige Umwege und fallen weg (`alpha = 0`).
4. Sobald das Ziel sichtbar ist, werden keine weiteren Wegpunkte benutzt.
5. Ist von einem Punkt aus gar kein späterer Punkt sichtbar (die LLM-Kette ist „kaputt“), wird ab dort
   ohne Wegpunkte gesucht.

### Früheres Umschalten auf den nächsten Wegpunkt

LLM-A\* wechselt zum nächsten Wegpunkt erst, wenn ein Nachbar **genau** auf dem Wegpunkt liegt. LLM-A\*-WW
wechselt schon, wenn eine erweiterte Zelle höchstens `switch_radius = 3` Zellen vom Wegpunkt entfernt
ist. Das spart Erweiterungen „rund um“ den Wegpunkt.

### Ablationsvarianten

Damit man sieht, welcher Teil wie viel bringt, gibt es drei abgeschwächte Varianten:

| Variante | Gewichtung | Umschalt-Radius |
|---|---|---|
| WW: weights only (partial) | `partial`: 0,5 · [vorheriger Punkt sichtbar] + 0,5 · [nächster Punkt sichtbar] | 0 (wie LLM-A\*) |
| WW: switching only | `none`: alle Gewichte = 1 (wie LLM-A\*) | 3 |
| WW: line-of-sight weights only | `los` | 0 (wie LLM-A\*) |

## 3. Ablauf der Suche (eine Karte)

`LLMAStarWW.searching()` (`llm_a_star_ww.py`) macht Folgendes:

1. **Karte einlesen**: Start, Ziel, Wände und Kartengröße (`_initialize_parameters`, aus LLM-A\*
   übernommen).
2. **LLM fragen**: derselbe Prompt wie bei LLM-A\* (`_initialize_llm_paths`). Die Antwort wird
   geparst; Punkte in Hindernissen oder außerhalb der Karte werden entfernt.
3. **Wegpunkte gewichten** (`_weight_waypoints`), siehe Abschnitt 2. Ergebnis: Zielliste
   `[Start, Wegpunkt 1, …, Ziel]` und eine Gewichtsliste.
4. **A\*-Schleife**:
   - Zelle mit kleinstem `f` aus der OPEN-Liste nehmen und in CLOSED eintragen.
   - Ist es das Ziel, Ende.
   - Für jeden Nachbarn: Ist der aktuelle Wegpunkt erreicht (`_target_reached`), zum nächsten wechseln
     und alle `f`-Werte in OPEN neu berechnen, weil sich die Heuristik geändert hat.
   - Kosten zum Nachbarn berechnen (unendlich, falls eine Wand im Weg ist) und den Nachbarn bei
     Verbesserung in OPEN eintragen.
5. **Ergebnis**: Anzahl erweiterter Zellen (`operation`), Größe der Kostentabelle (`storage`),
   Pfadlänge (`length`) und die tatsächlich benutzten Wegpunkte (`llm_output`).

## 4. Ablauf des Experiments

Das Notebook führt diese Schritte aus (Sections 2–5):

1. **Daten laden** (`load_samples`): 100 Karten der Größe 50 × 30 mit je 10 Start-Ziel-Paaren, also
   **1000 Samples**.
2. **LLM-Antworten holen**: Standardmäßig werden die gespeicherten GPT-4o-mini-Antworten aus unserer
   Table-1-Reproduktion benutzt (`table1_reproduction/antworten_<prompt>.json`). So braucht man keinen
   API-Key, und die Zahlen sind exakt reproduzierbar. Mit `QUERY_LLM = True` wird GPT-4o mini neu gefragt.
3. **Alle Verfahren laufen lassen** (`run_sample`; in Colab parallel, unter Windows nacheinander):
   - A\* (Referenz = 100 %)
   - Dynamic WA\* (Gewicht startet bei 2 und sinkt pro Erweiterung um den Faktor 0,99)
   - Statisches WA\* mit w = 2 (= LLM-A\* mit leerer LLM-Antwort)
   - LLM-A\* und LLM-A\*-WW, jeweils mit den Prompts Few-Shot, CoT und RePE
   - optional (`RUN_ABLATION = True`) die drei Ablationsvarianten

   A\*, LLM-A\* und LLM-A\*-WW kommen aus dem eigenen Paket `improving_llm_star/llm_astar_ww/llmastar/`:
   eine unveränderte Kopie des Originalcodes aus `llm-astar/`, ergänzt um LLM-A\*-WW, eine
   `chatgpt.py` für GPT-4o mini und einen optionalen LLaMA-Import.

   LLM-A\* und LLM-A\*-WW bekommen **dieselbe** LLM-Antwort; Unterschiede kommen also nur aus der Suche.
4. **Statistik** (Section 5): Für jedes Sample wird das Verhältnis Methode / A\* gebildet.
   - OR, SR, RL und Zeit: **geometrisches Mittel** der Verhältnisse mit 95-%-Konfidenzintervall
     (t-Intervall auf den Logarithmen). Das geometrische Mittel ist richtig für Verhältnisse:
     „halb so viel“ (0,5) und „doppelt so viel“ (2,0) heben sich auf.
   - VPR und „Worse than A\*“: Anteil in % mit **Wilson-Intervall** (funktioniert auch nahe 0 % oder
     100 %).
5. **Ausgabe** im Ordner `improving_llm_star/results/`:
   - `per_sample_results_ww.json`: Rohdaten pro Sample
   - `ww_with_statistics.csv`: Mittelwert, KI, Standardabweichung und n pro Metrik
   - `ww_with_ci.csv`: kompakte Tabelle „Mittelwert [KI unten, KI oben]“
   - `example_searches.json`: Suchdaten (erweiterte Zellen, Pfad, Wegpunkte) der zwei Beispielkarten
     aus Section 6, Grundlage für Abbildung 1
6. **Abbildungen**: `python improving_llm_star/make_figures.py` liest nur diese Dateien und schreibt
   nach `improving_llm_star/figures/`:
   - `fig1_example_paths.png`: Beispielkarten A\* / LLM-A\* / LLM-A\*-WW
   - `fig4_per_sample_or.png`: Operation Ratio pro Sample, LLM-A\* gegen LLM-A\*-WW
   - `fig5_pseudocode.png`: Pseudocode von LLM-A\*-WW und der Line-of-Sight-Prüfung
   - `fig6_failure_cases.png`: Fehlschläge von LLM-A\*-WW (schlechtester Fall bei untersuchten Zellen
     und bei der Weglänge), Suchdaten aus `failure_searches.json` (Notebook, Section 7)

### Metriken

| Kürzel | Bedeutung | besser ist |
|---|---|---|
| OR | Operation Ratio: erweiterte Zellen im Verhältnis zu A\* | kleiner |
| SR | Storage Ratio: gespeicherte Zellen im Verhältnis zu A\* | kleiner |
| RL | Relative Pfadlänge im Verhältnis zu A\* (A\* ist optimal, also ≥ 100 %) | näher an 100 |
| VPR | Valid Path Ratio: Anteil gefundener gültiger Pfade | größer |
| Worse than A\* | Anteil der Samples mit mehr Erweiterungen als A\* | kleiner |
| Time | Laufzeit im Verhältnis zu A\* (Wanduhrzeit, nicht deterministisch) | kleiner |

## 5. Ergebnisse (alle 1000 Samples, aus dem Notebook)

Werte in %, A\* = 100, Mittelwert [95-%-KI]:

| Methode | Prompt | OR | SR | RL | Worse than A\* |
|---|---|---|---|---|---|
| Dynamic WA\* | – | 60.90 [57.73, 64.25] | 78.52 [76.77, 80.32] | 100.24 | 60.40 |
| Static WA\* (w=2) | – | 34.32 [32.74, 35.97] | 56.23 [55.08, 57.41] | 102.02 | 5.30 |
| LLM-A\* | Few-Shot | 46.09 [43.71, 48.59] | 65.40 [63.68, 67.17] | 102.74 | 17.30 |
| **LLM-A\*-WW** | Few-Shot | **34.75 [33.17, 36.41]** | **56.59 [55.43, 57.77]** | 102.13 | 5.60 |
| LLM-A\* | CoT | 47.61 [45.17, 50.19] | 66.24 [64.47, 68.06] | 102.61 | 17.20 |
| **LLM-A\*-WW** | CoT | **35.24 [33.64, 36.92]** | **56.96 [55.79, 58.15]** | 102.26 | 6.20 |
| LLM-A\* | RePE | 50.13 [47.52, 52.89] | 68.31 [66.44, 70.22] | 102.30 | 19.20 |
| **LLM-A\*-WW** | RePE | **35.08 [33.45, 36.79]** | **56.86 [55.66, 58.08]** | 102.08 | 5.80 |

Alle Verfahren finden in 100 % der Fälle einen gültigen Pfad.

**Ablation (OR, Few-Shot):** nur Gewichte (partial) 40.39, nur Umschalten 39.59, nur Line-of-Sight
35.15, vollständiges LLM-A\*-WW 34.75. Den größten Teil des Gewinns bringt also die
Line-of-Sight-Gewichtung.

**Interpretation:**
- LLM-A\*-WW erweitert bei allen drei Prompts rund **25–30 % weniger Zellen** als LLM-A\* (z.B. 34.75 statt
  46.09 % bei Few-Shot), und die Konfidenzintervalle überlappen nicht.
- Der Anteil der Fälle, in denen die Suche schlechter als A\* ist, sinkt von 17–19 % auf etwa 6 %.
- Die Pfade sind sogar minimal kürzer als bei LLM-A\* (RL 102.1–102.3 statt 102.3–102.7).
- LLM-A\*-WW liegt fast gleichauf mit statischem WA\* (w = 2). Das heißt: Die LLM-Wegpunkte schaden
  jetzt nicht mehr, auf diesem Datensatz bringen sie gegenüber WA\* aber auch kaum zusätzlichen Gewinn.

## 6. Was hat sich gegenüber `Improve.ipynb` geändert?

| `Improve.ipynb` (erste Fassung) | `LLM_AStar_WW.ipynb` |
|---|---|
| Läuft nur in Colab mit Google Drive | Läuft lokal und in Colab (Drive oder Klonen mit dem Colab-Secret `GITHUB_TOKEN`) |
| Schreibt `llm_a_star_ww.py`, `__init__.py` und `chatgpt.py` per `%%writefile` in eine Kopie des `llmastar`-Pakets und startet ein Skript | Die Klasse liegt fest im eigenen Paket (`llm_astar_ww/llmastar/pather/llm_a_star_ww/`); das Notebook importiert sie. Der Originalcode in `llm-astar/` wird nicht verändert |
| Patch von `chatgpt.py` auf openai ≥ 1.0 | Ebenfalls fest im eigenen Paket (`llm_astar_ww/llmastar/model/chatgpt.py`), damit LLM-A\*-WW auf neuen Karten GPT-4o mini direkt fragen kann |
| Gewichte im Attribut `self.alpha` | Eigenes Attribut `self.waypoint_weights`, damit es nicht mit `alpha` in veränderten LLM-A\*-Versionen kollidiert |
| Absturz, falls kein Pfad gefunden wird; der Fehler wurde abgefangen und still ohne Wegpunkte neu gerechnet | Pfadlänge = unendlich (zählt dann als ungültiger Pfad) |
| Bei `switch_radius = 0` wurde zusätzlich umgeschaltet, wenn die erweiterte Zelle selbst auf dem Wegpunkt lag | Korrigiert: Radius 0 bedeutet jetzt exakt die Umschaltregel von LLM-A\* |
| Testlauf mit 50 Samples als eigene Zelle | Einstellung `LIMIT` in der ersten Zelle |

**Geprüft:**
- Mit allen Gewichten = 1 und Radius 0 liefert LLM-A\*-WW in allen 1002 getesteten Läufen (jedes dritte
  Sample, alle drei Prompts) exakt dasselbe Ergebnis wie das originale LLM-A\*.
- Ohne Wegpunkte liefert LLM-A\*-WW exakt dasselbe wie statisches WA\* (w = 2).
- Jeder behaltene Wegpunkt ist vom vorherigen aus in gerader Linie erreichbar, und die Reihenfolge der
  LLM-Wegpunkte bleibt erhalten.

Durch die Korrektur der Umschaltregel ändern sich nur die beiden Ablationsvarianten mit Radius 0
minimal (z.B. „partial weights only“, Few-Shot: OR 40.24 → 40.39). Alle anderen Werte (OR, SR, RL, VPR,
„Worse than A\*“), insbesondere die von LLM-A\*-WW, sind exakt gleich wie in `Improve.ipynb`.

## 7. Ausführen

**Colab:** Notebook hochladen und alle Zellen ausführen. Liegt das Projekt nicht in Google Drive unter
`MyDrive/llm_astar_max`, wird das Repository mit dem Colab-Secret `GITHUB_TOKEN` geklont.

**Lokal:** Python ≥ 3.10 mit `numpy`, `pandas`, `scipy`, `matplotlib`, `shapely`, `openai`; das Notebook
im Projektordner öffnen und alle Zellen ausführen.

```bash
pip install numpy "pandas==2.2.3" scipy matplotlib shapely openai jupyter
```

Einstellungen in der ersten Zelle:

| Variable | Bedeutung |
|---|---|
| `RUN_ABLATION` | Ablationsvarianten mitrechnen (dauert etwa doppelt so lange) |
| `LIMIT` | z.B. `50` für einen schnellen Test, `None` = alle 1000 Samples |
| `QUERY_LLM` | `True`: GPT-4o mini neu fragen (braucht `OPENAI_API_KEY`) |

Dauer für alle 1000 Samples mit Ablation: lokal etwa 30 Minuten, in Colab (2 Prozesse) etwa 1 Stunde.
Danach die Abbildungen erzeugen (im Hauptordner des Repositorys):

```bash
python improving_llm_star/make_figures.py
```
