import pygame
import json
from pathlib import Path
from vn_engine.script_parser import load_story
from vn_engine.characters import CharacterRegistry
from vn_engine.dialogue import ActionExecutor


class SaveManager:
    def __init__(self, save_dir="saves"):
        self.save_dir = Path(save_dir)
        self.save_dir.mkdir(parents=True, exist_ok=True)

    def save(self, slot, data):
        path = self.save_dir / f"slot_{slot}.json"
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def load(self, slot):
        path = self.save_dir / f"slot_{slot}.json"
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))


class VNApp:
    _DLGBOX_H = 200
    _DLGBOX_COLOR = (10, 10, 20, 210)
    _SPEAKER_COLOR = (255, 220, 100)
    _TEXT_COLOR = (230, 230, 230)
    _CHOICE_COLOR = (200, 200, 100)
    _CHOICE_HOVER = (255, 255, 160)

    def __init__(self, story_path, width=1280, height=720):
        pygame.init()
        self.W, self.H = width, height
        self.screen = pygame.display.set_mode((self.W, self.H))
        pygame.display.set_caption("VN Engine")
        self.clock = pygame.time.Clock()
        self.font_text = pygame.font.Font(None, 30)
        self.font_speaker = pygame.font.Font(None, 36)
        self.font_choice = pygame.font.Font(None, 28)

        story = load_story(story_path)
        self.base_dir = Path(story_path).resolve().parent
        self.chars = CharacterRegistry(story["characters"], base_dir=self.base_dir)
        self.scenes = story["scenes"]

        self.variables = {}
        self.save_manager = SaveManager()
        self.executor = ActionExecutor()
        self.current_bg = None
        self.dim_opacity = 160
        self.current_speaker_id = None
        self.current_speaker_name = ""
        self.current_text = ""
        self.choices = []
        self._choice_rects = []
        self.mode = "running"
        self.running = True

        self._load_scene(next(iter(self.scenes)))

    # ------------------------------------------------------------------
    # Scene loading
    # ------------------------------------------------------------------

    def _load_scene(self, scene_id):
        scene = self.scenes.get(scene_id)
        if not scene:
            print(f"[VN] Scene not found: {scene_id}")
            self.running = False
            return
        self._load_background(scene.get("background"))
        self.dim_opacity = scene.get("dim_opacity", 160)
        self.chars.hide_all()
        for entry in (scene.get("characters") or []):
            if isinstance(entry, dict):
                cid = next(iter(entry))
                pos = (entry[cid] or {}).get("position")
            else:
                cid, pos = entry, None
            self.chars.show(cid, (self.W, self.H), position=pos)
        self.executor.load(scene.get("actions", []))
        self.mode = "running"

    def _load_background(self, bg_path):
        if not bg_path:
            self.current_bg = None
            return
        try:
            p = Path(bg_path)
            if not p.is_absolute():
                p = (self.base_dir / p).resolve()
            surf = pygame.image.load(str(p)).convert()
            self.current_bg = pygame.transform.scale(surf, (self.W, self.H))
        except Exception as e:
            print(f"[BG] {e}")
            self.current_bg = None

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    def run(self):
        while self.running:
            self._handle_events()
            self._update()
            self._render()
            self.clock.tick(60)
        pygame.quit()

    def _handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                elif event.key == pygame.K_SPACE and self.mode == "waiting":
                    self.mode = "running"
                elif self.mode == "choice":
                    idx = event.key - pygame.K_1
                    if 0 <= idx < len(self.choices):
                        self._select_choice(idx)
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self.mode == "waiting":
                    self.mode = "running"
                elif self.mode == "choice":
                    for i, rect in enumerate(self._choice_rects):
                        if rect.collidepoint(event.pos):
                            self._select_choice(i)
                            break

    def _update(self):
        if self.mode == "running":
            self._execute_next()

    def _execute_next(self):
        if self.executor.finished:
            self.running = False
            return
        action = self.executor.current()
        if action is None:
            self.running = False
            return
        self._dispatch(action)

    # ------------------------------------------------------------------
    # Action dispatcher
    # ------------------------------------------------------------------

    def _dispatch(self, action):
        if not isinstance(action, dict):
            self.executor.advance()
            return

        if "say" in action:
            d = action["say"] or {}
            self.current_speaker_name = d.get("speaker", "")
            self.current_speaker_id = self.chars.resolve_speaker(self.current_speaker_name)
            self.current_text = d.get("text", "")
            self.executor.advance()
            self.mode = "waiting"

        elif "choice" in action:
            self.choices = action["choice"] or []
            self.mode = "choice"

        elif "set" in action:
            for k, v in (action["set"] or {}).items():
                self.variables[k] = v
            self.executor.advance()

        elif "jump" in action or "goto" in action:
            dest = action.get("jump") or action.get("goto")
            if dest in self.scenes:
                self._load_scene(dest)
            else:
                print(f"[VN] Unknown scene: {dest}")
                self.executor.advance()

        elif "show" in action:
            d = action["show"] or {}
            cid = d.get("id")
            if cid:
                self.chars.show(cid, (self.W, self.H), position=d.get("position"))
            self.executor.advance()

        elif "hide" in action:
            d = action["hide"]
            cid = d.get("id") if isinstance(d, dict) else d
            self.chars.hide(cid) if cid else self.chars.hide_all()
            self.executor.advance()

        elif "background" in action:
            self._load_background(action["background"])
            self.executor.advance()

        else:
            self.executor.advance()

    def _select_choice(self, idx):
        choice = self.choices[idx]
        for k, v in (choice.get("set") or {}).items():
            self.variables[k] = v
        # collect sub-actions, append goto as a synthetic action
        sub = list(choice.get("actions") or [])
        dest = choice.get("goto") or choice.get("jump")
        if dest:
            sub.append({"goto": dest})
        self.executor.advance()  # move past the choice node
        if sub:
            self.executor.push(sub)
        self.choices = []
        self._choice_rects = []
        self.mode = "running"

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    def _render(self):
        self.screen.fill((20, 20, 30))
        if self.current_bg:
            self.screen.blit(self.current_bg, (0, 0))
        for char in self.chars.all():
            if not char.visible:
                continue
            is_speaking = (char.id == self.current_speaker_id)
            char.render(self.screen, is_speaking, dim_alpha=self.dim_opacity)
        self._render_dialogue_box()
        if self.mode == "choice":
            self._render_choices()
        pygame.display.flip()

    def _render_dialogue_box(self):
        box_y = self.H - self._DLGBOX_H
        box_surf = pygame.Surface((self.W, self._DLGBOX_H), pygame.SRCALPHA)
        box_surf.fill(self._DLGBOX_COLOR)
        self.screen.blit(box_surf, (0, box_y))
        pad = 30
        y = box_y + 14
        if self.current_speaker_name:
            surf = self.font_speaker.render(str(self.current_speaker_name), True, self._SPEAKER_COLOR)
            self.screen.blit(surf, (pad, y))
            y += surf.get_height() + 8
        if self.current_text:
            self._draw_text_wrapped(self.current_text, pad, y, self.font_text,
                                    self._TEXT_COLOR, self.W - pad * 2)

    def _render_choices(self):
        self._choice_rects = []
        cy = int(self.H * 0.42)
        pad_x = 60
        bg_pad = 8
        mouse = pygame.mouse.get_pos()
        line_h = self.font_choice.get_linesize()
        for i, c in enumerate(self.choices):
            txt = f"{i + 1}.  {c.get('text', '')}"
            hit = pygame.Rect(pad_x - bg_pad, cy - bg_pad,
                              self.W - pad_x * 2, line_h + bg_pad * 2)
            self._choice_rects.append(hit)
            color = self._CHOICE_COLOR
            if hit.collidepoint(mouse):
                hl = pygame.Surface(hit.size, pygame.SRCALPHA)
                hl.fill((255, 255, 100, 40))
                self.screen.blit(hl, hit)
                color = self._CHOICE_HOVER
            self.screen.blit(self.font_choice.render(txt, True, color), (pad_x, cy))
            cy += line_h + 14

    def _draw_text_wrapped(self, text, x, y, font, color, max_width):
        line = ""
        for word in text.split():
            test = line + (" " if line else "") + word
            if font.render(test, True, color).get_width() <= max_width:
                line = test
            else:
                self.screen.blit(font.render(line, True, color), (x, y))
                y += font.get_linesize() + 2
                line = word
        if line:
            self.screen.blit(font.render(line, True, color), (x, y))
