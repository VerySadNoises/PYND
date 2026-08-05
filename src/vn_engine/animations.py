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
    """
    Glissement depuis un décalage initial (dx, dy) vers la position finale.
    Utile pour faire entrer un personnage en douceur.
    """

    def __init__(self, duration_ms: int = 500, dx: int = 80, dy: int = 0):
        super().__init__(duration_ms)
        self.dx = int(dx)
        self.dy = int(dy)

    def get_transform(self, rect, surf):
        # Smooth-step : accélération douce au départ et à l'arrivée
        t = self.progress
        ease = t * t * (3.0 - 2.0 * t)
        return surf, rect.move(
            int(self.dx * (1.0 - ease)),
            int(self.dy * (1.0 - ease)),
        )
