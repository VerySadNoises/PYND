class ActionExecutor:
    """Stack-based executor allowing inline nested action lists (e.g. choice sub-trees)."""

    def __init__(self):
        self._stack = []  # each entry: [actions_list, index]

    def load(self, actions):
        self._stack = [[list(actions or []), 0]]

    @property
    def finished(self):
        self._flush_empty()
        return not self._stack

    def current(self):
        self._flush_empty()
        if not self._stack:
            return None
        actions, idx = self._stack[-1]
        return actions[idx] if idx < len(actions) else None

    def advance(self):
        if self._stack:
            self._stack[-1][1] += 1
        self._flush_empty()

    def push(self, actions):
        if actions:
            self._stack.append([list(actions), 0])

    def _flush_empty(self):
        while self._stack:
            actions, idx = self._stack[-1]
            if idx < len(actions):
                break
            self._stack.pop()
