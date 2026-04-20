import random
import Rating_System
all_systems = Rating_System.all_systems


class Player:
    def __init__(self, name: str | int, skill: float | list[float] = 0):
        self.name = name
        self.skill = skill  # True skill of the player
        self.ratings = {}
        self.matches = []

    def __str__(self):
        return (f"{self.name} with skill {self.skill} "
                f"has ratings {self.ratings}.")


class Match:
    def __init__(self, player1: Player, player2: Player, result: float,
                 scoreline: tuple[float, float] | None = None,
                 time: float = 0):
        self.player1 = player1
        self.player2 = player2
        self.result = result  # 1, 0.5, or 0, 0 is player2 win
        self.scoreline = scoreline
        self.time = time

    def opposite_result(self):
        return 1 - self.result


def get_new_ratings(match: Match, system: Rating_System):
    rating1 = match.player1.ratings[system.name]
    rating2 = match.player2.ratings[system.name]
    new_rating1 = system.update_function(rating1, rating2, match.result)
    new_rating2 = system.update_function(rating2, rating1, match.opposite_result())
    return new_rating1, new_rating2


class Simulation:
    def __init__(self):
        self.players = []
        self.matches = []
        self.untreated_matches = []
        self.match_simulation_function = None

    def generate_matches(self, n: int):
        for _ in range(n):
            player1, player2 = random.choices(self.players, k=2)
            self.untreated_matches.append(
                self.match_simulation_function(player1, player2))

    def treat_matches(self):
        for match in self.untreated_matches:
            for system in all_systems:
                new1, new2 = get_new_ratings(match, system)
                match.player1.ratings[system.name] = new1
                match.player2.ratings[system.name] = new2
            self.matches.append(match)
        self.untreated_matches = []


def generate_flat_skill():
    """Generate a logarithmic random number between 1e-15 and 1e15."""
    return 10 ** ((random.random() - 0.5) * 30)


def generate_players(n: int, skill_generator):
    players = []
    starting_ratings = {}
    for system in all_systems:
        starting_ratings[system.name] = system.starting_rating
    for i in range(n):
        skill = skill_generator()
        players.append(Player(i, skill))
        players[-1].ratings = starting_ratings.copy()
    return players


def bradley_terry_simulate_match(player1: Player, player2: Player):
    if random.random() < player1.skill / (player1.skill + player2.skill):
        win = 1
    else:
        win = 0
    return Match(player1, player2, win)


def immediate_total_match_generation(simulation: Simulation, n_matches: int):
    simulation.generate_matches(n_matches)
    simulation.treat_matches()


def run_simulation(n_players: int, skill_generation_function,
                   n_matches: int, match_generation_function,
                   matchmaking_policy):
    simulation = Simulation()
    simulation.players = generate_players(n_players, skill_generation_function)
    simulation.match_simulation_function = match_generation_function
    matchmaking_policy(simulation, n_matches)
    return_error = {}
    for system in all_systems:
        bradley_error = 0
        for player in simulation.players:
            for opponent in simulation.players:
                if player is not opponent:
                    expected = system.estimating_function(
                        player.ratings[system.name],
                        opponent.ratings[system.name])
                    # TODO True expected is hardcoded
                    true_expected = player.skill / (
                            player.skill + opponent.skill)
                    bradley_error += (true_expected - expected) ** 2
        bradley_error = bradley_error / (len(simulation.players) *
                                         (len(simulation.players) - 1))
        print(f"{bradley_error} is the error for {system.name}.")
        return_error[system.name] = bradley_error
    return return_error


def run_numerous_simulations(k: int):
    overall_error = None
    for _ in range(k):
        error = run_simulation(1000, generate_flat_skill,
                               10000, bradley_terry_simulate_match,
                               immediate_total_match_generation)
        if overall_error is None:
            overall_error = error
        else:
            for r_system in all_systems:
                overall_error[r_system.name] += error[r_system.name]
    for r_system in all_systems:
        print(f"The average error of {r_system.name} was "
              f"{overall_error[r_system.name] / k}.")


run_numerous_simulations(15)

# Different player generation models: Gaussian, Hill (flat and tapers off)
# Different match generation models (matchmaking policy)
# Different probability models: Bradley-Terry
