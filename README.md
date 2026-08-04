# D.S.E

Ce dépôt contient un prototype minimal d'un moteur de Visual Novel en Python (MVP).

Stack principal:
- Runtime: `pygame`
- Scripting: `YAML` → compilé en JSON/AST
- Outils GUI (éditeur optionnel): `PySide6`

Quickstart (Windows PowerShell):

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python tools/cli.py run examples/story.yaml
```

Quickstart (macOS / Linux):

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python tools/cli.py run examples/story.yaml
```

Fichiers importants créés:
- `src/vn_engine/` : package du moteur
- `tools/cli.py` : CLI pour lancer/valider/build
- `examples/story.yaml` : script d'exemple
- `requirements.txt` : dépendances

Prochaine étape: j'ai créé le scaffold initial. Voulez-vous que je complète le parseur, ajoute la validation et étende le runtime (choix, sauvegardes) maintenant ?
