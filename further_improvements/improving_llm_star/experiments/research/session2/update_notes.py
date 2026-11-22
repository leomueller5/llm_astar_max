"""Append measured Session-2 findings; requires completed reports/verification."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4]
BASE=ROOT/'improving_llm_star/experiments/results/research_session2'

def main():
 data=json.loads((BASE/'report_statistics.json').read_text());fresh=data['fresh_core']['vs_matched_wa2'];cached=data['opened_cached_confirmation']['vs_matched_wa2'];llm=data['opened_cached_confirmation']['vs_witness_only']
 lines=['','---','','## Zweite autonome Forschungsphase am 16.11.2026','',
  'Der Forschungsbranch bleibt `research/waypoint-guidance`; kein Push/Merge, keine bezahlten Modellaufrufe. Alte Baselines und historische Resultate bleiben unverändert. Die Auswahl wurde in Commit `87c3310` vor Erzeugung der frischen Testkarten festgeschrieben.',
  '', '### Tatsächlicher Laufzeitengpass und neue Verfahren','',
  'Das Ausgangsprofil auf 120 Entwicklungsfällen zeigt: Nachbarerzeugung und Kollisionsprüfung dominieren. Die untere Schranke kostet etwa 0,1 % der instrumentierten Gesamtzeit; Heap-Primitive zusammen unter 1 %. Kumulative Profilerzeiten überlappen und werden nicht addiert.',
  '', 'Implementiert: Zeilen-/Spaltenindex für ganzzahlige Wände, direkte Einzelkantenabfragen, exakte Prüfung kurzer Gitterrouten als zwei gerade Teilstücke, erreichbarkeitsbasierter DAG, kollineare Waypoint-Kompression und schlankere robuste Fallback-Suche. Nichtganzzahlige Geometrie und degenerierte Wände behalten die tatsächlichen Einzelschritt-Kollisionsregeln. Alle Indizes/Caches werden pro Anfrage frisch bezahlt.',
  '', '**Entscheidender neuer Ansatz:** Aus der zulässigen Einzelwand-Schranke lassen sich Wandend-Kandidaten ableiten. Ein vollständig geprüfter Weg durch einen solchen Punkt wird nur übernommen, wenn seine Kosten die zulässige untere Schranke erreichen. Sonst läuft Weighted A* mit Gewicht 2. Optional folgt davor ein exakter Waypoint-DAG oder eine separate Variante mit verifizierter Waypoint-Route als oberer Schranke.',
  '', '**Der stärkste Laufzeitgewinn ist geometrisch, nicht LLM-spezifisch.** `WitnessFirstLLMAStar(use_waypoints=False)` benötigt keinen Modellaufruf. Die Waypoint-Ergänzung muss gegen genau diese Variante verglichen werden, nicht nur gegen das Original.',
  '', '### Festgelegte Abschlussauswertung','',
  'Frisch: 80 neue Karten, 640 Fälle, zehn Familien einschließlich großer Zufalls-/Labyrinthkarten, elf Wiederholungen je Verfahren. 576 Fälle lösbar, 64 absichtlich unerreichbar. Hilfreiche Hinweise sind optimale Referenzpfad-Ecken ausschließlich als synthetische Fixtures; keine echten neuen LLM-Ausgaben. Seed660000 ist von Entwicklung440000 und Validierung550000 sowie allen alten Seeds getrennt.',
  '', 'Zusätzlich: 600 bereits in Sitzung 1 geöffnete Modellcache-Beobachtungen auf 20 Karten, drei Promptvarianten, sieben Wiederholungen. Diese Wiederholung heißt ausdrücklich **geöffnete Bestätigung**, nicht neuer unabhängiger Holdout. Wiederholungen werden pro Fall per Median reduziert; Konfidenzintervalle resampeln ganze Karten.',
  '', '| Variante | Frische Fälle: mittlere Fallmedian-ms | Geöffnete Modellcaches: mittlere Fallmedian-ms | Cache: unterschiedliche Expansionen | Cache: Kosten / Optimum (geom.) |',
  '|---|---:|---:|---:|---:|']
 for m in ['original_indexed','old_cf','scheduled_wa2','witness_only','witness_cf','witness_chain','witness_frontier']:
  f=fresh[m];c=cached[m];lines.append(f"| {m} | {f['mean_case_median_ms']:.4f} | {c['mean_case_median_ms']:.4f} | {c['unique']:.2f} | {c['gm_cost_ratio']:.5f} |")
 lines+=['', '`original_indexed` bewahrt die originale Suchlogik, verwendet jedoch dieselbe neue Geometrie. Native Originalmessungen stehen separat im Report; diese Kontrollen nicht vermischen. Alle Vorverarbeitungskosten sind in den End-to-End-Kernzeiten enthalten.','']
 for label,stats in [('frischen Fixtures',fresh),('geöffneten Modellcaches',cached)]:
  s=stats['witness_only'];ci=s['ratio_of_mean_times_ci95']
  lines.append(f"Witness-only gegenüber identisch optimierter WA2-Kontrolle auf {label}: Zeitverhältnis {s['ratio_of_mean_times']:.4f}, 95%-Karten-Bootstrap [{ci[0]:.4f}; {ci[1]:.4f}].")
 s=llm['witness_cf'];ci=s['ratio_of_mean_times_ci95'];lines+=['', f"Zusätzliche exakte LLM-Stufe auf Modellcaches: Zeitverhältnis zu Witness-only {s['ratio_of_mean_times']:.4f} [{ci[0]:.4f}; {ci[1]:.4f}], {s['llm_accepted']} tatsächlich übernommene Waypoint-Routen. Die stärkeren geometrischen Gewinne dürfen ihr nicht zugeschrieben werden.",
  '', 'Die Raw-Chain/Frontier-Variante kann sehr gute synthetische Routen nutzen. Das belegt bedingtes Potenzial bei hochwertigen Hinweisen, nicht dieselbe Wirksamkeit realer Modellantworten. Frontier-Routen sind nur Faktor-2-beschränkt und können gegenüber der Kontrolle länger sein. Exakte Zertifikate bleiben optimal; das gesamte Verfahren ist wegen des Weighted-A*-Fallbacks nicht generell optimal.',
  '', '### Korrektheit, Speicher und Messgrenzen','',
  '82 automatisierte Tests bestanden nach den neuen Geometrie-, Bound-, Schnittstellen- und Budgettests. Eine zusätzliche unabhängige Shapely-Prüfung aller ausgewählten Abschlussvarianten sowie Kosten-/Zertifikatprüfung gegen A* ist im Verification-Artefakt gespeichert. Originaloperationen und -kosten werden erneut gegen die vorhandenen Table-1-Daten geprüft.',
  '', 'Python-tracemalloc auf 24 festen Entwicklungsfällen: mittlerer Peak ungefähr 225 kB alte Zertifikatsvariante, 138 kB Witness-only, 188 kB schlanke WA2-Kontrolle. Importierte Bibliotheken und native GEOS-Allokationen fehlen; keine vollständige RAM-/RSS-Aussage. Historische Storage-Zähler erfassen nicht alle Hilfsstrukturen.',
  '', 'Die erste native Testmessung wurde wegen einer falschen Einordnung gepufferter Statusausgabe unterbrochen; daraus werden keine Zahlen berichtet. Der vollständige Kernvergleich blieb erhalten. Wiederholung mit Journal pro Durchlauf und **einheitlichem Zwei-Sekunden-Limit für alle nativen Verfahren**: zensierte Originalzeiten werden nur als untere Laufzeitschranken ausgewiesen. Keine exakten vollständigen Originalmittelwerte daraus ableiten. Verfahrensparameter wurden dabei nicht geändert.',
  '', 'Negative Ergebnisse: einfache Stagnations-/Dichtegates und spätere Zertifizierung brachten keinen überzeugenden Zusatzgewinn; enge Waypoint-Korridore erhöhten Aufwand und teilweise Pfadlängen. Unzertifizierte Incumbents können helfen, kosten auf realen Caches aber häufig mehr als sie sparen. Frühere Source-Hash-/JSON-Probleme sind mit separaten Hinweisen archiviert; finale Läufe sichern Source-Snapshots zu Beginn.',
  '', '### Empfehlung für die Abgabe','',
  'Die Arbeit als evidenzgeleitete Untersuchung selektiver Guidance darstellen: ursprüngliche Adaptive-Alpha-Hypothese, gemessene kurze Waypoint-Lebensdauer, verifizierte Routen, dann schnelle geometrische Zertifikate mit sauberer LLM-Ablation. Nicht behaupten, dass der große Laufzeitgewinn von LLM-Intelligenz stammt. Für den stärksten Laufzeitstand Witness-only; die exakte LLM-Ergänzung und Raw-Chain-Incumbents als unabhängig bewertete Optionen zeigen. Weitere Modelle/Antworten und schwierigere Karten sind nötig, bevor ein echter LLM-Laufzeitvorteil behauptet werden kann.',
  '', '[Algorithmus, Pseudocode und exakte Befehle](improving_llm_star/experiments/research/session2/README.md), [Tabellen und Konfidenzintervalle](improving_llm_star/experiments/results/research_session2/REPORT.md), [Forschungslog](improving_llm_star/experiments/research/session2/EXPERIMENT_LOG.md), [Grafiken als PDF](improving_llm_star/experiments/results/research_session2/runtime.pdf).']
 target=ROOT/'PROJEKT_ERKENNTNISSE.md';text=target.read_text()
 if '## Zweite autonome Forschungsphase am 16.11.2026' in text:raise ValueError('Do not append findings twice')
 target.write_text(text.replace('Stand: 11. November 2026.','Stand: 16. November 2026 (historische Abschnitte zeitlich eingeordnet).')+'\n'.join(lines)+'\n')
 print('Project notes updated from measured report statistics.')
if __name__=='__main__':main()
