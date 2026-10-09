import ext_plant

id = ["000000000"]

class Controller:
    """This class is a controller for the ext_plant game."""

    def __init__(self, game: ext_plant.Game):
        """Initialize controller for given game model."""
        self.original_game = game


  
    def choose_next_action(self, state):
        """ Choose the next action given a state."""
        raise ValueError("Fill the function")