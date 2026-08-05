import yaml
from pathlib import Path

_RESERVED = {"say", "choice", "set", "jump", "goto", "show", "hide", "background", "wait", "if", "music", "transition", "animate", "sfx", "stop_sfx", "overlay", "stop_overlay"}


def _normalize_actions(actions, char_ids):
    """Recursively convert shorthand `{char_id: "text"}` to `{say: {speaker, text}}`."""
    result = []
    for action in (actions or []):
        if not isinstance(action, dict):
            result.append(action)
            continue
        keys = set(action.keys())
        # shorthand: single key not in reserved set and matching a known character id
        if len(keys) == 1 and not (keys & _RESERVED):
            key = next(iter(keys))
            val = action[key]
            if key in char_ids and isinstance(val, str):
                result.append({"say": {"speaker": key, "text": val}})
                continue
        # recurse into choice sub-actions
        if "choice" in action:
            normalized_choices = []
            for choice in (action["choice"] or []):
                if isinstance(choice, dict) and "actions" in choice:
                    choice = dict(choice)
                    choice["actions"] = _normalize_actions(choice["actions"], char_ids)
                normalized_choices.append(choice)
            result.append({"choice": normalized_choices})
            continue
        # recurse into if then/else branches
        if "if" in action:
            if_data = dict(action["if"] or {})
            if "then" in if_data:
                if_data["then"] = _normalize_actions(if_data["then"], char_ids)
            if "else" in if_data:
                if_data["else"] = _normalize_actions(if_data["else"], char_ids)
            result.append({"if": if_data})
            continue
        result.append(action)
    return result


def load_story(path):
    """Load a YAML story file; return {"characters": dict, "scenes": dict}."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Story file not found: {path}")
    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    characters = data.get("characters") or {}
    char_ids = set(characters.keys())

    scenes_raw = data.get("scenes") or []
    scenes = {}
    for s in scenes_raw:
        sid = s.get("id")
        if not sid:
            raise ValueError("Scene missing 'id' field")
        s["actions"] = _normalize_actions(s.get("actions") or [], char_ids)
        scenes[sid] = s

    return {"characters": characters, "scenes": scenes}
