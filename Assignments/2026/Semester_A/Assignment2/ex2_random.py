import ext_plant
import numpy as np

id = ["000000000"]

class Controller:
    """Random baseline controller for ext_plant."""

    def __init__(self, game: ext_plant.Game):
        self.original_game = game

    def choose_next_action(self, state):
        robots_t, plants_t, taps_t, total_need = state

        plant_positions = {pos for (pos, need) in plants_t}
        tap_positions   = {pos for (pos, water) in taps_t}

        occupied_positions = {(rr, cc) for (rid, (rr, cc), l) in robots_t}

        legal = []

        for rid, (r, c), load in robots_t:
            pos = (r, c)
            base_actions = self.original_game.applicable_actions[pos]

            for a in base_actions:
                if a in ("UP", "DOWN", "LEFT", "RIGHT"):
                    if a == "UP":    target = (r - 1, c)
                    elif a == "DOWN": target = (r + 1, c)
                    elif a == "LEFT": target = (r, c - 1)
                    else:             target = (r, c + 1)

                    if target in occupied_positions:
                        continue

                if a == "POUR" and (load == 0 or pos not in plant_positions):
                    continue

                if a == "LOAD":
                    cap = self.original_game._robots[rid]["cap"]
                    if load >= cap or pos not in tap_positions:
                        continue

                legal.append(f"{a}({rid})")

        if not legal:
            return "RESET"

        return np.random.choice(legal)
