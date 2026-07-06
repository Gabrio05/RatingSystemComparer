import copy
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

    def get_rating(self, system_name: str):
        return self.ratings[system_name] \
            if isinstance(self.ratings[system_name], float) else self.ratings[system_name][0]


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
        self.match_generation_function = generate_random_matches
        self.rating_system_sorting_name = all_systems[0].name
        self.should_calculate_all_rating_systems = True

    def generate_matches(self, n: int):
        self.match_generation_function(self, n)

    def treat_matches(self):
        for match in self.untreated_matches:
            for system in all_systems:
                if self.should_calculate_all_rating_systems or system.name == self.rating_system_sorting_name:
                    new1, new2 = get_new_ratings(match, system)
                    match.player1.ratings[system.name] = new1
                    match.player2.ratings[system.name] = new2
            self.matches.append(match)
        self.untreated_matches = []

    def sort_players_by_rating(self):
        self.players.sort(key=lambda x: x.get_rating(self.rating_system_sorting_name), reverse=True)


def generate_random_matches(self: Simulation, n: int):
    for _ in range(n):
        player1, player2 = random.choices(self.players, k=2)
        self.untreated_matches.append(
            self.match_simulation_function(player1, player2))


def generate_stairs_matches(self: Simulation, n: int):
    # Ratings must be a float only or have their first float in the list be their rating
    self.sort_players_by_rating()
    count = 0
    while count < n:
        for i in range(len(self.players) // 2):
            self.untreated_matches.append(
                self.match_simulation_function(self.players[i * 2], self.players[i * 2 + 1])
            )
            count += 1
            if count >= n:
                break


def generate_random_batch_matches(self: Simulation, n: int):
    players_to_consider = 4
    self.sort_players_by_rating()
    count = 0
    while count < n:
        untreated_players = copy.copy(self.players)
        for i in range(len(self.players) // 2):
            first = 0
            second = int(random.random() * (players_to_consider if len(untreated_players) - 1 > players_to_consider
                                            else len(untreated_players) - 1)) + 1
            self.untreated_matches.append(
                self.match_simulation_function(untreated_players[first], untreated_players[second])
            )
            untreated_players.pop(second)
            untreated_players.pop(first)
            count += 1
            if count >= n:
                break


def generate_random_skill_adjusted_matches(self: Simulation, n: int):
    players_to_consider = 10
    self.sort_players_by_rating()
    count = 0
    while count < n:
        untreated_players = copy.copy(self.players)
        for i in range(len(self.players) // 2):
            first = 0
            second = 1
            real_players_to_consider = (players_to_consider if len(untreated_players) - 1 > players_to_consider
                                        else len(untreated_players) - 1)
            biggest_difference = untreated_players[real_players_to_consider].get_rating(self.rating_system_sorting_name)
            inverse_skill_difference = 0
            for j in range(real_players_to_consider):
                inverse_skill_difference += (biggest_difference
                                             - untreated_players[j + 1].get_rating(self.rating_system_sorting_name))
            value = random.random() * inverse_skill_difference
            for j in range(real_players_to_consider):
                value -= biggest_difference - untreated_players[j + 1].get_rating(self.rating_system_sorting_name)
                if value < 0:
                    second = j + 1
                    break
            self.untreated_matches.append(
                self.match_simulation_function(untreated_players[first], untreated_players[second])
            )
            untreated_players.pop(second)
            untreated_players.pop(first)
            count += 1
            if count >= n:
                break


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


# Matchmaking Policies
def immediate_total_random_match_generation(simulation: Simulation, n_matches: int):
    simulation.generate_matches(n_matches)
    simulation.treat_matches()


def batched_match_generation(simulation: Simulation, n_matches: tuple[int, int]):
    for _ in range(n_matches[0]):
        simulation.generate_matches(n_matches[1])
        simulation.treat_matches()


# Loss metrics
def calculate_final_rating_errors(simulation: Simulation, system: Rating_System):
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
    return bradley_error / (len(simulation.players) * (len(simulation.players) - 1))


def calculate_all_match_skill_disparities(simulation: Simulation):
    mean_square_error = 0
    for match in simulation.matches:
        mean_square_error += ((0.5 - match.player1.skill / (match.player1.skill + match.player2.skill)) * 2)**2
    return mean_square_error / len(simulation.matches)


def run_simulation(n_players: int, skill_generation_function,
                   n_matches: float | tuple[float, ...], match_simulation_function, match_generation_function,
                   matchmaking_policy, should_separate_simulations_by_system: bool = False):
    simulation = Simulation()
    simulation.players = generate_players(n_players, skill_generation_function)
    simulation.match_simulation_function = match_simulation_function
    simulation.match_generation_function = match_generation_function
    simulations = {}  # Unused if "should not separate"
    if should_separate_simulations_by_system:
        for system in all_systems:
            simulations[system.name] = copy.deepcopy(simulation)
            simulations[system.name].rating_system_sorting_name = system.name
            simulations[system.name].should_calculate_all_rating_systems = False
            matchmaking_policy(simulations[system.name], n_matches)
    else:
        matchmaking_policy(simulation, n_matches)
    return_error = {}
    for system in all_systems:
        if should_separate_simulations_by_system:
            simulation = simulations[system.name]
        bradley_error = calculate_final_rating_errors(simulation, system)
        print(f"{bradley_error} is the error for {system.name}.")
        return_error[system.name] = bradley_error
    return return_error


def run_numerous_simulations(k: int):
    overall_error = None
    for _ in range(k):
        error = run_simulation(1000, generate_flat_skill,
                               (10, 1000), bradley_terry_simulate_match, generate_random_skill_adjusted_matches,
                               batched_match_generation, True)
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
