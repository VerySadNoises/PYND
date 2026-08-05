"""
Système d'animations de personnages modulaire.

Pour ajouter une animation personnalisée :

    from vn_engine.animations import BaseAnimation, register
    import pygame

    @register("ma_rotation")
    class MaRotation(BaseAnimation):
        def get_transform(self, rect, surf):
            angle = self.progress * 360
            rotated = pygame.transform.rotate(surf, angle)
            new_rect = rotated.get_rect(center=rect.center)
            return rotated, new_rect
"""

import math
import random
import pygame

_REGISTRY: dict = {}


def register(name: str):
    """Décorateur pour enregistrer une animation dans le registre global."""
    def decorator(cls):
        _REGISTRY[name] = cls
        return cls
    return decorator


def create(name: str, duration_ms: int = 500, **kwargs):
    """Instancie une animation par son nom avec des paramètres optionnels."""
    cls = _REGISTRY.get(name)
    if cls is None:
        return None
    try:
        return cls(duration_ms, **kwargs)
    except TypeError:
        return cls(duration_ms)


class BaseAnimation:
    """
    Base pour toutes les animations de personnage.
    Sous-classes : implémenter get_transform(rect, surf).
    """

    def __init__(self, duration_ms: int = 500):
        self.duration_ms = max(1, int(duration_ms))
        self._elapsed = 0
        self.done = False

    def tick(self, delta_ms: int):
        self._elapsed = min(self._elapsed + delta_ms, self.duration_ms)
        if self._elapsed >= self.duration_ms:
            self.done = True

    @property
    def progress(self) -> float:
        """0.0 (début) → 1.0 (fin)."""
        return self._elapsed / self.duration_ms

    def get_transform(self, rect: pygame.Rect, surf: pygame.Surface):
        """Retourne (surface, rect) modifiés par l'animation."""
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Animations intégrées
# ---------------------------------------------------------------------------

@register("shake")
class Shake(BaseAnimation):
    """Tremblement aléatoire qui s'atténue progressivement."""

    def __init__(self, duration_ms: int = 400, intensity: int = 12):
        super().__init__(duration_ms)
        self.intensity = int(intensity)

    def get_transform(self, rect, surf):
        fade = 1.0 - self.progress
        amt = int(self.intensity * fade)
        if amt <= 0:
            return surf, rect
        return surf, rect.move(
            random.randint(-amt, amt),
            random.randint(-amt, amt),
        )


@register("scale_up")
class ScaleUp(BaseAnimation):
    """Agrandissement pulsé : gonfle jusqu'à `scale` puis revient."""

    def __init__(self, duration_ms: int = 400, scale: float = 1.15):
        super().__init__(duration_ms)
        self.target_scale = float(scale)

    def get_transform(self, rect, surf):
        # Enveloppe parabolique 0 → max → 0
        envelope = 4 * self.progress * (1.0 - self.progress)
        s = 1.0 + (self.target_scale - 1.0) * envelope
        new_w = max(1, int(surf.get_width() * s))
        new_h = max(1, int(surf.get_height() * s))
        scaled = pygame.transform.smoothscale(surf, (new_w, new_h))
        return scaled, scaled.get_rect(center=rect.center)


@register("bounce")
class Bounce(BaseAnimation):
    """Saut vers le haut et retombée (arc parabolique)."""

    def __init__(self, duration_ms: int = 450, height: int = 30):
        super().__init__(duration_ms)
        self.height = int(height)

    def get_transform(self, rect, surf):
        arc = 4 * self.progress * (1.0 - self.progress)
        return surf, rect.move(0, -int(self.height * arc))


@register("translate")
class Translate(BaseAnimation):
    """Déplacement pulsé : nudge vers (dx, dy) puis retour à la position initiale."""

    def __init__(self, duration_ms: int = 500, dx: int = 0, dy: int = -20):
        super().__init__(duration_ms)
        self.dx = int(dx)
        self.dy = int(dy)

    def get_transform(self, rect, surf):
        envelope = 4 * self.progress * (1.0 - self.progress)
        return surf, rect.move(
            int(self.dx * envelope),
            int(self.dy * envelope),
        )


@register("slide_in")
class SlideIn(BaseAnimation):
    """Glissement depuis un décalage initial (dx, dy) vers la position finale."""

    def __init__(self, duration_ms: int = 500, dx: int = 80, dy: int = 0):
        super().__init__(duration_ms)
        self.dx = int(dx)
        self.dy = int(dy)

    def get_transform(self, rect, surf):
        t = self.progress
        ease = t * t * (3.0 - 2.0 * t)  # smooth-step
        return surf, rect.move(
            int(self.dx * (1.0 - ease)),
            int(self.dy * (1.0 - ease)),
        )


@register("slide_out")
class SlideOut(BaseAnimation):
    """Glissement vers un décalage final (dx, dy) — animation de sortie."""

    def __init__(self, duration_ms: int = 500, dx: int = 80, dy: int = 0):
        super().__init__(duration_ms)
        self.dx = int(dx)
        self.dy = int(dy)

    def get_transform(self, rect, surf):
        t = self.progress
        ease = t * t * (3.0 - 2.0 * t)
        return surf, rect.move(int(self.dx * ease), int(self.dy * ease))


@register("fade_in")
class FadeIn(BaseAnimation):
    """Apparition progressive depuis transparent vers opaque."""

    def get_transform(self, rect, surf):
        copy = surf.copy()
        copy.fill((255, 255, 255, int(255 * self.progress)), special_flags=pygame.BLEND_RGBA_MULT)
        return copy, rect


@register("fade_out")
class FadeOut(BaseAnimation):
    """Disparition progressive depuis opaque vers transparent."""

    def get_transform(self, rect, surf):
        copy = surf.copy()
        copy.fill((255, 255, 255, int(255 * (1.0 - self.progress))), special_flags=pygame.BLEND_RGBA_MULT)
        return copy, rect


@register("zoom_in")
class ZoomIn(BaseAnimation):
    """Entrée dramatique : zoom depuis `start_scale` vers la taille normale."""

    def __init__(self, duration_ms: int = 500, start_scale: float = 0.3):
        super().__init__(duration_ms)
        self.start_scale = float(start_scale)

    def get_transform(self, rect, surf):
        t = self.progress
        ease = t * t * (3.0 - 2.0 * t)
        s = self.start_scale + (1.0 - self.start_scale) * ease
        new_w = max(1, int(surf.get_width() * s))
        new_h = max(1, int(surf.get_height() * s))
        scaled = pygame.transform.smoothscale(surf, (new_w, new_h))
        return scaled, scaled.get_rect(center=rect.center)


@register("zoom_out")
class ZoomOut(BaseAnimation):
    """Sortie : rétrécissement depuis la taille normale vers `end_scale`."""

    def __init__(self, duration_ms: int = 500, end_scale: float = 0.3):
        super().__init__(duration_ms)
        self.end_scale = float(end_scale)

    def get_transform(self, rect, surf):
        t = self.progress
        ease = t * t * (3.0 - 2.0 * t)
        s = 1.0 - (1.0 - self.end_scale) * ease
        new_w = max(1, int(surf.get_width() * s))
        new_h = max(1, int(surf.get_height() * s))
        scaled = pygame.transform.smoothscale(surf, (new_w, new_h))
        return scaled, scaled.get_rect(center=rect.center)


@register("swing")
class Swing(BaseAnimation):
    """Oscillation pendulaire qui s'atténue — pour l'emphase ou la surprise."""

    def __init__(self, duration_ms: int = 600, angle: float = 15.0, oscillations: float = 2.5):
        super().__init__(duration_ms)
        self.angle = float(angle)
        self.oscillations = float(oscillations)

    def get_transform(self, rect, surf):
        fade = 1.0 - self.progress
        a = math.sin(self.progress * math.pi * 2 * self.oscillations) * self.angle * fade
        rotated = pygame.transform.rotate(surf, a)
        return rotated, rotated.get_rect(center=rect.center)


@register("flash")
class Flash(BaseAnimation):
    """Éclair blanc bref — réaction à un choc, une révélation, une attaque."""

    def __init__(self, duration_ms: int = 300, intensity: int = 200):
        super().__init__(duration_ms)
        self.intensity = min(255, int(intensity))

    def get_transform(self, rect, surf):
        envelope = 4 * self.progress * (1.0 - self.progress)
        alpha = int(self.intensity * envelope)
        if alpha <= 0:
            return surf, rect
        copy = surf.copy()
        copy.fill((alpha, alpha, alpha, 0), special_flags=pygame.BLEND_RGB_ADD)
        return copy, rect


@register("hover")
class Hover(BaseAnimation):
    """Flottement sinusoïdal continu — pour les personnages éthérés ou fantomatiques."""

    def __init__(self, duration_ms: int = 1200, height: int = 12, cycles: float = 1.0):
        super().__init__(duration_ms)
        self.height = int(height)
        self.cycles = float(cycles)

    def get_transform(self, rect, surf):
        dy = math.sin(self.progress * math.pi * 2 * self.cycles) * self.height
        return surf, rect.move(0, int(dy))


@register("_move_to")
class _MoveTo(BaseAnimation):
    """Glissement du rect depuis (start_x, start_y) vers la position cible — usage interne."""

    def __init__(self, duration_ms: int = 400, start_x: int = 0, start_y: int = 0):
        super().__init__(duration_ms)
        self.start_x = int(start_x)
        self.start_y = int(start_y)

    def get_transform(self, rect, surf):
        t = self.progress
        ease = t * t * (3.0 - 2.0 * t)  # smooth-step
        x = int(self.start_x + (rect.x - self.start_x) * ease)
        y = int(self.start_y + (rect.y - self.start_y) * ease)
        return surf, pygame.Rect(x, y, rect.width, rect.height)
