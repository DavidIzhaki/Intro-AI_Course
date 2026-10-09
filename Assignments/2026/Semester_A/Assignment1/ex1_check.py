import time

import ex1
import search



def run_problem(func, targs=(), kwargs=None):
    if kwargs is None:
        kwargs = {}
    result = (-3, "default")
    try:
        result = func(*targs, **kwargs)

    except Exception as e:
        result = (-3, e)
    return result


# check_problem: problem, search_method, timeout
# timeout_exec: search_method, targs=[problem], timeout_duration=timeout
def solve_problems(problem, algorithm):
    

    try:
        p = ex1.create_watering_problem(problem)
    except Exception as e:
        print("Error creating problem: ", e)
        return None

    if algorithm == "gbfs":
        result = run_problem((lambda p: search.greedy_best_first_graph_search(p, p.h_gbfs)),targs=[p])
    else:
        result = run_problem((lambda p: search.astar_search(p, p.h_astar)), targs=[p])

    if result and isinstance(result[0], search.Node):
        solve = result[0].path()[::-1]
        solution = [pi.action for pi in solve][1:]
        print(len(solution), solution)
    else:
        print("no solution")



#Optimal : 20
Problem_pdf = {
    "Size":   (3, 3),
    "Walls":  {(0, 1), (2, 1)},
    "Taps":   {(1, 1): 6},
    "Plants": {(2, 0): 2, (0, 2): 3},
    "Robots": {10: (1, 0, 0, 2), 11: (1, 2, 0, 2)},
}

# Format reminder:
# {
#   "Size":   (N, M),
#   "Walls":  {(r,c), ...},
#   "Taps":   {(r,c): remaining_water, ...},
#   "Plants": {(r,c): required_water, ...},
#   "Robots": {rid: (r, c, load, capacity), ...}
# }

# -------------------------
# Problem 1: Tiny, no walls
# One robot, one tap, one plant
# -------------------------
#Optimal : 8
problem1 = {
    "Size":   (3, 3),
    "Walls":  set(),
    "Taps":   {(1, 1): 3},        # center
    "Plants": {(0, 2): 2},        # top-right
    "Robots": {
        10: (2, 0, 0, 2),         # bottom-left, cap 2
    },
}

# -------------------------
# Problem 2: Small with walls (your example-style)
# Two robots, one tap, two plants, vertical walls
# -------------------------
#Optimal: 20
problem2 = {
    "Size":  (3, 3),
    "Walls": {(0, 1), (2, 1)},    # middle column walls in top & bottom rows
    "Taps":  {(1, 1): 6},         # center
    "Plants": {
        (0, 2): 3,                # top-right
        (2, 0): 2,                # bottom-left
    },
    "Robots": {
        10: (1, 0, 0, 2),         # middle-left
        11: (1, 2, 0, 2),         # middle-right
    },
}




# -------------------------
# Problem 3: Corridor with walls, 5x3, one robot shuttling
# -------------------------
#optimal: 28
problem3 = {
    "Size":  (5, 3),              # rows: 0..4, cols: 0..2
    "Walls": {(1, 1), (3, 1)},    # walls in the middle column
    "Taps": {
        (0, 0): 5,                # top-left
    },
    "Plants": {
        (4, 2): 4,                # bottom-right
    },
    "Robots": {
        10: (2, 0, 0, 2),         # middle-left, cap 2 → needs multiple trips
    },
}

# -------------------------
# Problem 4
# -------------------------
#optimal: 13
problem4 = {
    "Size":  (5, 5),
    "Walls": {(0, 1),(1, 1),(2, 1), (0, 3),(1, 3),(2, 3)},    # two blocked cells
    "Taps": {
        (3, 2): 1,                # top-left
        (4, 2): 1,                # bottom-right
    },
    "Plants": {
        (0, 2): 1,                # top-right
        (1, 2): 1,                # bottom-left
                        # somewhere in middle-left
    },
    "Robots": {
        10: (3, 1, 0, 1),         # near left side
        11: (3, 3, 0, 1),         # near right side
    },
}

# -------------------------
# Problem 5: Intentional dead-end (not enough water)
# Good to test your dead-end pruning
# -------------------------
problem5_deadend = {
    "Size":  (3, 4),
    "Walls": set(),
    "Taps": {
        (1, 1): 3,                # only 3 units in world
    },
    "Plants": {
        (0, 3): 2,
        (2, 3): 2,                # total need = 4 > 3 → impossible
    },
    "Robots": {
        10: (1, 0, 0, 2),
    },
}
# -------------------------
# Problem 6:
# -------------------------
#optimal: 8
problem6 = {
    "Size":  (8, 8),
    "Walls": {
        # All cells except the corridor (1,0), (1,1), (1,2)
        *( (r, c)
           for r in range(8)
           for c in range(8)
           if not (r == 1 and c in (0, 1, 2)) )
    },
    "Taps": {
        (1, 1): 3,
    },
    "Plants": {
        (1, 2): 3,
    },
    "Robots": {
        10: (1, 0, 0, 3),   # start left of tap, cap 3
    },
}
#optimal: 20
problem7 = {
    "Size":  (4, 4),

    "Walls": set(),  # everything open

    "Taps": {
        (2, 2): 18,       # center tap
    },

    "Plants": {
        (0, 3): 3,        # top-right
        (3, 0): 3,        # bottom-left
        # total need = 8, tap has 18 (some slack)
    },

    "Robots": {
        10: (2, 1, 0, 3),  # left of tap, capacity 3
        11: (2, 0, 0, 3),  # right of tap, capacity 3
    },
}






def main():
    start = time.time()
    problem = []
    for p in problem:
        for a in ['astar','gbfs']:
            solve_problems(p, a)
    end = time.time()
    print('Submission took:', end-start, 'seconds.')


if __name__ == '__main__':
    main()
