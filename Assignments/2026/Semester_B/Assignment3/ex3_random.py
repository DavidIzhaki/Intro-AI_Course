import ext_elev
import numpy as np

id = ["000000000"]


class Controller:
    """Random baseline controller for the multi-elevator MDP (RL setting).

    Picks uniformly at random from the legal actions. Self-loop MOVEs are
    excluded so the baseline doesn't waste steps trivially. This is the
    policy you must beat to receive a passing grade.
    """

    def __init__(self, game: ext_elev.GameAPI):
        self.game = game
        self.reachable = self.game.get_reachable()
        self.capacities = self.game.get_capacities()

    def choose_next_action(self, state):
        elevators_t, persons_t, _ = state

        actions = ["RESET"]

        # MOVE{e, f}: f in reachable[e], f != current floor
        for (eid, cur_f, _) in elevators_t:
            for f in self.reachable[eid]:
                if f != cur_f:
                    actions.append(f"MOVE{{{eid},{f}}}")

        # ENTER{p, e}: person on same floor as elevator, capacity not exceeded
        for (pid, loc) in persons_t:
            if not (isinstance(loc, tuple) and loc[0] == 'floor'):
                continue
            f_p = loc[1]
            w_p = self.game.get_person_weight(pid)
            for (eid, cur_f, cur_w) in elevators_t:
                if cur_f != f_p:
                    continue
                if cur_w + w_p > self.capacities[eid]:
                    continue
                actions.append(f"ENTER{{{pid},{eid}}}")

        # EXIT{p, e}: person currently inside elevator e
        for (pid, loc) in persons_t:
            if not (isinstance(loc, tuple) and loc[0] == 'in'):
                continue
            eid = loc[1]
            actions.append(f"EXIT{{{pid},{eid}}}")

        return str(np.random.choice(actions))
