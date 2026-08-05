# D.S.E

Ce dépôt contient un prototype minimal d'un moteur de Visual Novel en Python (MVP).

update github
git add .
git commit -m "Votre message"
git push

to launch from v env :
python tools/cli.py run examples/story.yaml


Stack principal:
- Runtime: `pygame`
- Scripting: `YAML` → compilé en JSON/AST
- Outils GUI (éditeur optionnel): `PySide6`

Quickstart (Windows PowerShell):

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python tools/cli.py run examples/demo_part1.yaml
```

Quickstart (macOS / Linux):

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python tools/cli.py run examples/demo_part1.yaml
```

Fichiers importants créés:
- `src/vn_engine/` : package du moteur
- `tools/cli.py` : CLI pour lancer/valider/build
- `examples/story.yaml` : script d'exemple
- `requirements.txt` : dépendances

