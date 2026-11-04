"""Local self-checker. Choose what to run on the command line:

    python ex1_check.py                 what RUN below says (all the problems, unless you change it)
    python ex1_check.py all             all the problems
    python ex1_check.py X               one set: X (the easy set in the pdf), Y (the hard set) or examples
    python ex1_check.py x3              one problem
    python ex1_check.py p1 x3 y2        problems of your choice; you can mix in sets too
    python ex1_check.py --list          the names of all the problems

    python ex1_check.py x3 --plan       also print the plan
    python ex1_check.py X --limit 60    another time limit, in seconds

You may add problems of your own to SETS, best in a set of your own, so that the points of X and Y stay right:
    "mine": {"m1": (init_state_m1, None)},      with None if you do not know the optimal cost
Then run them with: python ex1_check.py mine

Each problem runs in its own process with a time limit, like in grading.
The plan is checked by the rules in World below, which do not use your code.
"""
import argparse
import multiprocessing
import os
import re
import sys
import threading
import time
import traceback

RUN = ["all"]       # what runs when you give no arguments, for example ["X"] or ["p1", "x3"]
TIME_LIMIT = 30     # seconds for each problem, including the constructor of your problem class
POINTS = {"X": 5, "Y": 5}
SAIL_COST = 3       # every other action costs 1
NUMBER = "(?:0|-?[1-9][0-9]*)"     # as str(int) writes it: IDs must not change, so no leading zeros
ACTION = re.compile(rf"(DRIVE|LOAD|UNLOAD|BOARD|SAIL|DISEMBARK)\{{({NUMBER}(?:,{NUMBER})+)\}}")

# Format reminder:
# {
#   "Locations": number,
#   "Roads":     {(a, b), ...},
#   "Ports":     {location, ...},
#   "Trucks":    {tid: (location, max_weight), ...},
#   "Ferries":   {fid: (port, served_ports, max_trucks), ...},
#   "Packages":  {pid: (start_location, weight, goal_location), ...},
# }

# ---------- Set examples ----------

#Optimal: 6
# P2: the road (4 drives) is cheaper than the ferry (board + sail + disembark)
init_state_p2 = {
    "Locations": 5,
    "Roads": {(0, 1), (1, 2), (2, 3), (3, 4)},
    "Ports": {0, 4},
    "Trucks": {
        10: (0, 5)
    },
    "Ferries": {
        20: (0, (0, 4), 1)
    },
    "Packages": {
        30: (0, 1, 4)
    }
}

# ---------- Set X ----------

#Optimal: 26
# P1: the example from the pdf file, two islands connected by one ferry
init_state_p1 = {
    "Locations": 6,
    "Roads": {(0, 1), (1, 2), (3, 4), (4, 5)},
    "Ports": {2, 3},
    "Trucks": {
        10: (0, 10),
        11: (5, 6)
    },
    "Ferries": {
        20: (2, (2, 3), 1)
    },
    "Packages": {
        30: (0, 7, 5),
        31: (1, 4, 2),
        32: (4, 5, 0)
    }
}

#Optimal: 20
init_state_p3 = {
    "Locations": 9,
    "Roads": {(0, 1), (0, 3), (0, 5), (0, 7), (1, 2), (3, 4), (5, 6), (7, 8)},
    "Ports": set(),
    "Trucks": {
        10: (2, 2),
        11: (4, 2)
    },
    "Ferries": {},
    "Packages": {
        30: (2, 1, 8),
        31: (2, 1, 6),
        32: (4, 1, 6),
        33: (4, 1, 8)
    }
}

#Optimal: 49
init_state_x1 = {
    "Locations": 8,
    "Roads": {(0, 1), (1, 2), (3, 4), (4, 5), (6, 7)},
    "Ports": {0, 2, 3, 5, 6, 7},
    "Trucks": {
        10: (7, 8),
        11: (4, 3)
    },
    "Ferries": {
        20: (2, (2, 3), 1),
        21: (6, (5, 6), 1),
        22: (7, (7, 0), 1)
    },
    "Packages": {
        30: (2, 7, 6),
        31: (3, 7, 1),
        32: (2, 3, 7),
        33: (2, 3, 4)
    }
}

#Optimal: 30
init_state_x2 = {
    "Locations": 11,
    "Roads": {(0, 1), (0, 3), (0, 5), (0, 7), (0, 9), (1, 2), (3, 4), (5, 6), (7, 8), (9, 10)},
    "Ports": set(),
    "Trucks": {
        10: (2, 3),
        11: (4, 3)
    },
    "Ferries": {},
    "Packages": {
        30: (2, 1, 6),
        31: (2, 1, 8),
        32: (2, 1, 10),
        33: (4, 1, 6),
        34: (4, 1, 8),
        35: (4, 1, 10)
    }
}

#Optimal: 42
init_state_x3 = {
    "Locations": 8,
    "Roads": {(0, 1), (2, 3), (4, 5), (6, 7)},
    "Ports": {0, 1, 2, 3, 4, 5, 6, 7},
    "Trucks": {
        10: (0, 5),
        11: (2, 5),
        12: (4, 5)
    },
    "Ferries": {
        20: (1, (1, 2), 1),
        21: (3, (3, 4), 1),
        22: (5, (5, 6), 1),
        23: (7, (7, 0), 1)
    },
    "Packages": {
        30: (0, 5, 4),
        31: (2, 5, 6),
        32: (4, 5, 0)
    }
}

#Optimal: 38
init_state_x4 = {
    "Locations": 17,
    "Roads": {(0, 1), (0, 4), (0, 7), (0, 10), (1, 2), (2, 3), (4, 5), (5, 6), (7, 8), (8, 9), (10, 11), (11, 12), (13, 14), (15, 16)},
    "Ports": {0, 13, 14, 15},
    "Trucks": {
        10: (3, 4),
        11: (6, 4),
        12: (9, 4),
        13: (12, 4)
    },
    "Ferries": {
        20: (0, (0, 13), 1),
        21: (14, (14, 15), 1)
    },
    "Packages": {
        30: (3, 1, 16),
        31: (6, 1, 16),
        32: (9, 1, 16),
        33: (12, 1, 16)
    }
}

#Optimal: 34
init_state_x5 = {
    "Locations": 9,
    "Roads": {(0, 1), (0, 3), (1, 2), (1, 4), (2, 5), (3, 4), (3, 6), (4, 5), (4, 7), (5, 8), (6, 7), (7, 8)},
    "Ports": set(),
    "Trucks": {
        10: (0, 1),
        11: (8, 1)
    },
    "Ferries": {},
    "Packages": {
        30: (0, 1, 8),
        31: (8, 1, 0),
        32: (2, 1, 6),
        33: (6, 1, 2),
        34: (1, 1, 7),
        35: (7, 1, 1)
    }
}

#Optimal: 32
init_state_x6 = {
    "Locations": 11,
    "Roads": {(0, 1), (1, 2), (2, 3), (3, 6), (3, 7), (4, 5), (5, 6), (7, 8), (8, 9), (9, 10)},
    "Ports": set(),
    "Trucks": {
        10: (0, 1),
        11: (4, 1),
        12: (3, 4)
    },
    "Ferries": {},
    "Packages": {
        30: (0, 1, 10),
        31: (4, 1, 10),
        32: (3, 2, 10),
        33: (7, 1, 9),
        34: (1, 1, 10)
    }
}

#Optimal: 57
init_state_x7 = {
    "Locations": 6,
    "Roads": {(0, 1), (2, 3), (4, 5)},
    "Ports": {1, 2, 3, 4},
    "Trucks": {
        10: (0, 4),
        11: (0, 4),
        12: (0, 4)
    },
    "Ferries": {
        20: (1, (1, 2), 1),
        21: (3, (3, 4), 1)
    },
    "Packages": {
        30: (0, 4, 5),
        31: (0, 4, 5),
        32: (0, 4, 5)
    }
}

#Optimal: 44
init_state_x8 = {
    "Locations": 5,
    "Roads": {(0, 1), (1, 2), (2, 3), (3, 4)},
    "Ports": set(),
    "Trucks": {
        10: (0, 3)
    },
    "Ferries": {},
    "Packages": {
        30: (0, 3, 4),
        31: (0, 2, 4),
        32: (0, 2, 4),
        33: (0, 1, 4),
        34: (0, 1, 4),
        35: (0, 1, 4),
        36: (0, 1, 4),
        37: (0, 1, 4)
    }
}

# ---------- Set Y ----------

#Optimal: 48
init_state_y1 = {
    "Locations": 21,
    "Roads": {(0, 1), (0, 3), (0, 5), (0, 7), (0, 9), (1, 2), (3, 4), (5, 6), (7, 8), (9, 10), (11, 12), (11, 15), (11, 18), (12, 13), (13, 14), (15, 16), (16, 17), (18, 19), (19, 20)},
    "Ports": set(),
    "Trucks": {
        10: (2, 3),
        11: (4, 3),
        12: (14, 2),
        13: (17, 2),
        14: (20, 2)
    },
    "Ferries": {},
    "Packages": {
        300: (2, 1, 6),
        301: (2, 1, 8),
        302: (4, 1, 8),
        303: (4, 1, 10),
        304: (14, 1, 12),
        305: (13, 1, 11),
        306: (12, 1, 14),
        307: (17, 1, 15),
        308: (16, 1, 11),
        309: (20, 1, 18),
        310: (19, 1, 11)
    }
}

#Optimal: 53
init_state_y2 = {
    "Locations": 12,
    "Roads": set(),
    "Ports": {0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11},
    "Trucks": {
        10: (1, 3),
        11: (3, 3),
        12: (5, 3)
    },
    "Ferries": {
        20: (0, (0, 1, 2), 1),
        21: (2, (2, 3, 4), 1),
        22: (4, (0, 4, 5), 1),
        23: (0, (0, 6), 1),
        24: (1, (1, 7), 1),
        25: (2, (2, 8), 1),
        26: (3, (3, 9), 1),
        27: (4, (4, 10), 1),
        28: (5, (5, 11), 1)
    },
    "Packages": {
        30: (1, 2, 3),
        31: (3, 2, 5),
        32: (5, 2, 1),
        33: (1, 1, 5),
        34: (3, 1, 1)
    }
}

#Optimal: 96
init_state_y3 = {
    "Locations": 65,
    "Roads": {(0, 4), (0, 6), (0, 20), (1, 8), (1, 10), (1, 34), (1, 35), (2, 12), (2, 14), (2, 49), (2, 50), (3, 16), (3, 18), (3, 64), (4, 5), (6, 7), (8, 9), (10, 11), (12, 13), (14, 15), (16, 17), (18, 19), (20, 21), (21, 22), (22, 23), (23, 24), (24, 25), (25, 26), (26, 27), (27, 28), (28, 29), (29, 30), (30, 31), (31, 32), (32, 33), (33, 34), (35, 36), (36, 37), (37, 38), (38, 39), (39, 40), (40, 41), (41, 42), (42, 43), (43, 44), (44, 45), (45, 46), (46, 47), (47, 48), (48, 49), (50, 51), (51, 52), (52, 53), (53, 54), (54, 55), (55, 56), (56, 57), (57, 58), (58, 59), (59, 60), (60, 61), (61, 62), (62, 63), (63, 64)},
    "Ports": set(),
    "Trucks": {
        10: (5, 3),
        11: (9, 3),
        12: (13, 3)
    },
    "Ferries": {},
    "Packages": {
        30: (5, 1, 11),
        31: (9, 1, 15),
        32: (13, 1, 19),
        33: (5, 1, 19),
        34: (9, 1, 19),
        35: (5, 1, 15)
    }
}

#Optimal: 71
init_state_y4 = {
    "Locations": 17,
    "Roads": {(1, 9), (2, 11), (3, 13), (4, 15), (5, 10), (6, 12), (7, 14), (8, 16), (9, 10), (11, 12), (13, 14), (15, 16)},
    "Ports": {0, 1, 2, 3, 4},
    "Trucks": {
        10: (1, 4),
        11: (4, 4),
        12: (2, 4)
    },
    "Ferries": {
        20: (1, (0, 1, 2, 3, 4), 1),
        21: (4, (0, 1, 2, 3, 4), 1)
    },
    "Packages": {
        30: (5, 2, 6),
        31: (6, 2, 7),
        32: (7, 2, 8),
        33: (8, 2, 5),
        34: (6, 2, 5),
        35: (8, 2, 7)
    }
}

#Optimal: 48
init_state_y5 = {
    "Locations": 10,
    "Roads": {(0, 1), (2, 3), (4, 5), (6, 7), (8, 9)},
    "Ports": {0, 1, 2, 3, 4, 5, 6, 7, 8, 9},
    "Trucks": {
        10: (0, 5),
        11: (2, 5),
        12: (4, 5)
    },
    "Ferries": {
        20: (1, (1, 2), 1),
        21: (3, (3, 4), 1),
        22: (5, (5, 6), 1),
        23: (7, (7, 8), 1),
        24: (9, (0, 9), 1)
    },
    "Packages": {
        30: (0, 5, 4),
        31: (2, 5, 6),
        32: (4, 5, 8)
    }
}

#Optimal: 57
init_state_y6 = {
    "Locations": 7,
    "Roads": {(1, 2), (3, 4), (5, 6)},
    "Ports": {0, 1, 3, 5},
    "Trucks": {
        10: (0, 3),
        11: (0, 3),
        12: (2, 3),
        13: (4, 3)
    },
    "Ferries": {
        200: (0, (0, 1, 3, 5), 1),
        201: (0, (0, 1, 3, 5), 1),
        202: (0, (0, 1, 3, 5), 1),
        203: (0, (0, 1, 3, 5), 1)
    },
    "Packages": {
        300: (0, 2, 2),
        301: (0, 2, 4),
        302: (0, 2, 6),
        303: (2, 2, 4),
        304: (4, 2, 6),
        305: (6, 2, 2)
    }
}

#Optimal: 60
init_state_y7 = {
    "Locations": 10,
    "Roads": {(0, 1), (1, 2), (3, 4), (4, 5), (6, 7), (7, 8), (7, 9)},
    "Ports": {0, 2, 3, 5, 6},
    "Trucks": {
        10: (5, 3),
        11: (2, 4),
        12: (5, 4)
    },
    "Ferries": {
        20: (0, (0, 2, 3), 1),
        21: (5, (5, 6), 2)
    },
    "Packages": {
        30: (0, 3, 1),
        31: (2, 4, 6),
        32: (2, 2, 6),
        33: (4, 2, 9),
        34: (7, 2, 9),
        35: (2, 2, 7)
    }
}

# Each problem is name: (initial state, optimal cost)
SETS = {
    "examples": {
        "p2": (init_state_p2, 6),
    },
    "X": {
        "p1": (init_state_p1, 26),
        "p3": (init_state_p3, 20),
        "x1": (init_state_x1, 49),
        "x2": (init_state_x2, 30),
        "x3": (init_state_x3, 42),
        "x4": (init_state_x4, 38),
        "x5": (init_state_x5, 34),
        "x6": (init_state_x6, 32),
        "x7": (init_state_x7, 57),
        "x8": (init_state_x8, 44),
    },
    "Y": {
        "y1": (init_state_y1, 48),
        "y2": (init_state_y2, 53),
        "y3": (init_state_y3, 96),
        "y4": (init_state_y4, 71),
        "y5": (init_state_y5, 48),
        "y6": (init_state_y6, 57),
        "y7": (init_state_y7, 60),
    },
}


class IllegalAction(Exception):
    pass


class World:
    """The rules of the domain, written apart from any solution. apply() changes the world or raises IllegalAction."""

    def __init__(self, game):
        self.game = game
        self.roads = {frozenset(road) for road in game["Roads"]}
        self.truck_at = {t: location for t, (location, _) in game["Trucks"].items()}    # None while aboard a ferry
        self.truck_on = dict.fromkeys(game["Trucks"])                                   # the ferry, or None
        self.ferry_at = {f: port for f, (port, _, _) in game["Ferries"].items()}
        self.package_at = {p: start for p, (start, _, _) in game["Packages"].items()}   # None while inside a truck
        self.package_in = dict.fromkeys(game["Packages"])                               # the truck, or None
        self.cost = 0

    def load_of(self, truck):
        return sum(self.game["Packages"][p][1] for p, t in self.package_in.items() if t == truck)

    def aboard(self, ferry):
        return [t for t, f in self.truck_on.items() if f == ferry]

    def solved(self):
        return all(self.package_at[p] == goal for p, (_, _, goal) in self.game["Packages"].items())

    def snapshot(self):
        return dict(truck_at=dict(self.truck_at), truck_on=dict(self.truck_on), ferry_at=dict(self.ferry_at),
                    package_at=dict(self.package_at), package_in=dict(self.package_in), cost=self.cost)

    def apply(self, action):
        match = ACTION.fullmatch(action)
        if not match:
            raise IllegalAction(f"{action!r}: not a valid action string")
        args = [int(x) for x in match.group(2).split(",")]
        try:
            getattr(self, match.group(1).lower())(*args)
        except (KeyError, TypeError) as error:
            raise IllegalAction(f"{action}: wrong number or unknown ID ({error})") from None
        self.cost += SAIL_COST if match.group(1) == "SAIL" else 1

    def require(self, condition, why):
        if not condition:
            raise IllegalAction(why)

    def drive(self, truck, source, target):
        self.require(self.truck_at[truck] == source, f"DRIVE: truck {truck} is not standing at {source}")
        self.require(source != target and frozenset((source, target)) in self.roads, f"DRIVE: no road {source}-{target}")
        self.truck_at[truck] = target

    def load(self, package, truck):
        place = self.truck_at[truck]
        self.require(place is not None, f"LOAD: truck {truck} is aboard a ferry")
        self.require(self.package_at[package] == place, f"LOAD: package {package} is not at location {place}")
        total = self.load_of(truck) + self.game["Packages"][package][1]
        self.require(total <= self.game["Trucks"][truck][1], f"LOAD: truck {truck} cannot hold weight {total}")
        self.package_at[package], self.package_in[package] = None, truck

    def unload(self, package, truck):
        self.require(self.package_in[package] == truck, f"UNLOAD: package {package} is not inside truck {truck}")
        self.require(self.truck_at[truck] is not None, f"UNLOAD: truck {truck} is aboard a ferry")
        self.package_at[package], self.package_in[package] = self.truck_at[truck], None

    def board(self, truck, ferry):
        self.require(self.truck_at[truck] == self.ferry_at[ferry], f"BOARD: truck {truck} is not standing at ferry {ferry}'s port")
        self.require(len(self.aboard(ferry)) < self.game["Ferries"][ferry][2], f"BOARD: ferry {ferry} is full")
        self.truck_at[truck], self.truck_on[truck] = None, ferry

    def sail(self, ferry, source, target):
        self.require(self.ferry_at[ferry] == source, f"SAIL: ferry {ferry} is not at {source}")
        served = self.game["Ferries"][ferry][1]
        self.require(source != target and target in served, f"SAIL: ferry {ferry} does not sail {source} to {target}")
        self.ferry_at[ferry] = target

    def disembark(self, truck, ferry):
        self.require(self.truck_on[truck] == ferry, f"DISEMBARK: truck {truck} is not aboard ferry {ferry}")
        self.truck_at[truck], self.truck_on[truck] = self.ferry_at[ferry], None


def stop_with_parent():
    """If the checker is killed, for example by the stop button of an IDE, its child must not go on searching."""
    multiprocessing.parent_process().join()
    os._exit(1)


def solve_in_child(game, pipe):
    """Runs in its own process, so that the time limit can stop it. ex1 is imported only here, so the
    problem maker and the list of problems work before ex1.py does."""
    threading.Thread(target=stop_with_parent, daemon=True).start()
    try:
        import ex1
        import search
        t0 = time.perf_counter()
        problem = ex1.create_logistics_problem(game)
        result = search.astar_search(problem, problem.h_astar)
        seconds = time.perf_counter() - t0
        if result:
            node, expanded = result
            plan = [str(n.action) for n in node.path()[::-1]][1:]   # str: an action of another type is illegal, not a crash
            answer = dict(plan=plan, cost=node.path_cost, expanded=expanded, seconds=seconds)
        else:
            answer = dict(plan=None, seconds=seconds)
    except BaseException:   # utils.raiseNotDefined() calls sys.exit, which is not an Exception
        answer = dict(error=traceback.format_exc())
    print(end="", flush=True)   # what the solver printed must not be lost when the parent kills this process
    pipe.send(answer)


def solve(game, limit=TIME_LIMIT):
    """Returns dict(plan, cost, expanded, seconds), dict(error) if the solver crashed, or dict(timeout)."""
    parent, child = multiprocessing.Pipe(duplex=False)
    process = multiprocessing.Process(target=solve_in_child, args=(game, child), daemon=True)
    process.start()
    child.close()
    try:
        # the limit counts from after the imports, and the child measures it, so give the imports some room
        result = parent.recv() if parent.poll(limit + 5) else dict(timeout=f"no answer within {limit} s")
    except (EOFError, OSError):     # OSError: on Windows, if the child died before poll() began
        result = dict(error="the solver crashed, or ran out of memory")
    process.kill()
    process.join()
    if result.get("seconds", 0) > limit:
        result = dict(timeout=f"took {result['seconds']:.1f} s, over the limit of {limit} s")
    return result


def judge(game, result, optimal=None):
    """Returns (verdict, explanation) for what solve() returned. Replays the plan by the rules above."""
    if "timeout" in result:
        return "TIMEOUT", result["timeout"]
    if "error" in result:
        return "ERROR", result["error"]
    if result["plan"] is None:
        return "NO PLAN", "the search returned no plan"
    world = World(game)
    for step, action in enumerate(result["plan"], 1):
        try:
            world.apply(action)
        except IllegalAction as error:
            return "ILLEGAL", f"step {step}: {error}"
    if not world.solved():
        return "NOT SOLVED", "after the last action some package is not at its destination"
    if optimal is not None and world.cost != optimal:
        return "WRONG COST", f"cost {world.cost}, the optimum is {optimal}"
    return "PASS" if optimal is not None else "SOLVED", f"cost {world.cost}"


def find_problem(name):
    """Returns (set name, game, optimal cost) for a problem name."""
    for set_name, problems in SETS.items():
        if name in problems:
            return (set_name, *problems[name])
    raise SystemExit(f"Unknown problem or set: {name}. Use --list to see the names.")


def expand(names):
    """Turns the names of sets and problems into a list of problem names, keeping the order and no repeats."""
    all_problems = [problem for problems in SETS.values() for problem in problems]
    chosen = []
    for name in names:
        if name.lower() == "all":
            chosen += all_problems
        elif name in SETS:
            chosen += SETS[name]
        elif name.upper() in SETS and name not in all_problems:     # x means X, unless you named a problem x
            chosen += SETS[name.upper()]
        else:
            find_problem(name)
            chosen.append(name)
    return list(dict.fromkeys(chosen))


def show(text):
    """print() that does not stop the checker when the output cannot encode a letter, like Hebrew in a path in an error."""
    encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
    print(text.encode(encoding, "backslashreplace").decode(encoding), flush=True)


def main():
    parser = argparse.ArgumentParser(description="Run ex1.py on the problems. See the top of this file.")
    parser.add_argument("names", nargs="*", help="sets and problems to run: all, X, Y, examples, p1, x3, ...")
    parser.add_argument("--list", action="store_true", help="print the names of all the problems")
    parser.add_argument("--plan", action="store_true", help="also print each plan")
    parser.add_argument("--limit", type=float, default=TIME_LIMIT, help="seconds for each problem")
    args = parser.parse_args()
    if args.list:
        for set_name, problems in SETS.items():
            print(f"{set_name}: {' '.join(problems)}")
        return
    points = dict.fromkeys(POINTS, 0)
    for name in expand(args.names or RUN):
        set_name, game, optimal = find_problem(name)
        result = solve(game, args.limit)
        verdict, why = judge(game, result, optimal)
        seconds = f"{result['seconds']:.2f} s" if "seconds" in result else ""
        last_line = why.strip().splitlines()[-1]
        show(f"[{name:>3}] {verdict:10s} {seconds:>9s}   {last_line}")
        if why.strip() != last_line:
            show(why)
        if args.plan and result.get("plan"):
            show(" ".join(result["plan"]))
        if verdict == "PASS" and set_name in POINTS:
            points[set_name] += POINTS[set_name]


if __name__ == '__main__':
    import ex1_check    # by name, so that the child process finds solve_in_child however an IDE runs this file
    ex1_check.main()
