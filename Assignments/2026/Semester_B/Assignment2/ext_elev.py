import re
import numpy as np
from types import MappingProxyType
from pprint import pprint


def _parse_action(s):
    """Parse 'MOVE{e,f}', 'ENTER{p,e}', 'EXIT{p,e}', or 'RESET'."""
    if s == "RESET":
        return ("RESET",)
    m = re.fullmatch(r"\s*(MOVE|ENTER|EXIT)\s*\{\s*(-?\d+)\s*,\s*(-?\d+)\s*\}\s*", s)
    if not m:
        raise ValueError(f"Bad action format: {s!r}")
    return (m.group(1), int(m.group(2)), int(m.group(3)))


class Game:
    """Internal engine for the stochastic multi-elevator MDP.

    Students never see this class directly. The grader wraps it in a
    GameAPI and passes only the wrapper to the student's Controller.
    """

    def __init__(self, problem, debug=False):
        self._debug = debug
        self._history = [] if debug else None

        self._max_steps = int(problem["horizon"])
        self._goal_reward = float(problem["goal_reward"])
        self._height = int(problem["height"])

        # private RNG, name-mangled and never exposed via the API
        self.__rng = np.random.default_rng(problem["seed"])

        # read-only static configuration (MappingProxyType blocks __setitem__)
        self._capacities = MappingProxyType({
            eid: capacity
            for eid, (_, _, capacity) in problem["Elevators"].items()
        })
        self._reachable = MappingProxyType({
            eid: frozenset(reachable)
            for eid, (_, reachable, _) in problem["Elevators"].items()
        })

        self._person_weight = MappingProxyType({
            pid: weight
            for pid, (_, weight, _) in problem["Persons"].items()
        })
        self._person_goal = MappingProxyType({
            pid: goal
            for pid, (_, _, goal) in problem["Persons"].items()
        })

        self._elevator_action_prob = MappingProxyType(
            dict(problem["elevator_chosen_action_prob"])
        )
        self._person_action_prob = MappingProxyType(
            dict(problem["person_chosen_action_prob"])
        )
        self._persons_reward = MappingProxyType({
            pid: tuple(rewards)
            for pid, rewards in problem["persons_reward"].items()
        })

        # initial state
        elevators_t = tuple(sorted(
            (eid, floor, 0)
            for eid, (floor, _, _) in problem["Elevators"].items()
        ))
        persons_t = tuple(sorted(
            (pid, ('floor', start))
            for pid, (start, _, _) in problem["Persons"].items()
        ))
        total_remaining = len(persons_t)

        self._initial_state = (elevators_t, persons_t, total_remaining)
        self._state = self._initial_state

        self._steps = 0
        self._reward = 0.0
        self._done = False

    # ---------------------------------------------------------------- #
    # Action handling                                                  #
    # ---------------------------------------------------------------- #
    def submit_next_action(self, chosen_action):
        if self._done:
            return

        if chosen_action == "RESET":
            self._state = self._initial_state
            self._steps += 1
            self._log(f"step {self._steps}, action: RESET")
            if self._steps >= self._max_steps:
                self._done = True
            return

        parsed = _parse_action(chosen_action)
        name = parsed[0]

        if name == "MOVE":
            _, e_id, target_f = parsed
            self._apply_move(e_id, target_f, chosen_action)
        elif name == "ENTER":
            _, p_id, e_id = parsed
            self._apply_enter(p_id, e_id, chosen_action)
        elif name == "EXIT":
            _, p_id, e_id = parsed
            self._apply_exit(p_id, e_id, chosen_action)
        else:
            raise ValueError(f"Unknown action {name!r}")

        self._steps += 1
        if self._steps >= self._max_steps:
            self._done = True

    # ---------------------------------------------------------------- #
    # Internal helpers                                                 #
    # ---------------------------------------------------------------- #
    def _find_elevator(self, e_id):
        for i, (eid, fl, w) in enumerate(self._state[0]):
            if eid == e_id:
                return i, fl, w
        raise ValueError(f"Elevator {e_id} not in state")

    def _find_person(self, p_id):
        for i, (pid, loc) in enumerate(self._state[1]):
            if pid == p_id:
                return i, loc
        raise ValueError(f"Person {p_id} not in state")

    def _apply_move(self, e_id, target_f, action_str):
        elevators_t, persons_t, total_remaining = self._state

        if e_id not in self._reachable:
            raise ValueError(f"Unknown elevator {e_id}")
        if target_f not in self._reachable[e_id]:
            raise ValueError(
                f"Illegal MOVE{{{e_id},{target_f}}}: "
                f"floor {target_f} not in reachable {set(self._reachable[e_id])}"
            )

        e_idx, cur_f, cur_w = self._find_elevator(e_id)
        # Self-loops (target_f == cur_f) are permitted: success stays in place;
        # failure picks uniformly from F_e (which may or may not equal cur_f).

        p_succ = self._elevator_action_prob[e_id]
        if self.__rng.random() < p_succ:
            new_f = target_f
            outcome = "SUCCESS"
        else:
            # uniform over {cur_f} ∪ (F_e \ {target_f})
            options = sorted({cur_f} | (set(self._reachable[e_id]) - {target_f}))
            new_f = int(options[int(self.__rng.integers(0, len(options)))])
            outcome = f"FAIL->{new_f}"

        elevators = list(elevators_t)
        elevators[e_idx] = (e_id, new_f, cur_w)
        # persons inside this elevator keep loc=('in', e_id), no update needed
        self._state = (tuple(sorted(elevators)), persons_t, total_remaining)

        self._log(f"step {self._steps + 1}, action: {action_str}, outcome: {outcome}")

    def _apply_enter(self, p_id, e_id, action_str):
        elevators_t, persons_t, total_remaining = self._state

        if e_id not in self._capacities:
            raise ValueError(f"Unknown elevator {e_id}")
        if p_id not in self._person_weight:
            raise ValueError(f"Unknown person {p_id}")

        p_idx, p_loc = self._find_person(p_id)
        e_idx, cur_f, cur_w = self._find_elevator(e_id)

        if not (isinstance(p_loc, tuple) and p_loc[0] == 'floor'):
            raise ValueError(
                f"Illegal ENTER{{{p_id},{e_id}}}: person {p_id} is already inside an elevator"
            )
        if p_loc[1] != cur_f:
            raise ValueError(
                f"Illegal ENTER{{{p_id},{e_id}}}: person on floor {p_loc[1]}, "
                f"elevator on floor {cur_f}"
            )
        if cur_w + self._person_weight[p_id] > self._capacities[e_id]:
            raise ValueError(
                f"Illegal ENTER{{{p_id},{e_id}}}: capacity "
                f"{self._capacities[e_id]} exceeded"
            )

        p_succ = self._person_action_prob[p_id]
        if self.__rng.random() < p_succ:
            elevators = list(elevators_t)
            persons = list(persons_t)
            elevators[e_idx] = (e_id, cur_f, cur_w + self._person_weight[p_id])
            persons[p_idx] = (p_id, ('in', e_id))
            self._state = (
                tuple(sorted(elevators)),
                tuple(sorted(persons)),
                total_remaining,
            )
            outcome = "SUCCESS"
        else:
            outcome = "FAIL"

        self._log(f"step {self._steps + 1}, action: {action_str}, outcome: {outcome}")

    def _apply_exit(self, p_id, e_id, action_str):
        elevators_t, persons_t, total_remaining = self._state

        if e_id not in self._capacities:
            raise ValueError(f"Unknown elevator {e_id}")
        if p_id not in self._person_weight:
            raise ValueError(f"Unknown person {p_id}")

        p_idx, p_loc = self._find_person(p_id)
        e_idx, cur_f, cur_w = self._find_elevator(e_id)

        if not (isinstance(p_loc, tuple) and p_loc[0] == 'in' and p_loc[1] == e_id):
            raise ValueError(
                f"Illegal EXIT{{{p_id},{e_id}}}: person {p_id} not inside elevator {e_id}"
            )

        p_succ = self._person_action_prob[p_id]
        outcome = "FAIL"
        if self.__rng.random() < p_succ:
            elevators = list(elevators_t)
            elevators[e_idx] = (e_id, cur_f, cur_w - self._person_weight[p_id])

            if cur_f == self._person_goal[p_id]:
                # delivered: sample reward, drop person from state
                rewards = self._persons_reward[p_id]
                sampled = int(rewards[int(self.__rng.integers(0, len(rewards)))])
                self._reward += sampled

                new_persons = tuple(sorted(
                    (pid, loc) for (pid, loc) in persons_t if pid != p_id
                ))
                new_remaining = total_remaining - 1
                outcome = f"DELIVERED reward={sampled}"

                if new_remaining == 0:
                    # global goal reached: add goal_reward, reset to initial
                    self._reward += self._goal_reward
                    self._state = self._initial_state
                    outcome += f" + GOAL goal_reward={self._goal_reward}"
                else:
                    self._state = (tuple(sorted(elevators)), new_persons, new_remaining)
            else:
                persons = list(persons_t)
                persons[p_idx] = (p_id, ('floor', cur_f))
                self._state = (
                    tuple(sorted(elevators)),
                    tuple(sorted(persons)),
                    total_remaining,
                )
                outcome = "SUCCESS"

        self._log(f"step {self._steps + 1}, action: {action_str}, outcome: {outcome}")

    def _log(self, line):
        if self._history is not None:
            self._history.append(line)

    def show_history(self):
        if self._history is not None:
            print("History:")
            pprint(self._history)


class GameAPI:
    """Public-facing wrapper around Game.

    This is the ONLY class your controller is allowed to interact with.
    See the assignment PDF, Section 5, for the engine-access policy.
    Any attempt to reach into the underlying Game object (e.g. via
    _GameAPI__game, vars(), __dict__, ...) is forbidden and will result
    in a grade of zero.
    """

    def __init__(self, game):
        self.__game = game

    # ---- state ----
    def get_current_state(self):
        return self.__game._state

    def get_initial_state(self):
        return self.__game._initial_state

    # ---- progress / horizon / reward ----
    def get_done(self):
        return self.__game._done

    def get_current_steps(self):
        return self.__game._steps

    def get_max_steps(self):
        return self.__game._max_steps

    def get_current_reward(self):
        return self.__game._reward

    def get_goal_reward(self):
        return self.__game._goal_reward

    # ---- stochastics ----
    def get_elevator_action_prob(self, e):
        return self.__game._elevator_action_prob[e]

    def get_person_action_prob(self, p):
        return self.__game._person_action_prob[p]

    def get_person_reward(self, p):
        return tuple(self.__game._persons_reward[p])

    # ---- static person info ----
    def get_person_weight(self, p):
        return self.__game._person_weight[p]

    def get_person_goal(self, p):
        return self.__game._person_goal[p]

    # ---- static elevator info ----
    def get_capacities(self):
        return dict(self.__game._capacities)

    def get_reachable(self):
        return dict(self.__game._reachable)

    # ---- action submission ----
    def submit_next_action(self, chosen_action):
        return self.__game.submit_next_action(chosen_action)

    # ---- debug ----
    def show_history(self):
        return self.__game.show_history()


def create_elevators_game(problem, debug=False):
    """Factory: build a Game and wrap it in a GameAPI for student use."""
    if debug:
        print("-------- DEBUG MODE --------")
        print("<< create_elevators_game >>")
        pprint(problem)
    return GameAPI(Game(problem, debug=debug))
