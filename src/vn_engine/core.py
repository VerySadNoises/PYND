import json
from pathlib import Path

import pygame

from vn_engine.script_parser import load_story
from vn_engine.characters import CharacterRegistry
from vn_engine.dialogue import ActionExecutor


_VIDEO_EXTS = {
    ".mp4",
    ".avi",
    ".mov",
    ".mkv",
    ".webm",
}


class SaveManager:
    def __init__(self, save_dir="saves"):
        self.save_dir = Path(save_dir)
        self.save_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

    def save(self, slot, data):
        path = self.save_dir / f"slot_{slot}.json"

        path.write_text(
            json.dumps(data, indent=2),
            encoding="utf-8",
        )

    def load(self, slot):
        path = self.save_dir / f"slot_{slot}.json"

        if not path.exists():
            return None

        return json.loads(
            path.read_text(encoding="utf-8")
        )


class VNApp:
    _DLGBOX_H = 200
    _DLGBOX_COLOR = (10, 10, 20, 210)
    _SPEAKER_COLOR = (255, 220, 100)
    _TEXT_COLOR = (230, 230, 230)
    _CHOICE_COLOR = (200, 200, 100)
    _CHOICE_HOVER = (255, 255, 160)

    def __init__(
        self,
        story_path,
        width=1280,
        height=720,
    ):
        pygame.init()

        try:
            pygame.mixer.init(
                frequency=44100,
                size=-16,
                channels=2,
                buffer=512,
            )
        except pygame.error as error:
            print(f"[Audio] Initialisation impossible: {error}")

        self.W = width
        self.H = height

        self.screen = pygame.display.set_mode(
            (self.W, self.H)
        )

        pygame.display.set_caption("VN Engine")

        self.clock = pygame.time.Clock()

        self.font_text = pygame.font.Font(None, 30)
        self.font_speaker = pygame.font.Font(None, 36)
        self.font_choice = pygame.font.Font(None, 28)

        story = load_story(story_path)

        self.base_dir = Path(story_path).resolve().parent

        self.chars = CharacterRegistry(
            story["characters"],
            base_dir=self.base_dir,
        )

        self.scenes = story["scenes"]

        self.variables = {}
        self.save_manager = SaveManager()
        self.executor = ActionExecutor()

        # ------------------------------------------------------------------
        # Arrière-plan
        # ------------------------------------------------------------------

        self.current_bg = None

        # GIF animé : liste de tuples (surface, durée_en_ms)
        self._bg_frames = None
        self._bg_frame_idx = 0
        self._bg_frame_elapsed = 0

        # Vidéo via OpenCV et audio optionnel via ffpyplayer.
        self._bg_video = None
        self._bg_video_ms = 0.0
        self._bg_video_elapsed = 0
        self._bg_audio = None

        # ------------------------------------------------------------------
        # Dialogues et personnages
        # ------------------------------------------------------------------

        # Cette valeur ne représente plus une opacité.
        # Elle représente maintenant une quantité d'assombrissement :
        #
        # 0   = aucune modification
        # 255 = personnage complètement noir
        #
        # Le canal alpha du personnage reste toujours inchangé.
        self.character_dim = 120

        self.current_speaker_id = None
        self.current_speaker_name = ""
        self.current_text = ""

        self.choices = []
        self._choice_rects = []

        self.mode = "running"
        self.running = True

        first_scene_id = next(iter(self.scenes), None)

        if first_scene_id is None:
            print("[VN] Aucun scénario trouvé.")
            self.running = False
        else:
            self._load_scene(first_scene_id)

    # ------------------------------------------------------------------
    # Chargement d'une scène
    # ------------------------------------------------------------------

    def _load_scene(self, scene_id):
        scene = self.scenes.get(scene_id)

        if scene is None:
            print(f"[VN] Scene not found: {scene_id}")
            self.running = False
            return

        self._load_background(scene.get("background"))
        self._play_music(scene.get("music"))

        # Nouveau nom conseillé dans le YAML : character_dim.
        #
        # dim_opacity reste accepté pour conserver la compatibilité avec
        # les anciens fichiers, mais la valeur ne contrôle plus une opacité.
        self.character_dim = scene.get(
            "character_dim",
            scene.get("dim_opacity", 120),
        )

        try:
            self.character_dim = int(self.character_dim)
        except (TypeError, ValueError):
            self.character_dim = 120

        self.character_dim = max(
            0,
            min(255, self.character_dim),
        )

        self.chars.hide_all()

        for entry in scene.get("characters") or []:
            if isinstance(entry, dict):
                character_id = next(iter(entry), None)

                if character_id is None:
                    continue

                character_config = entry.get(character_id) or {}
                position = character_config.get("position")

            else:
                character_id = entry
                position = None

            self.chars.show(
                character_id,
                (self.W, self.H),
                position=position,
            )

        self.current_speaker_id = None
        self.current_speaker_name = ""
        self.current_text = ""
        self.choices = []
        self._choice_rects = []

        self.executor.load(
            scene.get("actions", [])
        )

        self.mode = "running"

    # ------------------------------------------------------------------
    # Chargement de l'arrière-plan
    # ------------------------------------------------------------------

    def _load_background(self, bg_spec):
        if self._bg_video is not None:
            self._bg_video.release()

        if self._bg_audio is not None:
            try:
                self._bg_audio.close_player()
            except Exception:
                pass

        self.current_bg = None

        self._bg_frames = None
        self._bg_frame_idx = 0
        self._bg_frame_elapsed = 0

        self._bg_video = None
        self._bg_video_elapsed = 0

        self._bg_audio = None

        if not bg_spec:
            return

        # Accepte :
        #
        # background: chemin/image.png
        #
        # ou :
        #
        # background:
        #   file: chemin/video.mp4
        #   audio: true
        if isinstance(bg_spec, dict):
            bg_path = (
                bg_spec.get("file")
                or bg_spec.get("path", "")
            )

            audio = bool(bg_spec.get("audio", False))

        else:
            bg_path = bg_spec
            audio = False

        try:
            path = Path(bg_path)

            if not path.is_absolute():
                path = (self.base_dir / path).resolve()

            extension = path.suffix.lower()

            if extension in _VIDEO_EXTS:
                self._open_video(
                    path,
                    audio=audio,
                )

            elif extension == ".gif":
                self._bg_frames = self._load_gif_frames(path)

                if self._bg_frames:
                    self.current_bg = self._bg_frames[0][0]

            else:
                surface = pygame.image.load(str(path)).convert()

                self.current_bg = pygame.transform.scale(
                    surface,
                    (self.W, self.H),
                )

        except Exception as error:
            print(f"[BG] {error}")

    def _open_video(self, path, audio=False):
        try:
            import cv2
        except ImportError:
            print(
                "[BG] Installez opencv-python pour utiliser "
                "des vidéos : pip install opencv-python"
            )
            return

        capture = cv2.VideoCapture(str(path))

        if not capture.isOpened():
            print(f"[BG] Impossible d'ouvrir la vidéo: {path}")
            return

        fps = capture.get(cv2.CAP_PROP_FPS)

        if not fps or fps <= 0:
            fps = 24

        self._bg_video = capture
        self._bg_video_ms = 1000.0 / fps

        if audio:
            try:
                from ffpyplayer.player import MediaPlayer

                self._bg_audio = MediaPlayer(
                    str(path),
                    ff_opts={
                        "vn": False,
                        "an": False,
                    },
                )

            except ImportError:
                print(
                    "[BG] Installez ffpyplayer pour l'audio "
                    "des vidéos : pip install ffpyplayer"
                )

            except Exception as error:
                print(f"[BG] Audio init error: {error}")

        self._advance_video_frame()

    def _advance_video_frame(self):
        if self._bg_video is None:
            return

        import cv2

        success, frame = self._bg_video.read()

        if not success:
            self._bg_video.set(
                cv2.CAP_PROP_POS_FRAMES,
                0,
            )

            success, frame = self._bg_video.read()

        if not success:
            return

        frame_rgb = cv2.cvtColor(
            frame,
            cv2.COLOR_BGR2RGB,
        )

        height, width = frame_rgb.shape[:2]

        surface = pygame.image.frombuffer(
            frame_rgb.tobytes(),
            (width, height),
            "RGB",
        ).convert()

        self.current_bg = pygame.transform.scale(
            surface,
            (self.W, self.H),
        )

    def _load_gif_frames(self, path):
        """
        Retourne une liste de tuples :
            (surface, durée_en_ms)
        """
        try:
            from PIL import Image
        except ImportError:
            print(
                "[BG] Installez Pillow pour utiliser les GIF animés : "
                "pip install Pillow"
            )
            return None

        frames = []

        try:
            with Image.open(path) as image:
                frame_count = getattr(image, "n_frames", 1)

                for frame_index in range(frame_count):
                    image.seek(frame_index)

                    duration = image.info.get(
                        "duration",
                        100,
                    )

                    frame_rgba = image.convert("RGBA")
                    raw = frame_rgba.tobytes()
                    size = frame_rgba.size

                    surface = pygame.image.fromstring(
                        raw,
                        size,
                        "RGBA",
                    ).convert_alpha()

                    surface = pygame.transform.scale(
                        surface,
                        (self.W, self.H),
                    )

                    frames.append(
                        (
                            surface,
                            max(int(duration), 20),
                        )
                    )

        except Exception as error:
            print(f"[BG] Impossible de charger le GIF '{path}': {error}")
            return None

        return frames or None

    # ------------------------------------------------------------------
    # Boucle principale
    # ------------------------------------------------------------------

    def run(self):
        while self.running:
            self._handle_events()
            self._update()
            self._render()

            self.clock.tick(60)

        if self._bg_video is not None:
            self._bg_video.release()

        if self._bg_audio is not None:
            try:
                self._bg_audio.close_player()
            except Exception:
                pass

        pygame.mixer.music.stop()
        pygame.quit()

    def _handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False

                elif (
                    event.key == pygame.K_SPACE
                    and self.mode == "waiting"
                ):
                    self.mode = "running"

                elif self.mode == "choice":
                    choice_index = event.key - pygame.K_1

                    if 0 <= choice_index < len(self.choices):
                        self._select_choice(choice_index)

            elif (
                event.type == pygame.MOUSEBUTTONDOWN
                and event.button == 1
            ):
                if self.mode == "waiting":
                    self.mode = "running"

                elif self.mode == "choice":
                    for index, rect in enumerate(self._choice_rects):
                        if rect.collidepoint(event.pos):
                            self._select_choice(index)
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
    # Exécution des actions
    # ------------------------------------------------------------------

    def _dispatch(self, action):
        if not isinstance(action, dict):
            self.executor.advance()
            return

        if "say" in action:
            dialogue = action["say"] or {}

            self.current_speaker_name = dialogue.get(
                "speaker",
                "",
            )

            self.current_speaker_id = self.chars.resolve_speaker(
                self.current_speaker_name
            )

            self.current_text = dialogue.get(
                "text",
                "",
            )

            self.executor.advance()
            self.mode = "waiting"

        elif "choice" in action:
            self.choices = action["choice"] or []
            self.mode = "choice"

        elif "set" in action:
            for key, value in (action["set"] or {}).items():
                self.variables[key] = value

            self.executor.advance()

        elif "jump" in action or "goto" in action:
            destination = (
                action.get("jump")
                or action.get("goto")
            )

            if destination in self.scenes:
                self._load_scene(destination)

            else:
                print(f"[VN] Unknown scene: {destination}")
                self.executor.advance()

        elif "show" in action:
            show_data = action["show"] or {}
            character_id = show_data.get("id")

            if character_id:
                self.chars.show(
                    character_id,
                    (self.W, self.H),
                    position=show_data.get("position"),
                )

            self.executor.advance()

        elif "hide" in action:
            hide_data = action["hide"]

            if isinstance(hide_data, dict):
                character_id = hide_data.get("id")
            else:
                character_id = hide_data

            if character_id:
                self.chars.hide(character_id)
            else:
                self.chars.hide_all()

            self.executor.advance()

        elif "background" in action:
            self._load_background(action["background"])
            self.executor.advance()

        elif "music" in action:
            self._play_music(action["music"])
            self.executor.advance()

        else:
            self.executor.advance()

    # ------------------------------------------------------------------
    # Musique
    # ------------------------------------------------------------------

    def _play_music(self, spec):
        if not pygame.mixer.get_init():
            return

        if not spec or spec in ("stop", "none", False):
            pygame.mixer.music.stop()
            return

        if isinstance(spec, dict):
            path_value = (
                spec.get("file")
                or spec.get("path", "")
            )

            try:
                volume = float(spec.get("volume", 1.0))
            except (TypeError, ValueError):
                volume = 1.0

        else:
            path_value = spec
            volume = 1.0

        try:
            path = Path(path_value)

            if not path.is_absolute():
                path = (self.base_dir / path).resolve()

            pygame.mixer.music.load(str(path))

            pygame.mixer.music.set_volume(
                max(0.0, min(1.0, volume))
            )

            # -1 signifie que la musique boucle indéfiniment.
            pygame.mixer.music.play(loops=-1)

        except Exception as error:
            print(f"[Music] {error}")

    # ------------------------------------------------------------------
    # Choix
    # ------------------------------------------------------------------

    def _select_choice(self, index):
        if not 0 <= index < len(self.choices):
            return

        choice = self.choices[index]

        for key, value in (choice.get("set") or {}).items():
            self.variables[key] = value

        sub_actions = list(
            choice.get("actions") or []
        )

        destination = (
            choice.get("goto")
            or choice.get("jump")
        )

        if destination:
            sub_actions.append(
                {"goto": destination}
            )

        # Passe le nœud de choix dans l'exécuteur principal.
        self.executor.advance()

        if sub_actions:
            self.executor.push(sub_actions)

        self.choices = []
        self._choice_rects = []
        self.mode = "running"

    # ------------------------------------------------------------------
    # Affichage
    # ------------------------------------------------------------------

    def _render(self):
        self.screen.fill((20, 20, 30))

        delta_time = self.clock.get_time()

        self._update_animated_background(delta_time)

        if self.current_bg is not None:
            self.screen.blit(
                self.current_bg,
                (0, 0),
            )

        for character in self.chars.all():
            if not character.visible:
                continue

            is_speaking = (
                character.id == self.current_speaker_id
            )

            character.render(
                self.screen,
                is_speaking=is_speaking,
                dim_amount=self.character_dim,
            )

        self._render_dialogue_box()

        if self.mode == "choice":
            self._render_choices()

        pygame.display.flip()

    def _update_animated_background(self, delta_time):
        if self._bg_video is not None:
            self._bg_video_elapsed += delta_time

            # La boucle while évite de ralentir la vidéo si une image
            # du jeu prend plus de temps que prévu.
            while self._bg_video_elapsed >= self._bg_video_ms:
                self._bg_video_elapsed -= self._bg_video_ms
                self._advance_video_frame()

        elif self._bg_frames:
            self._bg_frame_elapsed += delta_time

            _, duration = self._bg_frames[self._bg_frame_idx]

            while self._bg_frame_elapsed >= duration:
                self._bg_frame_elapsed -= duration

                self._bg_frame_idx = (
                    self._bg_frame_idx + 1
                ) % len(self._bg_frames)

                _, duration = self._bg_frames[self._bg_frame_idx]

            self.current_bg = self._bg_frames[
                self._bg_frame_idx
            ][0]

    def _render_dialogue_box(self):
        box_y = self.H - self._DLGBOX_H

        box_surface = pygame.Surface(
            (self.W, self._DLGBOX_H),
            pygame.SRCALPHA,
        )

        box_surface.fill(self._DLGBOX_COLOR)

        self.screen.blit(
            box_surface,
            (0, box_y),
        )

        padding = 30
        y = box_y + 14

        if self.current_speaker_name:
            speaker_surface = self.font_speaker.render(
                str(self.current_speaker_name),
                True,
                self._SPEAKER_COLOR,
            )

            self.screen.blit(
                speaker_surface,
                (padding, y),
            )

            y += speaker_surface.get_height() + 8

        if self.current_text:
            self._draw_text_wrapped(
                text=self.current_text,
                x=padding,
                y=y,
                font=self.font_text,
                color=self._TEXT_COLOR,
                max_width=self.W - padding * 2,
            )

    def _render_choices(self):
        self._choice_rects = []

        current_y = int(self.H * 0.42)
        padding_x = 60
        background_padding = 8

        mouse_position = pygame.mouse.get_pos()
        line_height = self.font_choice.get_linesize()

        for index, choice in enumerate(self.choices):
            text = (
                f"{index + 1}.  "
                f"{choice.get('text', '')}"
            )

            hit_rect = pygame.Rect(
                padding_x - background_padding,
                current_y - background_padding,
                self.W - padding_x * 2,
                line_height + background_padding * 2,
            )

            self._choice_rects.append(hit_rect)

            color = self._CHOICE_COLOR

            if hit_rect.collidepoint(mouse_position):
                highlight = pygame.Surface(
                    hit_rect.size,
                    pygame.SRCALPHA,
                )

                highlight.fill(
                    (255, 255, 100, 40)
                )

                self.screen.blit(
                    highlight,
                    hit_rect,
                )

                color = self._CHOICE_HOVER

            choice_surface = self.font_choice.render(
                text,
                True,
                color,
            )

            self.screen.blit(
                choice_surface,
                (padding_x, current_y),
            )

            current_y += line_height + 14

    def _draw_text_wrapped(
        self,
        text,
        x,
        y,
        font,
        color,
        max_width,
    ):
        current_line = ""

        for word in str(text).split():
            candidate_line = (
                current_line + (" " if current_line else "") + word
            )

            candidate_width = font.render(
                candidate_line,
                True,
                color,
            ).get_width()

            if candidate_width <= max_width:
                current_line = candidate_line
                continue

            if current_line:
                line_surface = font.render(
                    current_line,
                    True,
                    color,
                )

                self.screen.blit(
                    line_surface,
                    (x, y),
                )

                y += font.get_linesize() + 2

            current_line = word

        if current_line:
            line_surface = font.render(
                current_line,
                True,
                color,
            )

            self.screen.blit(
                line_surface,
                (x, y),
            )