class ActionExecutor:
    """
    Exécuteur basé sur une pile pour parcourir les listes d'actions.

    La pile permet d'imbriquer des listes secondaires (branches de choix,
    blocs then/else) sans perdre la position dans la liste parente :
    on empile la sous-liste, on l'exécute jusqu'au bout, puis on dépile
    et on reprend là où on s'était arrêté.

    Structure de la pile : chaque entrée est [actions_list, current_index].
    """

    def __init__(self) -> None:
        # Each entry: [actions_list, current_index]
        self._stack: list[list] = []

    def load(self, actions: list | None) -> None:
        """Réinitialise l'exécuteur avec une nouvelle liste d'actions (vide la pile)."""
        self._stack = [[list(actions or []), 0]]

    @property
    def finished(self) -> bool:
        """True quand toutes les actions ont été exécutées."""
        self._flush_empty()
        return not self._stack

    def current(self) -> dict | None:
        """Retourne l'action en cours sans avancer le curseur."""
        self._flush_empty()
        if not self._stack:
            return None
        actions, idx = self._stack[-1]
        return actions[idx] if idx < len(actions) else None

    def advance(self) -> None:
        """Passe à l'action suivante dans la liste en haut de la pile."""
        if self._stack:
            self._stack[-1][1] += 1
        self._flush_empty()

    def push(self, actions: list | None) -> None:
        """Empile une nouvelle liste d'actions à exécuter en priorité (ex : branche d'un choix)."""
        if actions:
            self._stack.append([list(actions), 0])

    def _flush_empty(self) -> None:
        """Supprime du sommet de la pile les listes entièrement consommées."""
        while self._stack:
            actions, idx = self._stack[-1]
            if idx < len(actions):
                break
            self._stack.pop()
