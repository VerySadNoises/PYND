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

## Changer le fond en cours de scène

```yaml
  - background: assets/bg/autre_fond.jpg

  # ou avec vidéo + son
  - background:
      file: assets/bg/explosion.mp4
      audio: true
```

---

## Exemple complet

```yaml
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
