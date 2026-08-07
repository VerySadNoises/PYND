"""
Système de transitions modulaire.

Pour ajouter une nouvelle transition :
    from vn_engine.transitions import BaseTransition, register

    @register("ma_transition")
    class MaTransition(BaseTransition):
        def _alpha(self) -> int: return int(self.progress * 255)
        def _color(self) -> tuple[int, int, int]: return (255, 0, 0)   # rouge
"""

from __future__ import annotations

import pygame

_REGISTRY: dict[str, type[BaseTransition]] = {}


def register(name: str):
    """Décorateur pour enregistrer une transition dans le registre global."""
    def decorator(cls):
        _REGISTRY[name] = cls
        return cls
    return decorator


def create(name: str, duration_ms: int = 500) -> BaseTransition | None:
    """Instancie une transition par son nom; retourne None si inconnue."""
    cls = _REGISTRY.get(name)
    if cls is None:
        return None
    return cls(duration_ms)


class BaseTransition:
    """
    Transition de base basée sur un overlay coloré semi-transparent.

    Chaque frame, `tick()` avance le temps puis `render()` dessine un
    rectangle couvrant tout l'écran avec une couleur et une opacité
    calculées par les sous-classes via `_color()` et `_alpha()`.

    Sous-classes : implémenter _alpha() et _color().
    """

    def __init__(self, duration_ms: int = 500):
        self.duration_ms = max(1, int(duration_ms))  # durée totale en ms
        self._elapsed = 0     # temps écoulé depuis le début
        self.done = False     # passe à True quand la transition est terminée

    def tick(self, delta_ms: int) -> None:
        """Avance la transition de `delta_ms` millisecondes et marque done si terminée."""
        self._elapsed = min(self._elapsed + delta_ms, self.duration_ms)
        if self._elapsed >= self.duration_ms:
            self.done = True

    @property
    def progress(self) -> float:
        """0.0 (début) → 1.0 (fin)."""
        return self._elapsed / self.duration_ms

    def render(self, screen: pygame.Surface) -> None:
        """Dessine l'overlay de transition par-dessus l'image déjà rendue."""
        alpha = self._alpha()
        if alpha <= 0:
            return
        overlay = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        overlay.fill((*self._color(), alpha))
        screen.blit(overlay, (0, 0))

    def _alpha(self) -> int:
        """Opacité de l'overlay (0 = transparent, 255 = opaque)."""
        raise NotImplementedError

    def _color(self) -> tuple[int, int, int]:
        """Couleur RGB de l'overlay."""
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Transitions intégrées
# ---------------------------------------------------------------------------

@register("fade_black")
class FadeBlack(BaseTransition):
    """Fondu au noir : l'écran devient progressivement noir."""
    def _alpha(self) -> int: return int(self.progress * 255)
    def _color(self) -> tuple[int, int, int]: return (0, 0, 0)


@register("fade_white")
class FadeWhite(BaseTransition):
    """Fondu au blanc : l'écran devient progressivement blanc."""
    def _alpha(self) -> int: return int(self.progress * 255)
    def _color(self) -> tuple[int, int, int]: return (255, 255, 255)


@register("fade_in")
class FadeIn(BaseTransition):
    """Apparition depuis le noir : le noir se dissipe pour révéler la scène."""
    def _alpha(self) -> int: return int((1.0 - self.progress) * 255)
    def _color(self) -> tuple[int, int, int]: return (0, 0, 0)


@register("fade_in_white")
class FadeInWhite(BaseTransition):
    """Apparition depuis le blanc : le blanc se dissipe pour révéler la scène."""
    def _alpha(self) -> int: return int((1.0 - self.progress) * 255)
    def _color(self) -> tuple[int, int, int]: return (255, 255, 255)


# ---------------------------------------------------------------------------
# Transitions de balayage (wipe)
# ---------------------------------------------------------------------------

class _WipeBase(BaseTransition):
    """
    Base pour les transitions par bande noire.

    `render()` dessine directement un rectangle plein (pas d'overlay SRCALPHA)
    pour éviter tout artefact de transparence.
    Sous-classes : implémenter `_rect()` qui retourne (x, y, largeur, hauteur).
    """
    def _alpha(self) -> int: return 255
    def _color(self) -> tuple[int, int, int]: return (0, 0, 0)

    def render(self, screen: pygame.Surface) -> None:
        rect = self._rect(*screen.get_size(), self.progress)
        if rect and rect[2] > 0 and rect[3] > 0:
            pygame.draw.rect(screen, (0, 0, 0), rect)

    def _rect(self, w: int, h: int, p: float) -> tuple[int, int, int, int] | None:
        """Retourne le rectangle (x, y, largeur, hauteur) de la bande à dessiner."""
        raise NotImplementedError


@register("wipe_right")
class WipeRight(_WipeBase):
    """Bande noire glissant de gauche à droite."""
    def _rect(self, w: int, h: int, p: float) -> tuple[int, int, int, int]: return (0, 0, int(w * p), h)


@register("wipe_left")
class WipeLeft(_WipeBase):
    """Bande noire glissant de droite à gauche."""
    def _rect(self, w: int, h: int, p: float) -> tuple[int, int, int, int]:
        bw = int(w * p)
        return (w - bw, 0, bw, h)


@register("wipe_down")
class WipeDown(_WipeBase):
    """Bande noire glissant du haut vers le bas."""
    def _rect(self, w: int, h: int, p: float) -> tuple[int, int, int, int]: return (0, 0, w, int(h * p))


@register("wipe_up")
class WipeUp(_WipeBase):
    """Bande noire glissant du bas vers le haut."""
    def _rect(self, w: int, h: int, p: float) -> tuple[int, int, int, int]:
        bh = int(h * p)
        return (0, h - bh, w, bh)


# ---------------------------------------------------------------------------
# Transitions en iris (masque circulaire)
# ---------------------------------------------------------------------------

class _IrisBase(BaseTransition):
    """
    Base pour les transitions en iris (masque circulaire).

    Technique : on remplit un overlay noir opaque couvrant tout l'écran,
    puis on y découpe un cercle transparent centré à l'écran.
    La scène en dessous est visible uniquement à l'intérieur du cercle.
    Sous-classes : implémenter `_radius()` pour contrôler la taille du cercle.
    """
    def _alpha(self) -> int: return 255
    def _color(self) -> tuple[int, int, int]: return (0, 0, 0)

    def render(self, screen: pygame.Surface) -> None:
        w, h = screen.get_size()
        # Rayon maximal = demi-diagonale de l'écran, pour couvrir les coins
        max_r = int((w * w + h * h) ** 0.5 / 2) + 2
        r = self._radius(max_r, self.progress)
        overlay = pygame.Surface((w, h), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 255))
        if r > 0:
            # pygame 2.x : draw.circle respecte l'alpha sur SRCALPHA
            pygame.draw.circle(overlay, (0, 0, 0, 0), (w // 2, h // 2), r)
        screen.blit(overlay, (0, 0))

    def _radius(self, max_r: int, p: float) -> int:
        """Retourne le rayon du cercle transparent (0 = tout noir, max_r = tout visible)."""
        raise NotImplementedError


@register("iris_close")
class IrisClose(_IrisBase):
    """Fermeture en iris : le cercle visible rétrécit jusqu'au noir total."""
    def _radius(self, max_r: int, p: float) -> int: return int(max_r * (1.0 - p))


@register("iris_open")
class IrisOpen(_IrisBase):
    """Ouverture en iris : le cercle grandit depuis le centre pour révéler la scène."""
    def _radius(self, max_r: int, p: float) -> int: return int(max_r * p)


# ---------------------------------------------------------------------------
# Autres transitions
# ---------------------------------------------------------------------------

@register("fade_red")
class FadeRed(BaseTransition):
    """Fondu vers un voile rouge — danger, mort, tension extrême."""
    def _alpha(self) -> int: return int(self.progress * 220)
    def _color(self) -> tuple[int, int, int]: return (180, 0, 0)


@register("dissolve")
class Dissolve(BaseTransition):
    """
    Dissolution en blocs aléatoires — classique des visual novels.

    L'écran est divisé en une grille de blocs de taille `block_size`.
    Au premier appel, l'ordre d'apparition des blocs est mélangé aléatoirement.
    À chaque frame, les blocs correspondant à la progression actuelle
    sont peints en noir, sans recalculer les blocs déjà traités.
    """

    def __init__(self, duration_ms: int = 600, block_size: int = 16):
        super().__init__(duration_ms)
        self.block_size = max(4, int(block_size))  # taille d'un bloc en pixels
        self._overlay: "pygame.Surface | None" = None  # surface cumulative des blocs noirs
        self._order: "list[int] | None" = None         # ordre aléatoire des indices de blocs
        self._last_n: int = 0                          # nombre de blocs déjà peints

    # _alpha/_color non utilisés : render() est entièrement surchargé
    def _alpha(self) -> int: return 0
    def _color(self) -> tuple[int, int, int]: return (0, 0, 0)

    def render(self, screen: pygame.Surface) -> None:
        import random as _random
        w, h = screen.get_size()
        bs = self.block_size
        # Nombre de blocs nécessaires pour couvrir l'écran en largeur et en hauteur
        cols = (w + bs - 1) // bs
        rows = (h + bs - 1) // bs
        total = cols * rows

        if self._overlay is None:
            # Initialisation au premier appel : crée l'overlay vide et mélange l'ordre
            self._overlay = pygame.Surface((w, h), pygame.SRCALPHA)
            self._overlay.fill((0, 0, 0, 0))
            self._order = list(range(total))
            _random.shuffle(self._order)

        # Peint uniquement les blocs nouveaux depuis la dernière frame
        n = int(total * self.progress)
        assert self._order is not None
        for idx in self._order[self._last_n:n]:
            c, r = idx % cols, idx // cols
            pygame.draw.rect(self._overlay, (0, 0, 0, 255), (c * bs, r * bs, bs, bs))
        self._last_n = n

        screen.blit(self._overlay, (0, 0))
