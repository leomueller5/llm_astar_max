# Python-Umgebung und Offline-Tests

Alle Befehle werden im Workspace-Root `llm_astar_max` ausgeführt.

Die lokale `.venv` verwendet Python 3.12.13. Die Verbesserungskopie ist darin
editierbar installiert: Änderungen an `improving_llm_star/llmastar` werden beim
nächsten Prozessstart direkt geladen. Die Originalkopie wurde nicht verändert.

## Aktivieren und prüfen

```sh
source .venv/bin/activate
python -m pip check
python -m pytest improving_llm_star/tests -q
```

Die Tests verwenden echte Paketimporte, Shapely, Matplotlib, NumPy, PyTorch und
Transformers. Eine kleine Tensoroperation und das Speichern einer tatsächlichen
Pfadgrafik werden ebenfalls geprüft. Modellantworten sind fest vorgegeben;
Netzwerkverbindungen werden während der Tests blockiert. Es sind keine API-Keys
oder heruntergeladenen Modellgewichte nötig.

## Fortschrittsmessung mit echten Bibliotheken

```sh
source .venv/bin/activate
MPLBACKEND=Agg MPLCONFIGDIR="$PWD/.venv/matplotlib" HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 python -B improving_llm_star/experiments/measure_waypoint_progress.py --backend installed
```

Ausgaben: `improving_llm_star/experiments/results/waypoint_progress_installed/`.
Die festen Waypoints und die fehlenden API-Aufrufe machen dies zu einem
Offline-Funktionstest, nicht zu einer GPT-4o-mini-Evaluation.

## Reproduzieren der Umgebung

`requirements-lock-macos-arm64-py312.txt` hält die lokal installierten Versionen
fest. Die Datei ist auf Python 3.12 unter macOS ARM64 zugeschnitten. Für andere
Betriebssysteme müssen kompatible Wheels und Abhängigkeiten neu geprüft werden.

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install --no-cache-dir -r improving_llm_star/requirements-lock-macos-arm64-py312.txt
.venv/bin/python -m pip install --no-cache-dir --no-deps -e ./improving_llm_star
```

Für eine neue, nicht vollständig gepinnte Entwicklungsumgebung genügt alternativ:

```sh
.venv/bin/python -m pip install --no-cache-dir -e ./improving_llm_star pytest
```

## Grenzen der Einrichtung

- Der vorhandene OpenAI-Adapter verwendet weiterhin das vom Repository
  vorgeschriebene SDK `openai==0.27.2` und die ursprünglichen GPT-3.5-Modellnamen.
  Für neue GPT-4o-mini-Waypoints muss die Modell-/Endpoint-Anbindung noch
  angepasst oder die bereits vorhandene Anbindung des Teams übernommen werden.
- PyTorch und Transformers sind installiert. Der bestehende Llama3-Konstruktor
  verwendet jedoch fest `cuda:3`; das ist keine auf diesem Mac lauffähige
  Gerätekonfiguration. Modellgewichte wurden nicht heruntergeladen.
- Die automatische Anpassung von `alpha` ist noch nicht implementiert.
