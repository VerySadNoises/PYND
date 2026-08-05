import pygame
from pathlib import Path


class Character:
    def __init__(
        self,
        char_id,
        name,
        image_path=None,
        position="center",
        base_dir=None,
    ):
        self.id = char_id
        self.name = name
        self.image_path = image_path
        self.default_position = position
        self.base_dir = Path(base_dir) if base_dir else Path(".")

        self._surf_original = None

        # Image normale, utilisée quand le personnage parle.
        self.surf = None

        # Cache des versions assombries.
        # La clé correspond à la valeur de dim_amount.
        self._dimmed_surfaces = {}

        self.rect = None
        self.visible = False

    # ------------------------------------------------------------------
    # Chargement et redimensionnement
    # ------------------------------------------------------------------

    def load(self, screen_size):
        if not self.image_path:
            return

        path = Path(self.image_path)

        if not path.is_absolute():
            path = (self.base_dir / path).resolve()

        try:
            raw = pygame.image.load(str(path))

            # convert_alpha() permet de conserver la transparence du PNG.
            if raw.get_flags() & pygame.SRCALPHA or raw.get_alpha() is not None:
                self._surf_original = raw.convert_alpha()
            else:
                # Même sans canal alpha d'origine, on convertit vers une
                # surface avec alpha afin d'avoir un comportement uniforme.
                self._surf_original = raw.convert_alpha()

            self._scale(screen_size)

        except Exception as error:
            print(f"[Character] Cannot load '{self.id}': {error}")
            self._surf_original = None
            self.surf = None
            self.rect = None

    def _scale(self, screen_size):
        if self._surf_original is None:
            return

        _, screen_height = screen_size
        max_height = int(screen_height * 0.65)

        width, height = self._surf_original.get_size()

        if height <= 0:
            return

        if height > max_height:
            scale = max_height / height
            width = max(1, int(width * scale))
            height = max(1, int(height * scale))

        self.surf = pygame.transform.smoothscale(
            self._surf_original,
            (width, height),
        ).convert_alpha()

        # Après un redimensionnement, les anciennes surfaces assombries
        # ne correspondent plus à la bonne taille.
        self._dimmed_surfaces.clear()

    # ------------------------------------------------------------------
    # Position et visibilité
    # ------------------------------------------------------------------

    def place(self, screen_size, position=None):
        if self.surf is None:
            return

        screen_width, screen_height = screen_size
        selected_position = (
            position or self.default_position or "center"
        ).lower()

        margin_x = int(screen_width * 0.05)
        bottom_offset = int(screen_height * 0.12)

        image_width, image_height = self.surf.get_size()

        if selected_position in ("left", "l"):
            x = margin_x

        elif selected_position in ("right", "r"):
            x = screen_width - image_width - margin_x

        else:
            x = (screen_width - image_width) // 2

        y = screen_height - image_height - bottom_offset

        self.rect = pygame.Rect(
            x,
            y,
            image_width,
            image_height,
        )

        self.visible = True

    def hide(self):
        self.visible = False

    # ------------------------------------------------------------------
    # Assombrissement
    # ------------------------------------------------------------------

    def _get_dimmed_surface(self, dim_amount):
        """
        Retourne une copie assombrie de l'image du personnage.

        dim_amount représente la quantité d'assombrissement :

            0   = image normale
            255 = image complètement noire

        Seules les composantes RGB sont modifiées.
        Le canal alpha du PNG est conservé tel quel.

        Les pixels totalement transparents restent donc transparents,
        et aucun rectangle de fond n'est créé.
        """
        if self.surf is None:
            return None

        dim_amount = max(0, min(255, int(dim_amount)))

        if dim_amount == 0:
            return self.surf

        cached_surface = self._dimmed_surfaces.get(dim_amount)

        if cached_surface is not None:
            return cached_surface

        dimmed = self.surf.copy().convert_alpha()

        # Valeur multiplicative :
        # 255 conserve entièrement la couleur.
        # 0 transforme les couleurs en noir.
        brightness = 255 - dim_amount

        # BLEND_RGBA_MULT multiplie les composantes RGB.
        # L'alpha est multiplié par 255, donc il reste inchangé.
        dimmed.fill(
            (brightness, brightness, brightness, 255),
            special_flags=pygame.BLEND_RGBA_MULT,
        )

        self._dimmed_surfaces[dim_amount] = dimmed
        return dimmed

    # ------------------------------------------------------------------
    # Affichage
    # ------------------------------------------------------------------

    def render(self, screen, is_speaking, dim_amount=120):
        """
        Affiche le personnage.

        Le personnage qui parle est affiché normalement.
        Les autres personnages sont assombris directement sur leurs pixels,
        sans modifier leur transparence et sans dessiner de rectangle.
        """
        if not self.visible:
            return

        if self.surf is None or self.rect is None:
            return

        if is_speaking or dim_amount <= 0:
            surface_to_draw = self.surf
        else:
            surface_to_draw = self._get_dimmed_surface(dim_amount)

        if surface_to_draw is not None:
            screen.blit(surface_to_draw, self.rect)


class CharacterRegistry:
    def __init__(self, data, base_dir):
        self._chars = {}

        for character_id, config in (data or {}).items():
            self._chars[character_id] = Character(
                char_id=character_id,
                name=config.get("name", character_id),
                image_path=config.get("image"),
                position=config.get("position", "center"),
                base_dir=base_dir,
            )

    def get(self, char_id):
        return self._chars.get(char_id)

    def all(self):
        return list(self._chars.values())

    def show(self, char_id, screen_size, position=None):
        character = self._chars.get(char_id)

        if character is None:
            print(f"[Registry] Unknown character id: '{char_id}'")
            return

        if character.surf is None:
            character.load(screen_size)

        character.place(
            screen_size,
            position=position,
        )

    def hide(self, char_id):
        character = self._chars.get(char_id)

        if character is not None:
            character.hide()

    def hide_all(self):
        for character in self._chars.values():
            character.hide()

    def register(self, char_id, config, base_dir):
        """Ajoute un personnage depuis un autre fichier YAML (ignoré si l'id existe déjà)."""
        if char_id in self._chars:
            return
        self._chars[char_id] = Character(
            char_id=char_id,
            name=config.get("name", char_id),
            image_path=config.get("image"),
            position=config.get("position", "center"),
            base_dir=base_dir,
        )

    def resolve_speaker(self, speaker_name):
        """
        Retourne l'identifiant correspondant à l'identifiant ou au nom
        affiché d'un personnage, sans tenir compte de la casse.
        """
        if not speaker_name:
            return None

        normalized_name = str(speaker_name).strip().lower()

        for character_id, character in self._chars.items():
            if character_id.lower() == normalized_name:
                return character_id

            if character.name.lower() == normalized_name:
                return character_id

        return None