# Personnalisation de l'interface (UI)

Toutes les constantes et méthodes de rendu se trouvent dans
`src/vn_engine/core.py`, classe `VNApp`.

---

## 1. Couleurs et constantes de base

Les constantes de classe en tête de `VNApp` contrôlent l'apparence globale.

```python
# src/vn_engine/core.py  —  class VNApp:

_DLGBOX_H     = 200                  # hauteur de la boîte de dialogue (px)
_DLGBOX_COLOR = (10, 10, 20, 210)    # fond RGBA (R, G, B, opacité 0-255)
_SPEAKER_COLOR = (255, 220, 100)     # couleur du nom du personnage
_TEXT_COLOR    = (230, 230, 230)     # couleur du texte de dialogue
_CHOICE_COLOR  = (200, 200, 100)     # couleur des lignes de choix
_CHOICE_HOVER  = (255, 255, 160)     # couleur d'un choix survolé
```

Modifier ces valeurs change immédiatement l'apparence sans toucher
aux méthodes de rendu.

---

## 2. Typographie — polices et tailles

Les trois polices sont créées dans `__init__` :

```python
# src/vn_engine/core.py  —  VNApp.__init__()

self.font_text    = pygame.font.Font(None, 30)   # texte principal
self.font_speaker = pygame.font.Font(None, 36)   # nom du personnage
self.font_choice  = pygame.font.Font(None, 28)   # choix + notifications
```

`pygame.font.Font(None, taille)` utilise la police système par défaut.
Pour utiliser un fichier `.ttf` :

```python
self.font_text    = pygame.font.Font("assets/fonts/mafonte.ttf", 30)
self.font_speaker = pygame.font.Font("assets/fonts/mafonte.ttf", 36)
self.font_choice  = pygame.font.Font("assets/fonts/mafonte.ttf", 28)
```

> Placer les fichiers `.ttf` dans `assets/fonts/` et ajuster les chemins.

---

## 3. Boîte de dialogue

La méthode `_render_dialogue_box()` dessine :
1. Un rectangle semi-transparent en bas de l'écran
2. Le nom du personnage
3. Le texte enroulé automatiquement

### Hauteur et position

```python
_DLGBOX_H = 200   # hauteur en pixels
# La boîte est toujours collée en bas : box_y = self.H - _DLGBOX_H
```

Pour la déplacer vers le haut, remplacer dans `_render_dialogue_box()` :

```python
# Avant
box_y = self.H - self._DLGBOX_H

# Après — décalage de 40 px vers le haut
box_y = self.H - self._DLGBOX_H - 40
```

### Couleur et opacité du fond

```python
_DLGBOX_COLOR = (10, 10, 20, 210)
#                R   G   B   A (0 = transparent, 255 = opaque)
```

### Marges internes

Dans `_render_dialogue_box()` :

```python
padding = 30   # marge gauche et droite en pixels
y = box_y + 14 # décalage vertical depuis le haut de la boîte
```

### Espacement entre le nom et le texte

```python
y += speaker_surface.get_height() + 8   # 8 = espace en pixels
```

### Ajouter une bordure à la boîte

Après le `blit` de `box_surface` dans `_render_dialogue_box()` :

```python
pygame.draw.rect(
    self.screen,
    (100, 100, 160),          # couleur de la bordure
    pygame.Rect(0, box_y, self.W, self._DLGBOX_H),
    width=2,                  # épaisseur en pixels
)
```

---

## 4. Choix (menu de sélection)

La méthode `_render_choices()` dessine la liste des choix.

### Position verticale de départ

```python
current_y = int(self.H * 0.42)   # 42 % de la hauteur de l'écran
```

Modifier `0.42` pour monter ou descendre le bloc de choix.

### Marge horizontale

```python
padding_x = 60   # pixels depuis le bord gauche
```

### Espacement entre les lignes

```python
current_y += line_height + 14   # 14 = espace inter-choix en pixels
```

### Format du texte d'un choix

Par défaut chaque ligne affiche `"N.  Texte du choix"`. Pour changer :

```python
# Avant
text = f"{index + 1}.  {choice.get('text', '')}"

# Sans numéro, avec flèche
text = f"▶  {choice.get('text', '')}"

# Avec crochets
text = f"[ {choice.get('text', '')} ]"
```

### Couleur de surbrillance (fond au survol)

```python
highlight.fill((255, 255, 100, 40))
#               R    G    B   A  — 40 = très léger
```

Augmenter l'alpha (ex. `80`) pour un fond plus visible.

### Ajouter une bordure par choix

Dans la boucle `for index, choice in enumerate(self.choices)`, après le `blit` :

```python
pygame.draw.rect(self.screen, (80, 80, 120), hit_rect, width=1)
```

---

## 5. HUD — afficher des variables dans des boîtes de texte

Pour ajouter un élément d'interface persistant (compteur, statut…),
créer une méthode `_render_hud()` et l'appeler depuis `_render()`.

### Exemple : afficher une variable en coin supérieur gauche

```python
# Dans _render() juste avant pygame.display.flip() :
self._render_hud()
```

```python
def _render_hud(self):
    credits = self.variables.get("credits", 0)
    text = f"Crédits : {credits}"
    surface = self.font_choice.render(text, True, (220, 220, 100))
    # Fond semi-transparent
    bg = pygame.Surface(
        (surface.get_width() + 16, surface.get_height() + 10),
        pygame.SRCALPHA,
    )
    bg.fill((0, 0, 0, 160))
    self.screen.blit(bg, (12, 12))
    self.screen.blit(surface, (20, 17))
```

### Afficher plusieurs variables en colonne

```python
def _render_hud(self):
    items = [
        ("Crédits",    self.variables.get("credits", 0)),
        ("Réputation", self.variables.get("reputation", 0)),
        ("Oxygène",    self.variables.get("oxygene", 100)),
    ]
    x, y = 16, 16
    for label, value in items:
        line = f"{label} : {value}"
        surf = self.font_choice.render(line, True, (200, 220, 255))
        bg = pygame.Surface(
            (surf.get_width() + 12, surf.get_height() + 8),
            pygame.SRCALPHA,
        )
        bg.fill((0, 0, 0, 150))
        self.screen.blit(bg, (x - 6, y - 4))
        self.screen.blit(surf, (x, y))
        y += surf.get_height() + 12
```

---

## 6. Barres de progression

Une barre de progression pour une variable numérique (ex. `oxygene` 0-100) :

```python
def _render_bar(self, label, value, max_value, x, y, width=200, height=16):
    # Fond de la barre
    pygame.draw.rect(self.screen, (40, 40, 40), (x, y, width, height))

    # Remplissage proportionnel
    fill_w = int(width * max(0, min(value, max_value)) / max_value)
    color = (
        (80, 200, 80)   if value > max_value * 0.5 else
        (220, 180, 0)   if value > max_value * 0.25 else
        (200, 60, 60)
    )
    if fill_w > 0:
        pygame.draw.rect(self.screen, color, (x, y, fill_w, height))

    # Bordure
    pygame.draw.rect(self.screen, (120, 120, 120), (x, y, width, height), width=1)

    # Étiquette
    surf = self.font_choice.render(f"{label} : {value}/{max_value}", True, (220, 220, 220))
    self.screen.blit(surf, (x, y - surf.get_height() - 4))
```

**Appel dans `_render_hud()` ou directement dans `_render()` :**

```python
self._render_bar(
    "Oxygène",
    self.variables.get("oxygene", 100),
    max_value=100,
    x=20, y=60,
    width=180,
)
```

La couleur change automatiquement :
- vert > 50 %
- orange entre 25 % et 50 %
- rouge < 25 %

---

## 7. Résumé des points de modification

| Quoi | Où | Paramètre / méthode |
|---|---|---|
| Hauteur boîte de dialogue | `VNApp` (constante) | `_DLGBOX_H` |
| Couleur fond boîte | `VNApp` (constante) | `_DLGBOX_COLOR` |
| Couleur nom personnage | `VNApp` (constante) | `_SPEAKER_COLOR` |
| Couleur texte dialogue | `VNApp` (constante) | `_TEXT_COLOR` |
| Couleur texte choix | `VNApp` (constante) | `_CHOICE_COLOR` |
| Couleur survol choix | `VNApp` (constante) | `_CHOICE_HOVER` |
| Taille texte dialogue | `__init__` | `self.font_text` |
| Taille nom personnage | `__init__` | `self.font_speaker` |
| Taille texte choix | `__init__` | `self.font_choice` |
| Police (fichier .ttf) | `__init__` | `pygame.font.Font("chemin.ttf", taille)` |
| Position verticale choix | `_render_choices()` | `current_y = int(self.H * 0.42)` |
| Marge horizontale choix | `_render_choices()` | `padding_x = 60` |
| Format du texte de choix | `_render_choices()` | ligne `text = f"..."` |
| Fond survol choix | `_render_choices()` | `highlight.fill(...)` |
| Variables en HUD | nouvelle méthode | `_render_hud()` |
| Barres de progression | nouvelle méthode | `_render_bar(...)` |
