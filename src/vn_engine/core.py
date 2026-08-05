import ast
import json
from pathlib import Path

import pygame

from vn_engine.script_parser import load_story
from vn_engine.characters import CharacterRegistry
from vn_engine.dialogue import ActionExecutor
from vn_engine.transitions import create as _create_transition
from vn_engine.animations import create as _create_animation


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


# ---------------------------------------------------------------------------
# Évaluation sécurisée des conditions (sans eval)
# ---------------------------------------------------------------------------

def _eval_ast_node(node, variables, _rhs=False):
    """Évalue récursivement un nœud AST Python contre un dict de variables."""
    if isinstance(node, ast.BoolOp):
        values = [_eval_ast_node(v, variables) for v in node.values]
        if isinstance(node.op, ast.And):
            return all(values)
        return any(values)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
        return not _eval_ast_node(node.operand, variables)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        val = _eval_ast_node(node.operand, variables)
        return -(val if val is not None else 0)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.UAdd):
        val = _eval_ast_node(node.operand, variables)
        return +(val if val is not None else 0)
    if isinstance(node, ast.BinOp):
        left  = _eval_ast_node(node.left,  variables)
        right = _eval_ast_node(node.right, variables)
        # Les variables non définies (None) valent 0 dans les calculs numériques
        if left  is None: left  = 0
        if right is None: right = 0
        op_type = type(node.op)
        try:
            if op_type is ast.Add:       return left + right
            if op_type is ast.Sub:       return left - right
            if op_type is ast.Mult:      return left * right
            if op_type is ast.Div:       return left / right
            if op_type is ast.FloorDiv:  return left // right
            if op_type is ast.Mod:       return left % right
            if op_type is ast.Pow:       return left ** right
        except (TypeError, ZeroDivisionError):
            return None
        return None
    if isinstance(node, ast.Compare):
        left = _eval_ast_node(node.left, variables, _rhs=False)
        for op, comparator in zip(node.ops, node.comparators):
            right = _eval_ast_node(comparator, variables, _rhs=True)
            op_type = type(op)
            try:
                if op_type is ast.Eq:
                    passed = left == right
                elif op_type is ast.NotEq:
                    passed = left != right
                elif op_type is ast.Lt:
                    passed = left < right
                elif op_type is ast.LtE:
                    passed = left <= right
                elif op_type is ast.Gt:
                    passed = left > right
                elif op_type is ast.GtE:
                    passed = left >= right
                else:
                    passed = False
            except TypeError:
                passed = False
            if not passed:
                return False
            left = right
        return True
    if isinstance(node, ast.Name):
        name = node.id
        if name == "true":
            return True
        if name == "false":
            return False
        if name in ("null", "none"):
            return None
        # Côté droit d'une comparaison : si la variable n'est pas définie,
        # traiter le nom comme un littéral chaîne (ex: mood == confident).
        if _rhs and name not in variables:
            return name
        return variables.get(name, None)
    if isinstance(node, ast.Constant):
        return node.value
    # Compatibilité Python < 3.8
    if isinstance(node, ast.NameConstant):
        return node.value
    if isinstance(node, ast.Num):
        return node.n
    if isinstance(node, ast.Str):
        return node.s
    raise ValueError(f"Nœud AST non supporté : {type(node).__name__}")


def _evaluate_condition(expr, variables):
    """Retourne True si la condition str est vérifiée, False sinon."""
    if not expr:
        return True
    text = str(expr).strip().lower()
    if text in ("true", "1", "yes"):
        return True
    if text in ("false", "0", "no"):
        return False
    try:
        tree = ast.parse(str(expr), mode="eval")
        return bool(_eval_ast_node(tree.body, variables))
    except Exception:
        return True


def _evaluate_expression(expr, variables):
    """Évalue une expression pour l'action set (arithmétique, variable, littéral)."""
    if not isinstance(expr, str):
        return expr
    try:
        tree = ast.parse(str(expr), mode="eval")
        # _rhs=True : un nom inconnu est traité comme un littéral chaîne
        result = _eval_ast_node(tree.body, variables, _rhs=True)
        return result
    except Exception:
        return expr


def _interpolate(text, variables):
    """Remplace {variable} dans le texte par la valeur de la variable."""
    if not isinstance(text, str) or "{" not in text:
        return text

    class _SafeDict(dict):
        def __missing__(self, key):  # laisse {key} intact si la variable n'existe pas
            return f"{{{key}}}"

    try:
        return str(text).format_map(_SafeDict(variables))
    except Exception:
        return text


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
        base_dir=None,
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

        # Réserve 16 canaux : canal 0 = réservé musique, 1-15 = effets sonores
        pygame.mixer.set_num_channels(16)

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

        # base_dir est la racine depuis laquelle les chemins d'assets sont résolus.
        # Si non fourni, on remonte d'un niveau par rapport au story.yaml
        # pour retomber sur la racine du projet (cas typique : examples/story.yaml).
        story_parent = Path(story_path).resolve().parent
        if base_dir is not None:
            self.base_dir = Path(base_dir).resolve()
        elif (story_parent.parent / "assets").exists():
            self.base_dir = story_parent.parent
        else:
            self.base_dir = story_parent

        self.chars = CharacterRegistry(
            story["characters"],
            base_dir=self.base_dir,
        )

        self.scenes = story["scenes"]

        # Répertoire du fichier story principal — sert de base pour les goto inter-fichiers
        self._story_dir = story_parent
        self._loaded_file_keys = {str(Path(story_path).resolve())}
        self._extra_files = []  # chemins relatifs pour la sauvegarde

        self.variables = {}
        self.save_manager = SaveManager()
        self.executor = ActionExecutor()

        self.current_scene_id = None
        self._notification = ""
        self._notification_timer = 0
        self._transition = None
        self._anim_barrier = None
        self._overlays: list = []  # effets visuels superposés (GIF / MP4 / image)

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

    def _parse_goto_destination(self, destination):
        """Retourne (fichier_ou_None, scene_id_ou_None) depuis un goto."""
        if isinstance(destination, dict):
            return destination.get("file"), destination.get("scene")
        if isinstance(destination, str) and "#" in destination:
            file_part, scene_part = destination.split("#", 1)
            return file_part.strip() or None, scene_part.strip() or None
        if isinstance(destination, str) and destination.endswith((".yaml", ".yml")):
            return destination, None
        return None, destination

    def _load_extra_story(self, file_ref):
        """
        Charge un fichier YAML supplémentaire et fusionne ses personnages
        et scènes dans la partie en cours. Retourne l'id de la première scène
        (utile quand aucune scène n'est précisée dans le goto).
        """
        path = Path(file_ref)
        if not path.is_absolute():
            path = (self._story_dir / file_ref).resolve()

        key = str(path)
        if key in self._loaded_file_keys:
            # Déjà chargé : on retourne quand même la première scène du fichier
            try:
                story = load_story(path)
                return next(iter(story["scenes"]), None)
            except Exception:
                return None

        try:
            story = load_story(path)
        except Exception as err:
            print(f"[VN] Impossible de charger '{file_ref}': {err}")
            return None

        for char_id, config in story["characters"].items():
            self.chars.register(char_id, config, base_dir=self.base_dir)

        for scene_id, scene in story["scenes"].items():
            self.scenes[scene_id] = scene

        self._loaded_file_keys.add(key)
        rel = str(path.relative_to(self._story_dir.parent)
                   if path.is_relative_to(self._story_dir.parent)
                   else path)
        self._extra_files.append(rel)

        return next(iter(story["scenes"]), None)

    def _load_scene(self, scene_id):
        scene = self.scenes.get(scene_id)

        if scene is None:
            print(f"[VN] Scene not found: {scene_id}")
            self.running = False
            return

        self.current_scene_id = scene_id
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
                # Format {id: "settler", position: ...}
                if "id" in entry:
                    character_id = entry["id"]
                    position = entry.get("position")
                # Format legacy {settler: {position: ...}}
                else:
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
        self._overlays.clear()

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

                elif event.key == pygame.K_F5:
                    self._quick_save()

                elif event.key == pygame.K_F9:
                    self._quick_load()

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
        delta = self.clock.get_time()

        if self._notification_timer > 0:
            self._notification_timer -= delta
            if self._notification_timer <= 0:
                self._notification = ""
                self._notification_timer = 0

        self._tick_overlays(delta)

        if self._transition is not None:
            self._transition.tick(delta)
            if self._transition.done:
                self._transition = None
                self.executor.advance()
            return

        # Tick toutes les animations de personnages
        for char in self.chars.all():
            if char._animation is not None:
                char._animation.tick(delta)
                if char._animation.done:
                    char._animation = None

        # Animation bloquante : suspend l'exécuteur jusqu'à la fin
        if self._anim_barrier is not None:
            if self._anim_barrier.done:
                self._anim_barrier = None
                self.executor.advance()
            return

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

            self.current_text = _interpolate(
                dialogue.get("text", ""),
                self.variables,
            )

            self.executor.advance()
            self.mode = "waiting"

        elif "choice" in action:
            all_choices = action["choice"] or []
            self.choices = [
                c for c in all_choices
                if _evaluate_condition(c.get("condition", "true"), self.variables)
            ]
            self.mode = "choice"

        elif "set" in action:
            for key, value in (action["set"] or {}).items():
                self.variables[key] = _evaluate_expression(value, self.variables)

            self.executor.advance()

        elif "jump" in action or "goto" in action:
            raw = action.get("jump") or action.get("goto")
            file_ref, scene_id = self._parse_goto_destination(raw)

            if file_ref:
                first = self._load_extra_story(file_ref)
                if scene_id is None:
                    scene_id = first

            if scene_id and scene_id in self.scenes:
                self._load_scene(scene_id)
            else:
                print(f"[VN] Scène introuvable : {scene_id!r}")
                self.executor.advance()

        elif "show" in action:
            show_data = action["show"] or {}
            character_id = show_data.get("id")
            move_duration = int(show_data.get("duration", 0))

            if character_id:
                char = self.chars.get(character_id)
                old_rect = (
                    char.rect.copy()
                    if (char and char.rect and char.visible and move_duration > 0)
                    else None
                )
                self.chars.show(
                    character_id,
                    (self.W, self.H),
                    position=show_data.get("position"),
                )
                if char and old_rect is not None and char.rect:
                    anim = _create_animation(
                        "_move_to", move_duration,
                        start_x=old_rect.x, start_y=old_rect.y,
                    )
                    if anim:
                        char._animation = anim
                        if show_data.get("blocking", False):
                            self._anim_barrier = anim
                            self.executor.advance()
                            return

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

        elif "sfx" in action:
            self._play_sfx(action["sfx"])
            self.executor.advance()

        elif "stop_sfx" in action:
            pygame.mixer.stop()
            self.executor.advance()

        elif "overlay" in action:
            self._load_overlay(action["overlay"])
            self.executor.advance()

        elif "stop_overlay" in action:
            key = action["stop_overlay"]
            if key:
                self._overlays = [o for o in self._overlays if o["key"] != str(key)]
            else:
                self._overlays.clear()
            self.executor.advance()

        elif "transition" in action:
            spec = action["transition"]
            if isinstance(spec, str):
                name, duration = spec, 500
            else:
                name     = (spec or {}).get("type", "fade_black")
                duration = int((spec or {}).get("duration", 500))
            t = _create_transition(name, duration)
            if t is not None:
                self._transition = t
            else:
                print(f"[VN] Transition inconnue : {name!r}")
                self.executor.advance()

        elif "animate" in action:
            spec      = action["animate"] or {}
            char_id   = spec.get("id") or spec.get("character")
            anim_type = spec.get("name") or spec.get("type", "shake")
            duration  = int(spec.get("duration", 500))
            blocking  = spec.get("blocking", spec.get("wait", True))
            kwargs    = {
                k: v for k, v in spec.items()
                if k not in ("id", "character", "name", "type", "duration", "blocking", "wait")
            }
            anim = _create_animation(anim_type, duration, **kwargs)
            char = self.chars.get(char_id) if char_id else None
            if anim and char:
                char._animation = anim
                if blocking:
                    self._anim_barrier = anim
                    return  # executor.advance() appelé quand done
            self.executor.advance()

        elif "if" in action:
            if_data = action["if"] or {}
            condition = if_data.get("condition", "true")
            if _evaluate_condition(condition, self.variables):
                sub_actions = list(if_data.get("then") or [])
            else:
                sub_actions = list(if_data.get("else") or [])
            self.executor.advance()
            if sub_actions:
                self.executor.push(sub_actions)

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
    # Effets sonores (SFX)
    # ------------------------------------------------------------------

    def _play_sfx(self, spec):
        if not pygame.mixer.get_init():
            return
        if not spec or spec in ("stop", "none", False):
            pygame.mixer.stop()
            return
        if isinstance(spec, dict):
            path_val = spec.get("file") or spec.get("path", "")
            volume   = float(spec.get("volume", 1.0))
            loops    = -1 if spec.get("loop", False) else 0
        else:
            path_val = str(spec)
            volume   = 1.0
            loops    = 0
        try:
            path = Path(path_val)
            if not path.is_absolute():
                path = (self.base_dir / path).resolve()
            sound = pygame.mixer.Sound(str(path))
            sound.set_volume(max(0.0, min(1.0, volume)))
            channel = pygame.mixer.find_channel(True)
            if channel:
                channel.play(sound, loops=loops)
        except Exception as error:
            print(f"[SFX] {error}")

    # ------------------------------------------------------------------
    # Overlays visuels (GIF / MP4 / image statique)
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_overlay_transforms(spec):
        t_translate = None
        if "translate" in spec:
            t = spec["translate"]
            if isinstance(t, dict):
                t_translate = {
                    "dx":       int(t.get("dx", 0)),
                    "dy":       int(t.get("dy", 0)),
                    "duration": max(1, int(t.get("duration", 1000))),
                    "loop":     bool(t.get("loop", True)),
                }
        t_scale = None
        if "scale" in spec:
            s = spec["scale"]
            if isinstance(s, dict):
                t_scale = {
                    "start":    float(s.get("start", 1.0)),
                    "end":      float(s.get("end", 1.0)),
                    "duration": max(1, int(s.get("duration", 1000))),
                    "loop":     bool(s.get("loop", False)),
                }
            elif isinstance(s, (int, float)):
                # Valeur statique : taille fixe sans animation
                t_scale = {"start": float(s), "end": float(s), "duration": 1, "loop": False}
        t_rotate = None
        if "rotate" in spec:
            r = spec["rotate"]
            if isinstance(r, dict):
                t_rotate = {"speed": float(r.get("speed", 90))}
            elif isinstance(r, (int, float)):
                t_rotate = {"speed": float(r)}
        return t_translate, t_scale, t_rotate

    @staticmethod
    def _overlay_transform_progress(params, elapsed_ms):
        duration = params["duration"]
        if params.get("loop"):
            # Ping-pong : 0→1→0→1…
            cycle = (elapsed_ms / duration) % 2.0
            return cycle if cycle <= 1.0 else 2.0 - cycle
        return min(1.0, elapsed_ms / duration)

    def _load_overlay(self, spec):
        if not spec:
            return
        if isinstance(spec, str):
            spec = {"file": spec}
        path_val = spec.get("file") or spec.get("path", "")
        loop    = bool(spec.get("loop", True))
        opacity = max(0, min(255, int(spec.get("opacity", 255))))
        ox      = int(spec.get("x", 0))
        oy      = int(spec.get("y", 0))
        ow      = int(spec.get("width",  spec.get("w", 0))) or self.W
        oh      = int(spec.get("height", spec.get("h", 0))) or self.H
        t_translate, t_scale, t_rotate = self._parse_overlay_transforms(spec)

        path = Path(path_val)
        if not path.is_absolute():
            path = (self.base_dir / path).resolve()
        key = path_val

        self._overlays = [o for o in self._overlays if o["key"] != key]

        def _base(extra):
            return {
                "key": key, "loop": loop, "done": False,
                "opacity": opacity, "x": ox, "y": oy,
                "orig_w": ow, "orig_h": oh,
                "transform_elapsed": 0.0,
                "t_translate": t_translate,
                "t_scale": t_scale,
                "t_rotate": t_rotate,
                **extra,
            }

        ext = path.suffix.lower()
        if ext == ".gif":
            frames = self._load_overlay_gif(path, ow, oh)
            if frames:
                self._overlays.append(_base({
                    "type": "gif", "frames": frames, "frame_idx": 0, "elapsed": 0.0,
                }))
        elif ext in (".mp4", ".avi", ".mov", ".mkv", ".webm"):
            state = self._open_video_overlay(
                path, ow, oh, loop, opacity, ox, oy, key,
                t_translate, t_scale, t_rotate,
            )
            if state:
                self._overlays.append(state)
        else:
            try:
                surf = pygame.image.load(str(path)).convert_alpha()
                surf = pygame.transform.smoothscale(surf, (ow, oh))
                self._overlays.append(_base({
                    "type": "static", "surf": surf, "loop": False,
                }))
            except Exception as error:
                print(f"[Overlay] {error}")

    def _load_overlay_gif(self, path, w, h):
        try:
            from PIL import Image
        except ImportError:
            print("[Overlay] Installez Pillow : pip install Pillow")
            return None
        frames = []
        try:
            with Image.open(path) as image:
                for i in range(getattr(image, "n_frames", 1)):
                    image.seek(i)
                    duration = max(int(image.info.get("duration", 100)), 20)
                    rgba = image.convert("RGBA")
                    surf = pygame.image.fromstring(
                        rgba.tobytes(), rgba.size, "RGBA"
                    ).convert_alpha()
                    surf = pygame.transform.smoothscale(surf, (w, h))
                    frames.append((surf, duration))
        except Exception as error:
            print(f"[Overlay] GIF '{path}': {error}")
            return None
        return frames or None

    def _open_video_overlay(self, path, w, h, loop, opacity, ox, oy, key,
                             t_translate=None, t_scale=None, t_rotate=None):
        try:
            import cv2
        except ImportError:
            print("[Overlay] Installez opencv-python : pip install opencv-python")
            return None
        capture = cv2.VideoCapture(str(path))
        if not capture.isOpened():
            print(f"[Overlay] Impossible d'ouvrir : {path}")
            return None
        fps = capture.get(cv2.CAP_PROP_FPS) or 24
        state = {
            "key": key, "type": "video",
            "capture": capture, "frame_ms": 1000.0 / fps,
            "elapsed": 0.0, "loop": loop, "done": False,
            "opacity": opacity, "x": ox, "y": oy, "w": w, "h": h,
            "orig_w": w, "orig_h": h,
            "current_surf": None,
            "transform_elapsed": 0.0,
            "t_translate": t_translate,
            "t_scale": t_scale,
            "t_rotate": t_rotate,
        }
        self._advance_overlay_video_frame(state)
        return state

    def _advance_overlay_video_frame(self, state):
        import cv2
        capture = state["capture"]
        success, frame = capture.read()
        if not success:
            if state["loop"]:
                capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
                success, frame = capture.read()
            else:
                state["done"] = True
                return
        if not success:
            state["done"] = True
            return
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        height, width = frame_rgb.shape[:2]
        surf = pygame.image.frombuffer(
            frame_rgb.tobytes(), (width, height), "RGB"
        ).convert()
        state["current_surf"] = pygame.transform.smoothscale(surf, (state["w"], state["h"]))

    def _tick_overlays(self, delta_ms: int):
        for state in self._overlays:
            if state["done"]:
                continue
            state["transform_elapsed"] += delta_ms
            if state["type"] == "gif":
                state["elapsed"] += delta_ms
                while True:
                    _, frame_dur = state["frames"][state["frame_idx"]]
                    if state["elapsed"] < frame_dur:
                        break
                    state["elapsed"] -= frame_dur
                    next_idx = state["frame_idx"] + 1
                    if next_idx >= len(state["frames"]):
                        if state["loop"]:
                            state["frame_idx"] = 0
                        else:
                            state["done"] = True
                        break
                    state["frame_idx"] = next_idx
            elif state["type"] == "video":
                state["elapsed"] += delta_ms
                while state["elapsed"] >= state["frame_ms"] and not state["done"]:
                    state["elapsed"] -= state["frame_ms"]
                    self._advance_overlay_video_frame(state)
        self._overlays = [o for o in self._overlays if not o["done"]]

    def _render_overlays(self):
        for state in self._overlays:
            if state["done"]:
                continue
            if state["type"] == "gif":
                surf = state["frames"][state["frame_idx"]][0]
            elif state["type"] == "video":
                surf = state["current_surf"]
            else:
                surf = state.get("surf")
            if surf is None:
                continue

            telap  = state["transform_elapsed"]
            orig_w = state["orig_w"]
            orig_h = state["orig_h"]

            # -- Scale --
            if state["t_scale"]:
                s    = state["t_scale"]
                prog = self._overlay_transform_progress(s, telap)
                ease = prog * prog * (3.0 - 2.0 * prog)
                f    = s["start"] + (s["end"] - s["start"]) * ease
                surf = pygame.transform.smoothscale(
                    surf, (max(1, int(orig_w * f)), max(1, int(orig_h * f)))
                )

            # -- Rotate --
            if state["t_rotate"]:
                surf = pygame.transform.rotate(
                    surf, state["t_rotate"]["speed"] * telap / 1000.0
                )

            # -- Opacity --
            if state["opacity"] < 255:
                surf = surf.copy()
                surf.set_alpha(state["opacity"])

            # -- Position + translate (centre-based pour compenser scale/rotate) --
            cx = state["x"] + orig_w // 2
            cy = state["y"] + orig_h // 2
            if state["t_translate"]:
                t    = state["t_translate"]
                prog = self._overlay_transform_progress(t, telap)
                ease = prog * prog * (3.0 - 2.0 * prog)
                cx  += int(t["dx"] * ease)
                cy  += int(t["dy"] * ease)
            self.screen.blit(surf, surf.get_rect(center=(cx, cy)))

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
    # Sauvegarde / chargement
    # ------------------------------------------------------------------

    def _build_save_data(self):
        return {
            "scene_id": self.current_scene_id,
            "variables": dict(self.variables),
            "stack": [
                [list(actions), idx]
                for actions, idx in self.executor._stack
            ],
            "mode": self.mode,
            "current_speaker_name": self.current_speaker_name,
            "current_text": self.current_text,
            "choices": list(self.choices),
            "extra_files": list(self._extra_files),
        }

    def _restore_from_save(self, data):
        # Recharger les fichiers YAML supplémentaires avant la scène
        for rel_path in (data.get("extra_files") or []):
            self._load_extra_story(rel_path)

        scene_id = data.get("scene_id")
        if not scene_id or scene_id not in self.scenes:
            print(f"[VN] Sauvegarde invalide : scène inconnue {scene_id!r}")
            return
        self._load_scene(scene_id)
        self.executor._stack = [
            [list(actions), idx]
            for actions, idx in (data.get("stack") or [])
        ]
        self.variables = dict(data.get("variables") or {})
        self.current_speaker_name = data.get("current_speaker_name", "")
        self.current_speaker_id = self.chars.resolve_speaker(
            self.current_speaker_name
        )
        self.current_text = data.get("current_text", "")
        self.mode = data.get("mode", "running")
        self.choices = list(data.get("choices") or [])
        self._choice_rects = []

    def _quick_save(self):
        self.save_manager.save(1, self._build_save_data())
        self._notify("Partie sauvegardée  [F5]")

    def _quick_load(self):
        data = self.save_manager.load(1)
        if data is None:
            self._notify("Aucune sauvegarde trouvée")
            return
        self._restore_from_save(data)
        self._notify("Partie chargée  [F9]")

    def _notify(self, message, duration_ms=2000):
        self._notification = message
        self._notification_timer = duration_ms

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

        self._render_overlays()
        self._render_dialogue_box()

        if self.mode == "choice":
            self._render_choices()

        self._render_notification()

        if self._transition is not None:
            self._transition.render(self.screen)

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

    def _render_notification(self):
        if not self._notification:
            return
        surface = self.font_choice.render(
            self._notification,
            True,
            (100, 255, 100),
        )
        x = self.W - surface.get_width() - 20
        y = 20
        bg = pygame.Surface(
            (surface.get_width() + 16, surface.get_height() + 10),
            pygame.SRCALPHA,
        )
        bg.fill((0, 0, 0, 160))
        self.screen.blit(bg, (x - 8, y - 5))
        self.screen.blit(surface, (x, y))

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