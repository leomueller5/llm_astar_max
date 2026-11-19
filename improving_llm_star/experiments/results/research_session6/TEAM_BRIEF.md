# Erklärung für Team und Professor

Wir untersuchen eine Schwäche von LLM-A*: Ungeprüfte Modell-Wegpunkte beeinflussen
die gesamte Suchpriorität, obwohl sie räumlich falsch oder strategisch nutzlos
sein können. Unsere Erweiterung lässt Geometrie zunächst wenige sichere
Kandidaten beschreiben. GPT-4o mini wählt daraus mehrere Routenhypothesen.
Wiederholt genannte Punkte werden als optionale, vollständig geprüfte Makrokanten
in A* verwendet. Normale Suchschritte bleiben verfügbar; das Modell kann weder
Kollisionen erlauben noch die klassische Rückfallebene abschalten.

Die Suchpriorität lautet `g+w*h_cut`. Jede Makrokante entspricht einem echten
Gitterweg mit genau berechneten Kosten. Damit gilt unter den dokumentierten
Voraussetzungen die Weighted-A*-Schranke `C <= w*C*`; bei `w=1` Optimalität.
Das ist eine sichere Integration bekannter Suchideen in LLM-A*, keine behauptete
absolute Neuerfindung.

Auf 200 Aufgaben reservierter Teamkarten und 20 neuen schwierigen Karten waren
alle Hauptverfahren erfolgreich. Auf Teamkarten sinken die mittleren Heap-Pops
von 2050.9 im Original auf 1007.4, das geometrische Mittel der Pfadkosten gegenüber
dem Optimum von 1.0360 auf 1.0185. **Die starke Geometrie-Kontrolle benötigt jedoch
nur 955.1 Pops.** Die Verbesserung gegenüber dem Original darf deshalb nicht als
nachgewiesener LLM-Vorteil präsentiert werden. Neue Folgeexperimente und passende
Zufallskontrollen bestätigen diesen vorsichtigen Schluss.

Der wertvolle Projektbeitrag besteht aus der klar definierten sicheren
Integrationsmethode, nachvollziehbaren Garantien, fairen Prompt-/Suchkern-/Geometrie-
Ablationen und der belegten Grenze heutiger echter Modellanleitung. Oracle-
Experimente zeigen Potenzial besserer vollständiger Routen, aber keine Leistung,
die wir dem realen Modell zuschreiben dürfen.

157 Tests bestanden; 3,080 Wege mit 242,757 Kanten unabhängig überprüft.
Kumulierte geschätzte API-Kosten inklusive Unsicherheitsreserve: $0.4463 von $3.
Alle neuen Experimente nutzten `gpt-4o-mini-2024-07-18`.

Für die Abgabe: Original-Reproduktion, unsere Methode mit w=2 und w=1.05,
Geometrie-/Zufalls-/Oracle-Kontrollen und klare negative Ergebnisse präsentieren.
Für reine Laufzeit bleibt Cut ohne LLM die stärkste Empfehlung.
