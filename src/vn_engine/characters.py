import pygame
from pathlib import Path


class Character:
    def __init__(self, char_id, name, image_path=None, position="center", base_dir=None):
        self.id = char_id
        self.name = name
        self.image_path = image_path
        self.default_position = position
        self.base_dir = Path(base_dir) if base_dir else Path(".")
        self._surf_original = None
        self.surf = None
        self.rect = None
        self.visible = False

    def load(self, screen_size):
        if not self.image_path:
            return
        p = Path(self.image_path)
        if not p.is_absolute():
            p = (self.base_dir / p).resolve()
        try:
            raw = pygame.image.load(str(p))
            self._surf_original = (
                raw.convert_alpha() if raw.get_flags() & pygame.SRCALPHA else raw.convert()
            )
            self._scale(screen_size)
        except Exception as e:
            print(f"[Character] Cannot load '{self.id}': {e}")

    def _scale(self, screen_size):
        if not self._surf_original:
            return
        _, sh = screen_size
        max_h = int(sh * 0.65)
        w, h = self._surf_original.get_size()
        if h > max_h:
            scale = max_h / h
            w, h = int(w * scale), int(h * scale)
        self.surf = pygame.transform.smoothscale(self._surf_original, (w, h))

    def place(self, screen_size, position=None):
        if not self.surf:
            return
        sw, sh = screen_size
        pos = (position or self.default_position).lower()
        margin_x = int(sw * 0.05)
        bottom_offset = int(sh * 0.12)
        img_w, img_h = self.surf.get_size()
        if pos in ("left", "l"):
            x = margin_x
        elif pos in ("right", "r"):
            x = sw - img_w - margin_x
        else:
            x = (sw - img_w) // 2
        y = sh - img_h - bottom_offset
        self.rect = pygame.Rect(x, y, img_w, img_h)
        self.visible = True

    def hide(self):
        self.visible = False

    def render(self, screen, is_speaking, dim_alpha=160):
        if not self.visible or not self.surf or not self.rect:
            return
        screen.blit(self.surf, self.rect)
        if not is_speaking and dim_alpha > 0:
            overlay = pygame.Surface(self.rect.size, pygame.SRCALPHA)
            overlay.fill((150, 150, 150, int(dim_alpha)))
            screen.blit(overlay, self.rect)


class CharacterRegistry:
    def __init__(self, data, base_dir):
        self._chars = {}
        for cid, cfg in (data or {}).items():
            self._chars[cid] = Character(
                char_id=cid,
                name=cfg.get("name", cid),
                image_path=cfg.get("image"),
                position=cfg.get("position", "center"),
                base_dir=base_dir,
            )

    def get(self, char_id):
        return self._chars.get(char_id)

    def all(self):
        return list(self._chars.values())

    def show(self, char_id, screen_size, position=None):
        c = self._chars.get(char_id)
        if not c:
            print(f"[Registry] Unknown character id: '{char_id}'")
            return
        if not c.surf:
            c.load(screen_size)
        c.place(screen_size, position)

    def hide(self, char_id):
        c = self._chars.get(char_id)
        if c:
            c.hide()

    def hide_all(self):
        for c in self._chars.values():
            c.hide()

    def resolve_speaker(self, speaker_name):
        """Return char_id matching speaker by id or display name (case-insensitive)."""
        if not speaker_name:
            return None
        s = str(speaker_name).strip().lower()
        for cid, c in self._chars.items():
            if cid.lower() == s or c.name.lower() == s:
                return cid
        return None
