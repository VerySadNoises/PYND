# Guide : écrire un story.yaml

## Structure globale

```yaml
characters:       # définition des personnages (une seule fois)
  <id>:
    ...

scenes:           # liste des scènes
  - id: ...
    ...
```

---

## Bloc `characters`

Définissez chaque personnage une seule fois. L'`id` sert de référence partout.

```yaml
characters:
  settler:
    name: Settler          # nom affiché dans la boîte de dialogue
    image: assets/characters/Settler.jpg   # chemin absolu ou relatif au story.yaml
    position: left         # left | center | right (position par défaut)

  captain:
    name: Capitaine
    image: assets/characters/Pilot.jpg
    position: right
```

---

## Structure d'une scène

```yaml
scenes:
  - id: intro              # identifiant unique (utilisé par goto)
    background: ...        # fond (image, GIF, vidéo) — optionnel
    music: ...             # musique de fond en boucle — optionnel
    character_dim: 120      # 0 = aucun assombrissement # 255 = personnage entièrement noir
    characters:            # personnages à afficher au chargement de la scène
      - settler
      - captain
    actions:               # liste des actions à exécuter
      - ...
```

---

## Backgrounds

### Image statique (PNG, JPG)

```yaml
background: assets/bg/space.jpg
```

### GIF animé

```yaml
background: assets/bg/stars.gif
```

### Vidéo MP4 (sans son)

```yaml
background: assets/bg/intro.mp4
```

### Vidéo MP4 avec son

```yaml
background:
  file: assets/bg/intro.mp4
  audio: true        # true = son activé | false = muet (défaut)
```

---

## Musique de fond (OGG en boucle)

La musique boucle indéfiniment. Elle peut coexister avec le son d'un MP4.

### Démarrer en début de scène

```yaml
scenes:
  - id: intro
    music: assets/audio/bgm/ambient.ogg
```

### Démarrer via une action

```yaml
actions:
  - music: assets/audio/bgm/ambient.ogg
```

### Avec volume personnalisé (0.0 – 1.0)

```yaml
  - music:
      file: assets/audio/bgm/tense.ogg
      volume: 0.6
```

### Couper la musique

```yaml
  - music: stop
```

---

## Dialogues

### Syntaxe courte (recommandée)

```yaml
actions:
  - settler: "Bienvenue à bord !"
  - captain: "Nous partons à l'aube."
```

### Syntaxe complète

```yaml
actions:
  - say:
      speaker: Settler
      text: "Bienvenue à bord !"
```

> Le `speaker` est comparé au `name` ou à l'`id` du personnage (insensible à la casse) pour activer le filtre grisé sur les autres.

---

## Choix et arbres de dialogue

### Choix simple avec goto

```yaml
  - choice:
      - text: "Explorer"
        goto: explore_scene
      - text: "Rester"
        goto: stay_scene
```

### Choix avec sous-dialogue inline (avant le goto)

```yaml
  - choice:
      - text: "Explorer"
        actions:
          - settler: "Excellent choix !"
          - captain: "Je prépare le vaisseau."
        goto: explore_scene
      - text: "Rester"
        actions:
          - captain: "Comme vous voulez."
        goto: stay_scene
```

### Choix avec variable + goto

```yaml
  - choice:
      - text: "Accepter"
        set:
          accepted: true
        goto: accepted_scene
      - text: "Refuser"
        set:
          accepted: false
        goto: refused_scene
```

---

## Variables et flags

### Définir une variable

```yaml
  - set:
      has_key: true
      reputation: 10
```

### Modifier dans un choix

```yaml
  - choice:
      - text: "Prendre la clé"
        set:
          has_key: true
        goto: next_scene
```

> Les variables sont sauvegardées automatiquement lors d'une sauvegarde rapide (**F5**) et restaurées au chargement (**F9**).

---

## Dialogues et actions conditionnels (`if`)

Exécute une branche `then` ou `else` selon la valeur d'une variable.

### Dialogue conditionnel simple

```yaml
actions:
  - if:
      condition: "explored"
      then:
        - settler: "Vous connaissez déjà cette route."
      else:
        - settler: "C'est votre premier voyage ici."
```

### Basé sur une valeur de variable

```yaml
actions:
  - if:
      condition: "mood == confident"
      then:
        - captain: "Avec cette attitude, rien ne peut nous arrêter !"
      else:
        - captain: "Ensemble, nous affronterons tout."
```

### Combiné avec `set` pour mémoriser un choix

```yaml
actions:
  - choice:
      - text: "Prendre le risque"
        set:
          mood: brave
        actions:
          - settler: "Je savais que vous seriez courageux."
      - text: "Rester prudent"
        set:
          mood: cautious
        actions:
          - settler: "La prudence est une vertu."

  - if:
      condition: "mood == brave"
      then:
        - captain: "Plein gaz !"
      else:
        - captain: "Nous avançons lentement."
```

> La branche `else` est optionnelle.

---

## Choix conditionnels

Ajoutez `condition` sur une option pour la masquer si la condition est fausse.

### Option débloquée par une variable

```yaml
  - choice:
      - text: "Utiliser la clé secrète"
        condition: "has_key"          # masquée si has_key est false / non définie
        actions:
          - settler: "La porte s'ouvre !"
        goto: secret_room
      - text: "Continuer sans la clé"
        goto: next_scene
```

### Option bloquée par une valeur

```yaml
  - choice:
      - text: "Demander pardon"
        condition: "reputation < 5"   # visible seulement si réputation faible
        actions:
          - captain: "Il était temps."
      - text: "Féliciter l'équipage"
        condition: "reputation >= 5"
        actions:
          - captain: "Merci, commandant."
```

---

## Syntaxe des conditions

Les conditions s'écrivent comme des expressions Python simplifiées.

| Type | Exemple | Description |
|---|---|---|
| Variable booléenne | `explored` | Vrai si la variable est définie et non nulle |
| Négation | `not explored` | Vrai si la variable est fausse / non définie |
| Égalité (chaîne) | `mood == confident` | Compare la valeur de `mood` au mot `confident` |
| Inégalité | `mood != angry` | |
| Numérique | `score >= 10` | Supporte `<` `<=` `>` `>=` |
| Logique | `has_key and level >= 2` | Supporte `and` / `or` |
| Avec guillemets | `mood == "confident"` | Les guillemets sont optionnels pour les chaînes |

> Les valeurs booléennes s'écrivent `true` et `false` (minuscules).

---

## Sauvegarde rapide

| Touche | Effet |
|---|---|
| **F5** | Sauvegarde la progression (scène, position, variables) dans le slot 1 |
| **F9** | Charge la dernière sauvegarde du slot 1 |

Une notification verte s'affiche brièvement en haut à droite pour confirmer l'action.
Les fichiers de sauvegarde sont au format JSON dans le dossier `saves/`.

---

## Positionner les personnages

Les personnages sont placés selon deux axes :
- **x** : centre horizontal du personnage, en fraction de la largeur d'écran (0.0 = gauche, 1.0 = droite).
- **y** : bas du personnage, en fraction de la hauteur d'écran (0.0 = haut, 1.0 = bas — défaut : 0.88).

### Positions nommées (5 emplacements prédéfinis)

| Nom | Alias | Centre x |
|---|---|---|
| `left` | `l` | 18 % |
| `center_left` | `cl` | 33 % |
| `center` | `c` | 50 % |
| `center_right` | `cr` | 67 % |
| `right` | `r` | 82 % |

```yaml
characters:
  perso_a:
    name: Alice
    image: assets/characters/alice.png
    position: left          # position par défaut du personnage
```

### Positionnement dans une scène (surcharge la définition)

```yaml
scenes:
  - id: confrontation
    characters:
      - id: alice
        position: center_left     # nomé
      - id: bob
        position: center_right
      - id: narrateur
        position:
          x: 0.50                 # centre horizontal exact
          y: 0.70                 # plus haut que les autres
```

### Position numérique libre

Utilise un dict `{x, y}` pour un placement précis :

```yaml
# 5 personnages côte à côte sans superposition
characters:
  - id: perso_a
    position: {x: 0.10}
  - id: perso_b
    position: {x: 0.30}
  - id: perso_c
    position: {x: 0.50}
  - id: perso_d
    position: {x: 0.70}
  - id: perso_e
    position: {x: 0.90}
```

### Changer la position en cours de scène (`show`)

```yaml
- show:
    id: alice
    position: center          # nomé

- show:
    id: alice
    position:
      x: 0.35                 # numérique
      y: 0.85
```

---

## Afficher / cacher des personnages

### Afficher un personnage (déjà défini dans `characters`)

```yaml
  - show:
      id: settler
      position: left     # optionnel : surcharge la position par défaut
```

### Cacher un personnage

```yaml
  - hide:
      id: settler
```

### Cacher tous les personnages

```yaml
  - hide:
```

---

## Changer de scène

```yaml
  - goto: nom_de_scene
  # ou
  - jump: nom_de_scene
```

---

## Naviguer entre plusieurs fichiers YAML

Divisez votre histoire en autant de fichiers que vous voulez. Un `goto` peut
pointer vers une scène d'un autre fichier — le moteur le charge à la volée.

### Syntaxe

```yaml
# Forme courte : fichier#scene  (recommandée)
- goto: "chapter2.yaml#foret"

# Forme dict : explicite
- goto:
    file: chapter2.yaml
    scene: foret

# Sans préciser la scène → première scène du fichier
- goto: "chapter2.yaml"

# Dans un choix
- choice:
    - text: "Continuer au chapitre 2"
      goto: "chapter2.yaml#intro"
    - text: "Rester ici"
      goto: scene_locale
```

> Les chemins sont relatifs au répertoire du fichier lancé avec la CLI
> (ex. `examples/` si vous lancez `python tools/cli.py run examples/chapter1.yaml`).

### Ce qui se passe au moment du goto

1. Le fichier YAML cible est lu et **fusionné** dans la partie en cours :
   - Ses scènes s'ajoutent au pool de scènes disponibles.
   - Ses personnages s'enregistrent (un personnage déjà connu par son `id` est ignoré — pas d'écrasement).
2. Le moteur saute dans la scène demandée exactement comme pour un `goto` normal.
3. Un fichier déjà chargé **ne sera pas relu** si un autre `goto` pointe à nouveau vers lui.

### Variables entre fichiers

Les variables (`set`) sont **globales à la partie**, pas au fichier. Tout ce
qui a été défini dans `chapter1.yaml` est directement accessible dans
`chapter2.yaml` sans aucune action supplémentaire.

```yaml
# chapter1.yaml — définit les variables
- set:
    player_name: Zara
    credits: 120

# chapter2.yaml — les utilise directement
- captain: "Bienvenue, {player_name}. Solde : {credits} crédits."
```

### Lancer un chapitre seul (sans le précédent)

Si `chapter2.yaml` est lancé directement, les variables du chapitre 1
n'existent pas. Utilisez un `if` pour initialiser des valeurs par défaut :

```yaml
# En début de première scène de chapter2.yaml
- if:
    condition: "not player_name"
    then:
      - set:
          player_name: Inconnu
          credits: 80
```

### Sauvegarde F5 / F9

La liste des fichiers extra chargés est incluse dans la sauvegarde.
Au chargement F9, ils sont rechargés automatiquement avant de restaurer
la scène — la partie reprend exactement dans le même état.

---

## Changer le fond en cours de scène

```yaml
  - background: assets/bg/autre_fond.jpg

  # ou avec vidéo + son
  - background:
      file: assets/bg/explosion.mp4
      audio: true
```

---

## Transitions entre scènes

Une transition bloque l'exécution jusqu'à sa fin, puis passe à l'action suivante.

### Syntaxe courte (durée par défaut : 500 ms)

```yaml
- transition: fade_black
```

### Avec durée personnalisée

```yaml
- transition:
    type: fade_white
    duration: 800
```

### Enchaînement typique : sortie → scène → entrée

```yaml
# Fin de la scène A
- transition:
    type: fade_black
    duration: 600
- goto: foret

# Début de la scène foret
- transition:
    type: fade_in
    duration: 400
- captain: "Nous voilà dans la forêt."
```

### Transitions disponibles

| Nom | Effet |
|---|---|
| `fade_black` | L'écran devient progressivement noir |
| `fade_white` | L'écran devient progressivement blanc |
| `fade_in` | Le noir se dissipe pour révéler la scène |
| `fade_in_white` | Le blanc se dissipe pour révéler la scène |

### Ajouter une transition personnalisée

Dans `src/vn_engine/transitions.py` :

```python
from vn_engine.transitions import BaseTransition, register

@register("flash_rouge")
class FlashRouge(BaseTransition):
    def _alpha(self): return int((1.0 - abs(self.progress * 2 - 1)) * 255)
    def _color(self): return (255, 0, 0)
```

---

## Animations de personnages

Applique un effet visuel à un personnage. Bloquant par défaut (`wait: true`).

### Shake (tremblement)

```yaml
- animate:
    character: settler
    type: shake
    duration: 400
    intensity: 15      # amplitude en pixels (défaut : 12)
```

### Scale up (gonflement pulsé)

```yaml
- animate:
    character: captain
    type: scale_up
    duration: 500
    scale: 1.2         # facteur max (défaut : 1.15)
```

### Bounce (saut)

```yaml
- animate:
    character: settler
    type: bounce
    duration: 450
    height: 40         # hauteur en pixels (défaut : 30)
```

### Translate (nudge et retour)

```yaml
- animate:
    character: captain
    type: translate
    dx: 0
    dy: -25            # décalage en pixels
    duration: 400
```

### Slide in (entrée depuis un côté)

```yaml
- animate:
    character: settler
    type: slide_in
    dx: 150            # démarre 150 px à droite de sa position
    dy: 0
    duration: 600
```

### Non-bloquant : animation en arrière-plan

```yaml
# wait: false → l'exécuteur continue sans attendre la fin
- animate:
    character: settler
    type: shake
    duration: 800
    wait: false
- settler: "Ce dialogue s'affiche pendant que le shake se joue."
```

### Animations disponibles

| Nom | Paramètres | Effet |
|---|---|---|
| `shake` | `intensity` (px, défaut 12) | Tremblement qui s'atténue |
| `scale_up` | `scale` (facteur, défaut 1.15) | Gonflement pulsé |
| `bounce` | `height` (px, défaut 30) | Saut parabolique |
| `translate` | `dx`, `dy` (px, défaut 0/-20) | Nudge et retour |
| `slide_in` | `dx`, `dy` (px, défaut 80/0) | Glissement d'entrée |

### Ajouter une animation personnalisée

Dans `src/vn_engine/animations.py` :

```python
from vn_engine.animations import BaseAnimation, register
import pygame

@register("rotation")
class Rotation(BaseAnimation):
    def get_transform(self, rect, surf):
        angle = self.progress * 15   # 15° max
        rotated = pygame.transform.rotate(surf, angle)
        return rotated, rotated.get_rect(center=rect.center)
```


    reputation: "reputation + 1"

# Multiplier, diviser
- set:
    money: "money * 2"
    money: "money // 3"   # division entière

# Dans un choix
- choice:
    - text: "Soudoyer le garde (50 crédits)"
      condition: "money >= 50"
      set:
        money: "money - 50"
      actions:
        - garde: "Passez."

    - text: "Travailler pour gagner de l'argent"
      set:
        money: "money + 20"
        reputation: "reputation + 1"
      actions:
        - patron: "Bien joué, voici votre salaire."

```
```yaml
# Variable dans une ligne de dialogue
- set:
    player_name: "Zara"
    money: 150
    reputation: 7

- merchant: "Bonjour {player_name}, vous avez {money} crédits."
- captain: "Votre réputation est de {reputation}/10."

# Fonctionne aussi dans les if et partout où il y a du texte
- if:
    condition: "money >= 100"
    then:
      - merchant: "Avec {money} crédits, vous pouvez vous offrir ce vaisseau."
    else:
      - merchant: "Il vous manque {money} crédits pour l'acheter."
```

---

## Exemple complet

```yaml
# Opération
characters:
  alex:
    name: Alex
    image: assets/characters/alex.png
    position: left
  commander:
    name: Commandant
    image: assets/characters/commander.png
    position: right

scenes:
  - id: debut
    background: assets/bg/pont.jpg
    music: assets/audio/bgm/tension.ogg
    dim_opacity: 150
    characters: [alex, commander]
    actions:
      - alex: "Commandant, nous avons un problème."
      - commander: "De quoi s'agit-il ?"
      - alex: "Le réacteur principal est hors ligne."
      - choice:
          - text: "Réparer soi-même"
            actions:
              - alex: "Je vais m'en occuper."
              - commander: "Soyez prudent."
            set:
              repaired_alone: true
            goto: reparation
          - text: "Demander de l'aide"
            actions:
              - commander: "J'envoie une équipe immédiatement."
            goto: aide

  - id: reparation
    background: assets/bg/salle_moteur.jpg
    music:
      file: assets/audio/bgm/action.ogg
      volume: 0.8
    characters: [alex]
    actions:
      - alex: "C'est plus grave que prévu..."
      - music: stop
      - alex: "Réparation terminée."

  - id: aide
    background: assets/bg/couloir.jpg
    characters: [alex, commander]
    actions:
      - commander: "L'équipe est en route."
      - alex: "Merci, Commandant."
```




---

## Contrôles en jeu

| Touche / Action | Effet |
|---|---|
| `Espace` ou clic gauche | Avancer le dialogue |
| `1` … `9` | Sélectionner un choix |
| Survol souris | Surbrillance sur les choix |
| `F5` | Sauvegarde rapide (slot 1) |
| `F9` | Chargement rapide (slot 1) |
| `Echap` | Quitter |

---

## Lancer le jeu

```powershell
.venv\Scripts\Activate.ps1
python tools/cli.py run examples/story.yaml
```

