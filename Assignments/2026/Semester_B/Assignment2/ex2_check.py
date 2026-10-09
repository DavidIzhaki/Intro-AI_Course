import time
import ext_elev
import ex2


def solve(api):
    controller = ex2.Controller(api)
    for _ in range(api.get_max_steps()):
        action = controller.choose_next_action(api.get_current_state())
        api.submit_next_action(action)
        if api.get_done():
            break
    return api.get_current_reward()


# =================================================================== #
# Base layouts (geometry + rewards). Variants below add stochastics.   #
# Each base records "optimal_a1" -- the deterministic optimal length   #
# from Assignment 1, used to scale horizons per difficulty tier.       #
# =================================================================== #

_p1 = dict(
    height=6,
    Elevators={0: (0, (0, 1, 2, 3), 8), 1: (4, (2, 4, 5, 6), 10)},
    Persons={10: (0, 3, 3), 11: (2, 4, 6), 12: (4, 5, 0)},
    persons_reward={10: [2, 3, 6, 10], 11: [1, 5, 6, 10], 12: [3, 4, 8, 12]},
    goal_reward=30,
    optimal_a1=13,
)

_e1 = dict(
    height=5,
    Elevators={0: (0, (0, 1, 2, 3, 4, 5), 15), 1: (5, (0, 1, 2, 3, 4, 5), 15)},
    Persons={10: (0, 3, 5), 11: (5, 3, 0), 12: (3, 3, 1)},
    persons_reward={10: [3, 5, 7], 11: [3, 5, 7], 12: [2, 4, 6]},
    goal_reward=20,
    optimal_a1=10,
)

_e2 = dict(
    height=6,
    Elevators={0: (0, (0, 1, 2, 3), 10), 1: (6, (3, 4, 5, 6), 10)},
    Persons={10: (1, 3, 3), 11: (5, 3, 4), 12: (0, 3, 2)},
    persons_reward={10: [2, 4, 6], 11: [1, 3, 5], 12: [2, 4, 6]},
    goal_reward=20,
    optimal_a1=11,
)

_e3 = dict(
    height=6,
    Elevators={0: (0, (0, 1, 2, 3, 4), 10), 1: (6, (2, 4, 5, 6), 10)},
    Persons={10: (0, 3, 5), 11: (6, 3, 1), 12: (3, 4, 6)},
    persons_reward={10: [3, 5, 8, 10], 11: [3, 5, 8, 10], 12: [4, 6, 8, 12]},
    goal_reward=30,
    optimal_a1=18,
)

_e4 = dict(
    height=5,
    Elevators={0: (0, (0, 1, 2, 3, 4, 5), 7), 1: (5, (0, 1, 2, 3, 4, 5), 7)},
    Persons={10: (0, 5, 5), 11: (0, 5, 3), 12: (5, 5, 0)},
    persons_reward={10: [2, 4, 6, 8], 11: [2, 4, 6, 8], 12: [2, 4, 6, 8]},
    goal_reward=20,
    optimal_a1=9,
)

_e5 = dict(
    height=7,
    Elevators={0: (0, (0, 1, 2, 3, 4), 12), 1: (7, (3, 4, 5, 6, 7), 12)},
    Persons={10: (1, 4, 3), 11: (6, 4, 7), 12: (0, 4, 7)},
    persons_reward={10: [2, 4, 6], 11: [3, 5, 7], 12: [4, 6, 8, 10]},
    goal_reward=25,
    optimal_a1=13,
)

_m1 = dict(
    height=6,
    Elevators={0: (0, (0, 1, 2, 3), 12), 1: (6, (3, 4, 5, 6), 12)},
    Persons={10: (0, 4, 5), 11: (5, 4, 0), 12: (2, 4, 6), 13: (5, 4, 1)},
    persons_reward={10: [3, 5, 8], 11: [3, 5, 8], 12: [3, 5, 8], 13: [3, 5, 8]},
    goal_reward=40,
    optimal_a1=24,
)

_m2 = dict(
    height=8,
    Elevators={0: (0, (0, 1, 2, 3, 4), 10), 1: (4, (2, 4, 6, 8), 10)},
    Persons={10: (0, 3, 8), 11: (8, 3, 0), 12: (2, 3, 6), 13: (6, 3, 1)},
    persons_reward={10: [3, 5, 7, 10], 11: [3, 5, 7, 10],
                    12: [2, 4, 6, 8],  13: [2, 4, 6, 8]},
    goal_reward=35,
    optimal_a1=21,
)

_m3 = dict(
    height=8,
    Elevators={0: (0, (0, 1, 2, 3, 4), 10),
               1: (4, (2, 4, 6, 8), 10),
               2: (4, (7, 2), 10)},
    Persons={10: (0, 3, 8), 11: (8, 3, 0), 12: (2, 3, 7), 13: (6, 3, 1)},
    persons_reward={10: [3, 5, 7, 10], 11: [3, 5, 7, 10],
                    12: [4, 6, 8, 10], 13: [2, 4, 6, 8]},
    goal_reward=35,
    optimal_a1=22,
)

_m4 = dict(
    height=6,
    Elevators={0: (0, (0, 1, 2, 3, 4, 5, 6), 8),
               1: (6, (0, 1, 2, 3, 4, 5, 6), 8)},
    Persons={10: (0, 5, 6), 11: (0, 5, 4), 12: (6, 5, 0),
             13: (6, 5, 2), 14: (3, 5, 6)},
    persons_reward={10: [2, 4, 6], 11: [2, 4, 6], 12: [2, 4, 6],
                    13: [2, 4, 6], 14: [3, 5, 7]},
    goal_reward=30,
    optimal_a1=16,
)

_m5 = dict(
    height=8,
    Elevators={0: (0, (0, 1, 2, 3, 4), 10), 1: (4, (4, 5, 6, 7, 8), 10)},
    Persons={10: (0, 6, 8), 11: (0, 4, 5), 12: (8, 6, 0), 13: (8, 5, 3)},
    persons_reward={10: [4, 6, 8, 10], 11: [3, 5, 7, 9],
                    12: [4, 6, 8, 10], 13: [3, 5, 7, 9]},
    goal_reward=40,
    optimal_a1=25,
)

# Reset-friendly: a single cheap, high-reward person makes reset-looping the
# best policy; the other persons are expensive to deliver and have tiny
# rewards; goal_reward is small so full delivery isn't the prize.
_rl = dict(
    height=2,
    Elevators={0: (0, (0, 1, 2), 6)},
    Persons={
        10: (0, 3, 1),   # cheap & lucrative (3 actions: ENTER, MOVE, EXIT)
        11: (0, 3, 2),   # farther, low reward
        12: (2, 3, 0),   # opposite corner, low reward
    },
    persons_reward={10: [50, 50], 11: [1], 12: [1]},
    goal_reward=5,
    optimal_a1=9,
)


# =================================================================== #
# Variant builders                                                     #
#   easy:   every elevator and person at 0.95, short horizon.          #
#   medium: elev 0 at 0.95 (anchor); rest of elevs 0.85-0.90;          #
#           persons 0.85-0.90; medium horizon.                         #
#   hard:   elev 0 at 0.95 (anchor); other elev(s) broken (0.25-0.4);  #
#           persons all 0.90; long horizon.                            #
# Rule: every variant has at least one entity with prob > 0.9.         #
# =================================================================== #

_HORIZON_MIN = 40
_HORIZON_MAX = 70


def _build(base, elev_p, pers_p, h_mult):
    raw_h = int(round(base["optimal_a1"] * h_mult))
    horizon = max(_HORIZON_MIN, min(_HORIZON_MAX, raw_h))
    return {
        "height": base["height"],
        "Elevators": dict(base["Elevators"]),
        "Persons": dict(base["Persons"]),
        "elevator_chosen_action_prob": elev_p,
        "person_chosen_action_prob": pers_p,
        "persons_reward": dict(base["persons_reward"]),
        "goal_reward": base["goal_reward"],
        "horizon": horizon,
    }


def _easy(base):
    elev_p = {e: 0.95 for e in base["Elevators"]}
    pers_p = {p: 0.95 for p in base["Persons"]}
    return _build(base, elev_p, pers_p, h_mult=2.0)


def _medium(base):
    elev_ids = sorted(base["Elevators"])
    elev_p = {}
    for i, e in enumerate(elev_ids):
        elev_p[e] = [0.95, 0.90, 0.85][min(i, 2)]   # first = anchor

    pers_ids = sorted(base["Persons"])
    pers_p = {p: (0.90 if i % 2 == 0 else 0.85) for i, p in enumerate(pers_ids)}
    return _build(base, elev_p, pers_p, h_mult=2.5)


def _hard(base):
    elev_ids = sorted(base["Elevators"])
    elev_p = {}
    for i, e in enumerate(elev_ids):
        if i == 0:
            elev_p[e] = 0.95                         # anchor
        else:
            elev_p[e] = [0.30, 0.40, 0.25][min(i - 1, 2)]   # broken

    pers_p = {p: 0.90 for p in base["Persons"]}
    return _build(base, elev_p, pers_p, h_mult=4.0)


# =================================================================== #
# 33 problems: 11 layouts × 3 difficulty tiers, ordered easy -> hard. #
# =================================================================== #

# ---- TIER 1: easy (all probs 0.95) ---------------------------------- #
problem_p1_easy = _easy(_p1)
problem_e1_easy = _easy(_e1)
problem_e2_easy = _easy(_e2)
problem_e3_easy = _easy(_e3)
problem_e4_easy = _easy(_e4)
problem_e5_easy = _easy(_e5)
problem_m1_easy = _easy(_m1)
problem_m2_easy = _easy(_m2)
problem_m3_easy = _easy(_m3)
problem_m4_easy = _easy(_m4)
problem_m5_easy = _easy(_m5)
problem_rl_easy = _easy(_rl)

# ---- TIER 2: medium (anchor + 0.85-0.90) ---------------------------- #
problem_p1_med  = _medium(_p1)
problem_e1_med  = _medium(_e1)
problem_e2_med  = _medium(_e2)
problem_e3_med  = _medium(_e3)
problem_e4_med  = _medium(_e4)
problem_e5_med  = _medium(_e5)
problem_m1_med  = _medium(_m1)
problem_m2_med  = _medium(_m2)
problem_m3_med  = _medium(_m3)
problem_m4_med  = _medium(_m4)
problem_m5_med  = _medium(_m5)
problem_rl_med  = _medium(_rl)

# ---- TIER 3: hard (anchor + broken elevators) ----------------------- #
problem_p1_hard = _hard(_p1)
problem_e1_hard = _hard(_e1)
problem_e2_hard = _hard(_e2)
problem_e3_hard = _hard(_e3)
problem_e4_hard = _hard(_e4)
problem_e5_hard = _hard(_e5)
problem_m1_hard = _hard(_m1)
problem_m2_hard = _hard(_m2)
problem_m3_hard = _hard(_m3)
problem_m4_hard = _hard(_m4)
problem_m5_hard = _hard(_m5)
problem_rl_hard = _hard(_rl)


PROBLEMS = [
    # easy
    ("p1_easy", problem_p1_easy),
    ("e1_easy", problem_e1_easy),
    ("e2_easy", problem_e2_easy),
    ("e3_easy", problem_e3_easy),
    ("e4_easy", problem_e4_easy),
    ("e5_easy", problem_e5_easy),
    ("m1_easy", problem_m1_easy),
    ("m2_easy", problem_m2_easy),
    ("m3_easy", problem_m3_easy),
    ("m4_easy", problem_m4_easy),
    ("m5_easy", problem_m5_easy),
    ("rl_easy", problem_rl_easy),
    # medium
    ("p1_med",  problem_p1_med),
    ("e1_med",  problem_e1_med),
    ("e2_med",  problem_e2_med),
    ("e3_med",  problem_e3_med),
    ("e4_med",  problem_e4_med),
    ("e5_med",  problem_e5_med),
    ("m1_med",  problem_m1_med),
    ("m2_med",  problem_m2_med),
    ("m3_med",  problem_m3_med),
    ("m4_med",  problem_m4_med),
    ("m5_med",  problem_m5_med),
    ("rl_med",  problem_rl_med),
    # hard
    ("p1_hard", problem_p1_hard),
    ("e1_hard", problem_e1_hard),
    ("e2_hard", problem_e2_hard),
    ("e3_hard", problem_e3_hard),
    ("e4_hard", problem_e4_hard),
    ("e5_hard", problem_e5_hard),
    ("m1_hard", problem_m1_hard),
    ("m2_hard", problem_m2_hard),
    ("m3_hard", problem_m3_hard),
    ("m4_hard", problem_m4_hard),
    ("m5_hard", problem_m5_hard),
    ("rl_hard", problem_rl_hard),
]


def main():
    n_runs = 30
    debug_mode = False

    out_file = "Solution.txt"
    with open(out_file, "a", encoding="utf-8") as f:
        f.write(f"Averages per problem (n_runs = {n_runs})\n")
        f.write("=" * 50 + "\n\n")

    for name, problem in PROBLEMS:
        total_reward = 0.0
        problem_start = time.perf_counter()

        for seed in range(n_runs):
            run_start = time.perf_counter()
            problem["seed"] = seed
            api = ext_elev.create_elevators_game(problem, debug=debug_mode)
            run_reward = solve(api)
            total_reward += run_reward
            run_time = time.perf_counter() - run_start
            print(f"[{name}] seed={seed}: reward={run_reward} time={run_time:.4f}s")

        total_time = time.perf_counter() - problem_start
        avg_reward = total_reward / n_runs
        avg_time = total_time / n_runs

        print(f"\n[{name}] avg reward over {n_runs} runs: {avg_reward:.3f} "
              f"(avg time {avg_time:.4f}s)\n")

        with open(out_file, "a", encoding="utf-8") as f:
            f.write(f"{name}: reward_average={avg_reward:.6f} | "
                    f"time_average={avg_time:.6f}s\n")


if __name__ == "__main__":
    main()
