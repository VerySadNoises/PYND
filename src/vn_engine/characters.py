from __future__ import annotations

import pygame
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from vn_engine.animations import BaseAnimation

# Character position presets: (center_x_fraction, bottom_y_fraction)
_NAMED_POSITIONS: dict[str, tuple[float, float]] = {
    "left":         (0.18, 0.88),
    "l":            (0.18, 0.88),
    "center_left":  (0.33, 0.88),
    "cl":           (0.33, 0.88),
    "center":       (0.50, 0.88),
    "c":            (0.50, 0.88),
    "center_right": (0.67, 0.88),
    "cr":           (0.67, 0.88),
    "right":        (0.82, 0.88),
    "r":            (0.82, 0.88),
}
_DEFAULT_POS: tuple[float, float] = (0.50, 0.88)


def _parse_position(raw: str | dict | None) -> tuple[float, float]:
    """
    Retourne (x_frac, y_frac) :
      - x_frac : centre horizontal du personnage / largeur d'écran
      - y_frac : bas du personnage / hauteur d'écran

    Formats acceptés :
      str  -> "left" | "center_left" | "center" | "center_right" | "right"
      dict -> {x: 0.3}  |  {x: 0.3, y: 0.9}
    """
    if isinstance(raw, dict):
        return (
            float(raw.get("x", _DEFAULT_POS[0])),
            float(raw.get("y", _DEFAULT_POS[1])),
        )
    if isinstance(raw, str):
        return _NAMED_POSITIONS.get(raw.strip().lower(), _DEFAULT_POS)
    return _DEFAULT_POS


class Character:
    def __init__(
        self,
        char_id: str,
        name: str,
        image_path: str | None = None,
        position: str | dict = "center",
        base_dir: str | Path | None = None,
    ) -> None:
        self.id: str = char_id
        self.name: str = name
        self.image_path: str | None = image_path
        self.default_position: str | dict = position
        self.base_dir: Path = Path(base_dir) if base_dir else Path(".")

        self._surf_original: pygame.Surface | None = None

        # Image normale, utilisée quand le personnage parle.
        self.surf: pygame.Surface | None = None

        # Cache des versions assombries (clé = valeur de dim_amount).
        self._dimmed_surfaces: dict[int, pygame.Surface] = {}

        self.rect: pygame.Rect | None = None
        self.visible: bool = False
        self._animation: BaseAnimation | None = None

    # ------------------------------------------------------------------
    # Chargement et redimensionnement
    # ------------------------------------------------------------------

    def load(self, screen_size: tuple[int, int]) -> None:
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

    def _scale(self, screen_size: tuple[int, int]) -> None:
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

    def place(self, screen_size: tuple[int, int], position: str | dict | None = None) -> None:
        if self.surf is None:
            return

        screen_width, screen_height = screen_size
        image_width, image_height = self.surf.get_size()

        raw = position if position is not None else (self.default_position or "center")
        x_frac, y_frac = _parse_position(raw)

        # Centre x du personnage, puis bord gauche pour le rect
        cx = int(screen_width * x_frac)
        x = cx - image_width // 2

        # Bord bas du personnage, puis bord haut pour le rect
        by = int(screen_height * y_frac)
        y = by - image_height

        # Garder dans les limites de l'écran
        x = max(0, min(screen_width  - image_width,  x))
        y = max(0, min(screen_height - image_height, y))

        self.rect = pygame.Rect(x, y, image_width, image_height)
        self.visible = True

    def hide(self) -> None:
        self.visible = False

    # ------------------------------------------------------------------
    # Assombrissement
    # ------------------------------------------------------------------

    def _get_dimmed_surface(self, dim_amount: int) -> pygame.Surface | None:
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

    def render(self, screen: pygame.Surface, is_speaking: bool, dim_amount: int = 120) -> None:
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
            if self._animation is not None:
                surface_to_draw, draw_rect = self._animation.get_transform(
                    self.rect, surface_to_draw
                )
            else:
                draw_rect = self.rect
            screen.blit(surface_to_draw, draw_rect)


class CharacterRegistry:
    def __init__(self, data: dict | None, base_dir: str | Path) -> None:
        self._chars: dict[str, Character] = {}

        for character_id, config in (data or {}).items():
            self._chars[character_id] = Character(
                char_id=character_id,
                name=config.get("name", character_id),
                image_path=config.get("image"),
                position=config.get("position", "center"),
                base_dir=base_dir,
            )

    def get(self, char_id: str) -> Character | None:
        return self._chars.get(char_id)

    def all(self) -> list[Character]:
        return list(self._chars.values())

    def show(self, char_id: str, screen_size: tuple[int, int], position: str | dict | None = None) -> None:
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

    def hide(self, char_id: str) -> None:
        character = self._chars.get(char_id)

        if character is not None:
            character.hide()

    def hide_all(self) -> None:
        for character in self._chars.values():
            character.hide()

    def register(self, char_id: str, config: dict, base_dir: str | Path) -> None:
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

    def resolve_speaker(self, speaker_name: str) -> str | None:
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