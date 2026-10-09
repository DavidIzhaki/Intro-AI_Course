from pprint import pprint
import numpy as np
import re

ACTIONS = {"LOAD", "UP", "RIGHT", "LEFT", "DOWN", "POUR"}

class Game:
    """Game class --- presents a ext plate game played for given number of steps."""

    def __init__(self, problem, debug=False):
        """Initialize the Game class."""
        self._max_steps = problem["horizon"]
        self._problem = problem
        self._debug = debug
        if self._debug:
            self._history = list()
        self._steps = 0
        self._reward = 0
        self._robot_chosen_action_prob = problem["robot_chosen_action_prob"]
        self._goal_reward = self._problem.get("goal_reward", 0)
        self._plants_reward = problem['plants_reward']
        self._seed = problem["seed"]
        self._done = False
        self._successful = False
        np.random.seed(self._seed)
        self.rows, self.cols = problem["Size"]
        self.walls  = set(problem.get("Walls", []))
        self.taps   = set(problem.get("Taps", {}).keys())
        self.plants = set(problem.get("Plants", {}).keys())
        
        # Robots: problem["Robots"]: rid -> (r, c, carried, capacity)
        self._robots = {}
        self._capacities = {}   # rid -> capacity
        for rid, (r, c, carried, capacity) in problem["Robots"].items():
            self._capacities[rid] = capacity
            self._robots[rid] = {
                "pos":   (r, c),
                "load":  carried,   # current carried water
                "cap":   capacity,  # capacity (may be useful later)
            }

        # Plants: problem["Plants"]: (r, c) -> required_water
        self._plants = {}
        for (r, c), need in problem["Plants"].items():
            self._plants[(r, c)] = {
                "need": need,  # remaining water needed
            }

        # Taps: problem["Taps"]: (r, c) -> water_units
        self._taps = {}
        for (r, c), water in problem["Taps"].items():
            self._taps[(r, c)] = {
                "water": water,  # remaining water in tap
            }
        # Precompute initial state
        self._state = self._build_state()
        self._initial_state = self._state

        # For each (r,c) → list of actions that *can* be applied in that cell
        self.applicable_actions = {}
        self._init_applicable_actions()

    def _init_applicable_actions(self):
        for r in range(self.rows):
            for c in range(self.cols):
                pos = (r, c)

                # If it's a wall, no actions (or skip it completely)
                if pos in self.walls:
                    self.applicable_actions[pos] = []
                    continue

                actions = []

                # Movement actions (only if next cell is inside grid and not a wall)
                if r - 1 >= 0 and (r - 1, c) not in self.walls:
                    actions.append("UP")
                if r + 1 < self.rows and (r + 1, c) not in self.walls:
                    actions.append("DOWN")
                if c - 1 >= 0 and (r, c - 1) not in self.walls:
                    actions.append("LEFT")
                if c + 1 < self.cols and (r, c + 1) not in self.walls:
                    actions.append("RIGHT")

                # LOAD is only meaningful on a tap cell
                if pos in self.taps:
                    actions.append("LOAD")

                # POUR is only meaningful on a plant cell
                if pos in self.plants:
                    actions.append("POUR")

                self.applicable_actions[pos] = actions
                

        
    def _get_adjacent_cells(self, r, c):
        """Return dict: dir_name -> (nr, nc) for legal orthogonal moves."""
        moves = {}
        for name, (dr, dc) in self.directions.items():
            nr, nc = r + dr, c + dc
            if 0 <= nr < self.N and 0 <= nc < self.M:
                if (nr, nc) not in self.walls:
                    moves[name] = (nr, nc)
        return moves
    def get_current_state(self):

        return self._state

    def get_max_steps(self):

        return self._max_steps

    def get_current_reward(self):
  
        return self._reward

    def get_problem(self):
      
        return self._problem
    
    def get_current_steps(self):
      
        return self._steps
    
    def get_done(self):
      
        return self._done
    
    def get_capacities(self):
        return self._capacities


   

    def parse_robot_action(self, s: str):
        m = re.fullmatch(r"\s*([A-Za-z_]\w*)\s*\(\s*([^)]+?)\s*\)\s*", s)
        if not m:
            raise ValueError(f"Bad action format: {s!r}")

        action = m.group(1).upper()
        if action not in ACTIONS:
            raise ValueError(f"Unknown action {action!r} in {s!r}")

        robot_id_str = m.group(2).strip()
        robot_id = int(robot_id_str)  # will raise if not an integer

        return action, robot_id
    
    def submit_next_action(self, chosen_action):
        """
        Takes chosen action from user and updates the game from its consequences.
        """
        if self._done:
            return

        # Special RESET action (no robot id, just "RESET")
        if chosen_action == "RESET":
            self._state = self._initial_state
            self._steps += 1

            if self._debug:
                submit_result = [f"step {self._steps}, action_choose: RESET, action_applicable: RESET"]
                self._history.append(submit_result)

            if self._steps == self._max_steps:
                self._done = True
            return

        # 1) Parse "ACTION(robot_id)"
        action_name, robot_id = self.parse_robot_action(chosen_action)

        # Read current state
        robots_t, plants_t, taps_t, total_water_need = self._state

        # 2) Check Illegal Action
        robots_list = list(robots_t)   # mutable copies
        plants_list = list(plants_t)
        taps_list   = list(taps_t)

        robot_idx = None
        r = c = load = None
        for idx, (rid, (rr, cc), l) in enumerate(robots_list):
            if rid == robot_id:
                robot_idx = idx
                r, c, load = rr, cc, l
                break

        if robot_idx is None:
            raise ValueError(f"Robot {robot_id} not found in state")

        robot_pos = (r, c)

        plant_positions = {pos for (pos, need) in plants_t}
        tap_positions   = {pos for (pos, water) in taps_t}
        # --- NEW: filter applicable actions to avoid robot collisions ---

        # positions occupied by other robots (not this one)
        occupied_positions = {
            (rr, cc)
            for (rid, (rr, cc), l) in robots_t
            if rid != robot_id
        }

        base_applicable = self.applicable_actions[robot_pos]

        dynamic_applicable = []
        for a in base_applicable:
            if a in ("UP", "DOWN", "LEFT", "RIGHT"):
                # compute target cell for this move
                if a == "UP":
                    target = (r - 1, c)
                elif a == "DOWN":
                    target = (r + 1, c)
                elif a == "LEFT":
                    target = (r, c - 1)
                else:  # "RIGHT"
                    target = (r, c + 1)

                # if another robot is there, this move is not allowed now
                if target in occupied_positions:
                    continue

            # everything else (including LOAD/POUR) stays
            dynamic_applicable.append(a)
        if (
            (action_name not in dynamic_applicable)
            or (action_name == "POUR" and (load == 0 or robot_pos not in plant_positions))
            or (action_name == "LOAD" and (load >= self._robots[robot_id]["cap"] or robot_pos not in tap_positions))
        ):
            # illegal action from this cell
            raise ValueError(
                f"\nIllegal action {action_name} from position {robot_pos}\n"
                f"for robot {robot_id}\n"
                f"with state: {self._state}"
            )

        # 3) Sample success / failure
        p_success = self._robot_chosen_action_prob[robot_id]
        success = (np.random.rand() < p_success)
        add_reward = 0
        submit_result = []  # only used when self._debug is True
        chosen_action_name = action_name  # default = what we tried to do

        # 4) Apply action
        if success:

            # ---------- MOVE actions ----------
            if action_name in ("UP", "DOWN", "LEFT", "RIGHT"):
                if action_name == "UP":
                    new_pos = (r - 1, c)
                elif action_name == "DOWN":
                    new_pos = (r + 1, c)
                elif action_name == "LEFT":
                    new_pos = (r, c - 1)
                else:  # "RIGHT"
                    new_pos = (r, c + 1)

                # We already checked applicability, so we just move
                robots_list[robot_idx] = (robot_id, new_pos, load)

            # ---------- LOAD action ----------
            elif action_name == "LOAD":
                # we already know there's a tap here and load < cap
                tap_idx = None
                tap_water = None
                for idx, (pos, water) in enumerate(taps_list):
                    if pos == robot_pos:
                        tap_idx = idx
                        tap_water = water
                        break

                # decrease tap water by 1, delete if becomes 0
                new_tap_water = tap_water - 1
                if new_tap_water > 0:
                    taps_list[tap_idx] = (robot_pos, new_tap_water)
                else:
                    del taps_list[tap_idx]

                # increase robot load by 1
                new_load = load + 1
                robots_list[robot_idx] = (robot_id, robot_pos, new_load)

            # ---------- POUR action ----------
            elif action_name == "POUR":
                # Find plant at this position (we know it exists by precondition)
                plant_idx = None
                plant_need = None
                for idx, (ppos, need) in enumerate(plants_list):
                    if ppos == robot_pos:
                        plant_idx = idx
                        plant_need = need
                        break

                new_need = plant_need - 1
                new_load = load - 1

                # update or delete the plant
                if new_need > 0:
                    plants_list[plant_idx] = (robot_pos, new_need)
                else:
                    del plants_list[plant_idx]

                # update robot
                robots_list[robot_idx] = (robot_id, robot_pos, new_load)
                total_water_need -= 1

                # Sample reward uniformly from this plant's reward list
                reward_options = self._plants_reward[robot_pos]
                sampled_reward = np.random.choice(reward_options)
                add_reward += sampled_reward

        # Robot Error.
        else:
            # ---------- MOVE actions ----------
            if action_name in ("UP", "DOWN", "LEFT", "RIGHT"):
                move_actions = ("UP", "DOWN", "LEFT", "RIGHT")

                # all move directions that are possible from this cell,
                # respecting other robots as well
                legal_moves = [
                    a for a in dynamic_applicable
                    if a in move_actions
                ]

                # remove the direction we *wanted*
                alt_moves = [a for a in legal_moves if a != action_name]

               
                
                # include “stay in place” as an option
                options = alt_moves + ["STAY"]

                # choose uniformly among these options
                chosen_err_move = np.random.choice(options)
                chosen_action_name = chosen_err_move

                if chosen_err_move == "STAY":
                    new_pos = robot_pos
                else:
                    # move according to the alternative direction
                    if chosen_err_move == "UP":
                        new_pos = (r - 1, c)
                    elif chosen_err_move == "DOWN":
                        new_pos = (r + 1, c)
                    elif chosen_err_move == "LEFT":
                        new_pos = (r, c - 1)
                    else:  # "RIGHT"
                        new_pos = (r, c + 1)

                robots_list[robot_idx] = (robot_id, new_pos, load)

            # ---------- LOAD (error) ----------
            elif action_name == "LOAD":
                # nothing happens
                chosen_action_name = "LOAD FAIL"

            # ---------- POUR (error): lose 1 load for nothing ----------
            elif action_name == "POUR":
                new_load = load - 1
                chosen_action_name = "POUR FAIL"
                robots_list[robot_idx] = (robot_id, robot_pos, new_load)

        # Rebuild state with updated robots/plants/taps
        # First, accumulate step reward
        self._reward += add_reward

        # Goal check: if total_water_need == 0 → add goal reward and reset state
        if total_water_need == 0:
            self._reward += self._goal_reward
            self._state = self._initial_state
        else:
            robots_t = tuple(robots_list)
            plants_t = tuple(plants_list)
            taps_t   = tuple(taps_list)
            self._state = (robots_t, plants_t, taps_t, total_water_need)

        # Step count and done
        self._steps += 1
        if self._steps == self._max_steps:
            self._done = True

        # Debug history
        if self._debug:
            submit_result = []
            submit_result.append(
                f"step {self._steps}, action_choose: {chosen_action}, action_applicable: {chosen_action_name}"
            )
            self._history.append(submit_result)

        
        
    def _build_state(self):
        """
        Build a canonical state representation:
        (robots_t, plants_t, taps_t, total_water_need)

        robots_t: tuple of (robot_id, (r, c), load), sorted by robot_id
        plants_t: tuple of ((r, c), need), sorted by position
        taps_t:   tuple of ((r, c), water), sorted by position
        total_water_need: sum of plant needs
        """

        # Robots
        robots_t_list = []
        for rid, data in self._robots.items():
            (r, c) = data["pos"]
            load = data["load"]
            robots_t_list.append((rid, (r, c), load))
        robots_t_list.sort(key=lambda x: x[0])  # sort by robot_id
        robots_t = tuple(robots_t_list)

        # Plants
        plants_t_list = []
        for pos, data in self._plants.items():
            need = data["need"]
            plants_t_list.append((pos, need))
        plants_t_list.sort(key=lambda x: x[0])  # sort by (r, c)
        plants_t = tuple(plants_t_list)

        # Taps
        taps_t_list = []
        for pos, data in self._taps.items():
            water = data["water"]
            taps_t_list.append((pos, water))
        taps_t_list.sort(key=lambda x: x[0])  # sort by (r, c)
        taps_t = tuple(taps_t_list)

        # Total water need in the system (current, not initial)
        total_water_need = sum(need for (_, need) in plants_t_list)

        return (robots_t, plants_t, taps_t, total_water_need)

  

    def show_history(self):
        """
        Debug function used to see the probabilities and the process of the game.
        """
        if self._debug:
            print('History:')
            pprint(self._history)


def create_pressure_plate_game(game):
    if game[1]:
        print('--------DEBUG MODE--------')
        print('<< create pressure plate game >>')
        print('under these conditions:')
        pprint(game[0])
    return Game(*game)





