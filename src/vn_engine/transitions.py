"""
Système de transitions modulaire.

Pour ajouter une nouvelle transition :
    from vn_engine.transitions import BaseTransition, register

    @register("ma_transition")
    class MaTransition(BaseTransition):
        def _alpha(self): return int(self.progress * 255)
        def _color(self): return (255, 0, 0)   # rouge
"""

import pygame

_REGISTRY: dict = {}


def register(name: str):
    """Décorateur pour enregistrer une transition dans le registre global."""
    def decorator(cls):
        _REGISTRY[name] = cls
        return cls
    return decorator


def create(name: str, duration_ms: int = 500):
    """Instancie une transition par son nom; retourne None si inconnue."""
    cls = _REGISTRY.get(name)
    if cls is None:
        return None
    return cls(duration_ms)


class BaseTransition:
    """
    Transition de base basée sur un overlay coloré semi-transparent.
    Sous-classes : implémenter _alpha() et _color().
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

    def render(self, screen: pygame.Surface):
        alpha = self._alpha()
        if alpha <= 0:
            return
        overlay = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        overlay.fill((*self._color(), alpha))
        screen.blit(overlay, (0, 0))

    def _alpha(self) -> int:
        raise NotImplementedError

    def _color(self) -> tuple:
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Transitions intégrées
# ---------------------------------------------------------------------------

@register("fade_black")
class FadeBlack(BaseTransition):
    """Fondu au noir : l'écran devient progressivement noir."""
    def _alpha(self): return int(self.progress * 255)
    def _color(self): return (0, 0, 0)


@register("fade_white")
class FadeWhite(BaseTransition):
    """Fondu au blanc : l'écran devient progressivement blanc."""
    def _alpha(self): return int(self.progress * 255)
    def _color(self): return (255, 255, 255)


@register("fade_in")
class FadeIn(BaseTransition):
    """Apparition depuis le noir : le noir se dissipe pour révéler la scène."""
    def _alpha(self): return int((1.0 - self.progress) * 255)
    def _color(self): return (0, 0, 0)


@register("fade_in_white")
class FadeInWhite(BaseTransition):
    """Apparition depuis le blanc : le blanc se dissipe pour révéler la scène."""
    def _alpha(self): return int((1.0 - self.progress) * 255)
    def _color(self): return (255, 255, 255)
