# Session 7 — Kurzfassung für Team und Professor

**Ergebnis:** Eine zusätzliche Beschleunigung durch echte LLM-Information ist
gegenüber starken geometrischen Kontrollen weiterhin nicht belastbar nachgewiesen.
Wir haben dafür mehrere neue Mechanismen implementiert, echte Modellantworten
untersucht und die Grenzen der bisherigen Hypothesen genauer eingegrenzt.

## Was wurde entwickelt?

LLM-RH* lässt GPT-4o mini für 16 Kartenregionen zusätzliche Restkosten und
Konfidenzen schätzen. Diese Information bleibt während der Suche erhalten.
Die Suchpriorität lautet:

```text
f(n) = g(n) + h(n) + min(0.05*h(n), a*confidence(region)*delta(region))
a = 0.22640953779865894, ausschließlich auf Entwicklungskarten kalibriert
```

Alle normalen Übergänge bleiben verfügbar. Verbesserte Wege werden wieder
geöffnet; veraltete Queue-Einträge werden übersprungen. Die zusätzliche
Heuristik verschwindet am Ziel. Unter den dokumentierten Voraussetzungen ist
der zurückgegebene Weg höchstens 5% länger als optimal. Das ist eine sichere
Integration unzuverlässiger Modellschätzungen, keine Behauptung ihrer Zulässigkeit.

## Was zeigen die neuen Karten?

100 Aufgaben, 60 neue Kartengeometrien, zehn Kartenfamilien. Die Konfiguration
wurde vor der Testkartenerzeugung eingefroren. Angaben: lokale Planungszeit mit
gespeicherter Guidance und jeweils frischer Vorverarbeitung, ohne API-Latenz.

| Verfahren | Hauptsatz: 80 Aufgaben | Große Karten: 20 Aufgaben |
|---|---:|---:|
| Identischer Kern, konstantes Gewicht 1,05 | 27,18 ms | 124,68 ms |
| LLM-RH*, Bild, Zero-shot | 34,53 ms | 191,42 ms |
| LLM-RH*, feste Few-shot-Beispiele | 30,76 ms | 168,67 ms |
| Geometrisches VM*, Gewicht 1,05 | 23,63 ms | 112,52 ms |

Die Konfidenzintervalle über Karten sind breit. Die beobachteten Mittelwerte
belegen keinen allgemeinen LLM-Gewinn. Neue Varianten lösen alle Aufgaben;
der eingefrorene Originalcode überschreitet bei 26/100 die Fünf-Sekunden-Grenze.
Seine zensierten Werte dürfen nicht wie vollständige Laufzeiten behandelt werden.

## Warum hilft das Modell nicht zuverlässig?

- Vorhergesagte Zusatzkosten korrelieren kaum mit tatsächlichen Zusatzkosten.
  Einfache geometrische Untergrenzen sind numerisch genauer.
- Grobe Regionen verlieren wichtige Unterschiede innerhalb eines Labyrinths.
- Die enge Sicherheitsschranke begrenzt sogar die Nutzbarkeit perfekter Guidance.
- Few-shot kopiert überall Konfidenz 1, verschlechtert den Kostenfehler und kann
  durch stärkere Gewichtung schneller werden. Das beweist kein besseres Verständnis.
- Focal/Discrepancy senkt teilweise Expansionen, verursacht aber mehr Queue-Arbeit.
- Bei VM* verschwindet ein kleiner Zeitvorteil gegenüber sämtlichen Endpunkten
  gegenüber stärkeren Kontrollen wie Abstinenz und zufällig vertauschten Modellzielen.

## Wissenschaftlich vertretbarer Beitrag

Wir erweitern LLM-A* um persistente räumliche Guidance, eine explizite
Pfadkostenschranke und eine kontrollierte Evaluation. Die Ergebnisse unterscheiden
zwischen Modellinformation, bloßer Heuristikgewichtung, Geometrie und Suchkern.
Das ist eine Integration und empirische Untersuchung bekannter Suchideen;
wir behaupten keine absolute Neuheit von Focal Search, Pathmax oder Weighted A*.

Eine zusätzliche Herleitung erklärt die Originalformel als gewichtete Suche:
Bei konstantem globalem alpha ergibt sich unter den genannten Bedingungen eine
Schranke von 1+alpha. Das Original mit alpha=1 ist trotzdem nicht optimal.
Beliebige ortsabhängige Modellschätzungen benötigen eigene Schutzmaßnahmen.

## Empfehlung für die Abgabe

LLM-A-VM* bleibt der praktische, reproduzierbare Kandidat. Der starke geometrische
Anteil und die Kontrolle ohne LLM müssen offen gezeigt werden. LLM-RH* ergänzt
die Arbeit um eine klare Forschungsfrage und ein belastbar dokumentiertes
negatives Ergebnis. Keine Verbesserungen der KI zuschreiben, die geometrische
Suche oder unterschiedliche Gewichtung bereits erklären.

Für den verbleibenden Tag: Methode/Theorie, unabhängige Reproduktion/Statistik
und Bericht/Präsentation auf drei Personen verteilen. Der vollständige Forschungs-
bericht ist Hintergrundmaterial; er ersetzt nicht die verlangte kurze ACL-Abgabe.

## Verifikation und Kosten

209 Tests bestanden. 4.217 gespeicherte Konfigurationspfade unabhängig geprüft;
diese Zahl ist keine Anzahl unabhängiger Karten. Exakte Modellversion:
`gpt-4o-mini-2024-07-18`. Kumulativ geschätzt 1,47217 USD abgerechnet plus
0,19775 USD vorsorglich reserviert, insgesamt 1,66991 USD unter der Grenze von 3 USD.
Keine offenen Anfragen und keine weiteren bezahlten Abschlusskontrollen.

Der GitHub-Account ist bestätigt, die konfigurierte Commit-E-Mail jedoch nicht
als verifiziert zugeordnet. Deshalb kein automatischer Push und keine Änderung
der Identitäts- oder Authentifizierungseinstellungen.

Bericht: REPORT.md / REPORT.pdf. Theorie: ../../research/session7/THEORY.md.
Exakte Offline-Befehle: ../../research/session7/README.md. Originalcode, vorherige
Forschung, negative Versuche und Rohdaten bleiben erhalten.
