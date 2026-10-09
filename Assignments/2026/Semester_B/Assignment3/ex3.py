import ext_elev

id = ["000000000"]


class Controller:
    """Reinforcement-learning multi-elevator controller.

    The model is HIDDEN: the elevator/person success probabilities and the
    per-person reward lists are unknown and cannot be queried. You learn
    about the world only by acting and observing the consequences -- in
    particular via api.get_last_gained_reward() after each action.

    Implement choose_next_action(state) to return a single legal action
    string. See the assignment PDF (Section "Engine API") for the full API
    contract and the engine-access policy.
    """

    def __init__(self, game: ext_elev.GameAPI):
        self.game = game
        # Initialize your learned estimates (success counts, observed
        # rewards, ...), caches, etc. here. They should persist across
        # calls to choose_next_action so you can learn over the horizon.

    def choose_next_action(self, state):
        """Return one of:
            "MOVE{e,f}", "ENTER{p,e}", "EXIT{p,e}", "RESET"

        Input:
            state = (elevators_t, persons_t, total_persons_remaining)
        """
        raise NotImplementedError
