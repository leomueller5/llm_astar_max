# Offline-Messung des Waypoint-Fortschritts

Sechs feste Testfälle, jeweils mit alpha = 0, 0.5 und 1. Keine echten LLM-Aufrufe; keine adaptive Gewichtsänderung.

| Fall | alpha | Operationen | Storage | Pfadlänge | Max. Stillstand |
|---|---:|---:|---:|---:|---:|
| open_direct | 0 | 207 | 246 | 26.9706 | 27 |
| open_direct | 0.5 | 23 | 96 | 26.9706 | 0 |
| open_direct | 1 | 23 | 96 | 26.9706 | 0 |
| open_detour | 0 | 23 | 72 | 22.0000 | 22 |
| open_detour | 0.5 | 299 | 307 | 22.0000 | 22 |
| open_detour | 1 | 243 | 256 | 22.8284 | 25 |
| wall_bypass | 0 | 179 | 234 | 24.1421 | 19 |
| wall_bypass | 0.5 | 58 | 119 | 24.1421 | 17 |
| wall_bypass | 1 | 21 | 85 | 24.1421 | 0 |
| wall_wrong_direction | 0 | 175 | 234 | 24.1421 | 25 |
| wall_wrong_direction | 0.5 | 74 | 127 | 24.1421 | 43 |
| wall_wrong_direction | 1 | 66 | 134 | 26.9706 | 39 |
| wall_unreachable_endpoint | 0 | 175 | 234 | 24.1421 | 43 |
| wall_unreachable_endpoint | 0.5 | 74 | 127 | 24.1421 | 47 |
| wall_unreachable_endpoint | 1 | 31 | 99 | 24.1421 | 8 |
| public_prompt_example | 0 | 473 | 450 | 42.7279 | 35 |
| public_prompt_example | 0.5 | 402 | 388 | 42.7279 | 30 |
| public_prompt_example | 1 | 281 | 298 | 42.7279 | 31 |

## Prüfungen

- Alle 18 Vergleiche mit/ohne Messung haben identische Ergebnisse, Pfade, Vorgänger und Heap-Pop-Reihenfolgen.
- alpha=1 stimmt in allen sechs Fällen mit dem Original überein.
- Alle ausgegebenen Pfade wurden auf Endpunkte, legale Schritte und Kollisionen geprüft.
- Zähler-Resets bei Fortschritt, Waypoint-Wechsel und erneutem Suchlauf wurden geprüft.

## Einordnung

Der Stillstandszähler erfasst aufeinanderfolgende Heap-Pops ohne eine neue beste euklidische Distanz zum aktiven Waypoint. Duplikate und der Ziel-Pop werden wie beim bisherigen operation-Zähler mitgezählt. Der erste Pop eines neuen Targets legt den Distanz-Ausgangswert fest.

Ein hilfreicher Waypoint spart im offenen Direktfall Operationen; ein unnötiger Umweg-Waypoint erhöht sie im offenen Umwegfall. Ein sinnvoller Waypoint im öffentlichen Prompt-Beispiel hat bei alpha=1 ebenfalls 26 Pops Stillstand vor dem nächsten Fortschritt. Der Umwegfall hat 25. Ein einzelner Grenzwert trennt diese Beispiele daher nicht zuverlässig.

Im Endpoint-Fall schaltet die Original-Logik bereits beim Erzeugen des Nachbarn um, obwohl der Target-Punkt auf einem Hindernis liegt. Diese unveränderte Logik kann problematische Waypoints vor der Messung verbergen.

Dies ist ein isolierter Funktionstest mit handgeschriebenen Waypoints und einem Beispiel aus dem Repository-Prompt, kein GPT-4o-mini-Benchmark. Der Test umgeht optionale Imports; eine geschlossene Segmentprüfung auf ganzzahligen Koordinaten ersetzt Shapely. Keine Laufzeit-, Kosten- oder Generalisierungsverbesserung wird daraus abgeleitet.
