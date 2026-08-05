# Guide des effets sonores (SFX)

Les SFX sont des sons courts joués par-dessus la musique de fond — explosions, claquements de porte, alarmes, etc.  
Le moteur alloue jusqu'à **15 canaux audio simultanés** (canal 0 réservé à la musique).

---

## Formats supportés

| Format | Notes |
|--------|-------|
| `.ogg` | Recommandé — open-source, léger, bien supporté |
| `.wav` | Sans compression, qualité maximale, fichiers lourds |
| `.mp3` | Supporté mais peut causer des problèmes de latence |

---

## Utilisation dans un script YAML

### Forme courte

La façon la plus simple : juste le chemin vers le fichier.

```yaml
- sfx: assets/audio/sfx/explosion.ogg
```

### Forme complète (avec options)

```yaml
- sfx:
    file: assets/audio/sfx/alarm.ogg
    volume: 0.7      # 0.0 (silence) → 1.0 (plein volume) — défaut : 1.0
    loop: true       # joue en boucle jusqu'à stop_sfx — défaut : false
```

### Arrêter tous les SFX

```yaml
- stop_sfx:
```

> `stop_sfx` n'arrête **pas** la musique de fond. Pour la musique : `- music: stop`

---

## Exemples concrets

### Son ponctuel (impact, coup)

```yaml
- say:
    char: capitaine
    text: "Feu !"
- sfx: assets/audio/sfx/canon.wav
```

### Alarme en boucle, puis arrêt

```yaml
- sfx:
    file: assets/audio/sfx/alarm.ogg
    volume: 0.6
    loop: true
- say:
    char: ingenieur
    text: "L'alarme retentit dans tout le vaisseau..."
- say:
    char: capitaine
    text: "Coupez ça !"
- stop_sfx:
```

### SFX conditionnel selon une variable

```yaml
- if: alerte == true
  then:
    - sfx: assets/audio/sfx/alarm.ogg
  else:
    - sfx: assets/audio/sfx/calm_ambience.ogg
```

### Plusieurs SFX à la suite (canaux différents)

Le moteur cherche automatiquement un canal libre — deux SFX peuvent se superposer.

```yaml
- sfx: assets/audio/sfx/door_open.wav
- sfx: assets/audio/sfx/footsteps.wav
```

---

## Créer ses propres SFX

### Outils gratuits recommandés

| Outil | Usage |
|-------|-------|
| [Audacity](https://www.audacityteam.org/) | Enregistrement et édition audio |
| [BFXR / SFXR](https://www.bfxr.net/) | Génération de sons 8-bit/rétro en ligne |
| [Freesound.org](https://freesound.org/) | Banque de sons libres (CC) |
| [ZapSplat](https://www.zapsplat.com/) | Sons professionnels gratuits |

### Conseils de production

- **Format cible** : OGG Vorbis, qualité Q5 (~160 kbps) — bon équilibre taille/qualité
- **Durée** : idéalement < 5 secondes pour les sons ponctuels
- **Normalisation** : viser -3 dB de crête pour éviter la saturation
- **Mono ou stéréo** : les deux fonctionnent ; mono pour l'ambiance, stéréo pour les effets cinématiques

### Convertir en OGG avec ffmpeg

```bash
ffmpeg -i input.mp3 -c:a libvorbis -q:a 5 output.ogg
```

---

## Organisation recommandée des fichiers

```
assets/
  audio/
    music/          ← musiques de fond (longues)
    sfx/
      ui/           ← sons d'interface (clic, transition)
      ambiance/     ← boucles d'ambiance
      impacts/      ← explosions, chocs
      voix/         ← voix, souffles, cris
```

---

## Comportement technique

- Le moteur utilise `pygame.mixer` avec **16 canaux** (canal 0 = musique).
- `_play_sfx` appelle `pygame.mixer.find_channel(True)` : si tous les canaux sont occupés, il vole le canal le plus ancien.
- Un SFX non bouclé se termine seul — pas besoin de `stop_sfx`.
- `stop_sfx` arrête **tous** les canaux SFX (1–15) immédiatement.
- Si le fichier est introuvable, une erreur est affichée dans la console sans planter le jeu.
