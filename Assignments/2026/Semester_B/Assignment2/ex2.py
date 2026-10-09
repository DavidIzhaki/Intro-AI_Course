import ext_elev

id = ["000000000"]


class Controller:
    """Stochastic multi-elevator controller.

    Implement choose_next_action(state) to return a single legal action
    string. See the assignment PDF (Section 5) for the full API contract
    and the engine-access policy.
    """

    def __init__(self, game: ext_elev.GameAPI):
        self.game = game
        # Initialize precomputations, caches, etc. here.

    def choose_next_action(self, state):
        """Return one of:
            "MOVE{e,f}", "ENTER{p,e}", "EXIT{p,e}", "RESET"

        Input:
            state = (elevators_t, persons_t, total_persons_remaining)
        """
        raise NotImplementedError
