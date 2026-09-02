import copy
import random
import ContinuousMatchmaking
import Rating_System
all_systems = Rating_System.all_systems


class Player:
    """

    :var name: Name (or index) to refer back to the player.
    :var skill: The true skill of the player and how matches are resolved.
    :var ratings: The calculated ratings of the player.
    :var matches: The matches this player has played.
    """
    def __init__(self, name: str | int, skill: float | list[float] = 0):
        self.name = name
        self.skill = skill  # True skill of the player
        self.ratings = {}
        self.matches = []
        self.is_currently_in_queue = False

    def __str__(self):
        return (f"{self.name} with skill {self.skill} "
                f"has ratings {self.ratings}.")

    def get_rating(self, system_name: str):
        return self.ratings[system_name] \
            if isinstance(self.ratings[system_name], float) else self.ratings[system_name][0]


class Match:
    """A class representing a single match between two players.

    :var player1: Player class instance.
    :var player2: Second player class instance.
    :var result: 1, 0.5, or 0, 0 is player2 win
    :var scoreline: Use for more specific game scores. Currently unused.
    :var time: The time of the match for the matchmaking policy. 0 by default.
    :var player1_rating: The rating of player1 after the match.
    :var player2_rating: The rating of player2 after the match.
    """
    def __init__(self, player1: Player, player2: Player, result: float,
                 scoreline: tuple[float, float] | None = None,
                 time: float = 0):
        self.player1 = player1
        self.player2 = player2
        self.result = result
        self.scoreline = scoreline
        self.time = time
        self.wait_time_player1 = time
        self.wait_time_player2 = time
        self.player1_rating = {}
        self.player2_rating = {}

    def opposite_result(self):
        return 1 - self.result


def get_new_ratings(match: Match, system: Rating_System.RatingSystem):
    """Use the system's update function to update the rating of both
    players in the match according to the match results.
    """
    rating1 = match.player1.ratings[system.name]
    rating2 = match.player2.ratings[system.name]
    new_rating1 = system.update_function(rating1, rating2, match.result)
    new_rating2 = system.update_function(rating2, rating1, match.opposite_result())
    return new_rating1, new_rating2


class Simulation:
    """Generate matches between given players and calculate ratings
    for those matches, recursively if needed.

    :var players: The Player instances for the simulation.
    :var matches: The Match instances which have already had their
        ratings calculated.
    :var untreated_matches: The Match instances which have not had
        their ratings calculated.
    :var match_simulation_function: A Callable to generate a new Match
        instance from two Player instances.
    :var match_generation_function: A Callable to generate matches
        (calling match_simulation_function repeatedly) by repeatedly
        picking two Player instances.
    :var rating_system_sorting_name: The rating to sort by if the
        matches generated are affected by the player ratings (i.e., the
        matchmaking policy depends on the specific rating system)
    :var should_calculate_all_rating_systems: Set to "False" to reduce
        computation if the matchmaking policy depends on the specific
        rating system.
    """
    players: list[Player]
    matches: list[Match]
    untreated_matches: list[Match]

    def __init__(self):
        self.players = []
        self.matches = []
        self.untreated_matches = []
        self.match_simulation_function = bradley_terry_simulate_match
        self.match_generation_function = generate_random_matches
        self.rating_system_sorting_name = all_systems[0].name
        self.should_calculate_all_rating_systems = True

    def generate_matches(self, n: int):
        self.match_generation_function(self, n)

    def treat_matches(self):
        """Calculate the rating of players for all untreated matches."""
        for match in self.untreated_matches:
            for system in all_systems:
                if self.should_calculate_all_rating_systems or system.name == self.rating_system_sorting_name:
                    new1, new2 = get_new_ratings(match, system)
                    match.player1.ratings[system.name] = new1
                    match.player2.ratings[system.name] = new2
                    match.player1_rating = new1
                    match.player2_rating = new2
            self.matches.append(match)
            match.player1.matches.append(match)
            match.player2.matches.append(match)
        self.untreated_matches = []

    def sort_players_by_rating(self):
        self.players.sort(key=lambda x: x.get_rating(self.rating_system_sorting_name), reverse=True)


# Match Generation Functions used for the Matchmaking Policy
def generate_random_matches(self: Simulation, n: int):
    """Generate n fully random matches."""
    for _ in range(n):
        player1, player2 = random.choices(self.players, k=2)
        self.untreated_matches.append(
            self.match_simulation_function(player1, player2))


def generate_stairs_matches(self: Simulation, n: int):
    """Sort all players by rating and pair each player with the player
    above (if even) or below (if odd).
    """
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


def generate_random_batch_matches(self: Simulation, n: int, players_to_consider=3):
    """Sort all players and, starting from the top, pair each player
    with a random player in the next 'players_to_consider' players.
    """
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


def generate_random_skill_adjusted_matches(self: Simulation, n: int, players_to_consider=3):
    """Sort all players and, starting from the top, pair each player
    with a random player in the next 'players_to_consider' players,
    weighing each player by the difference in rating with the current
    top player.
    """
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
                inverse_skill_difference += (untreated_players[j + 1].get_rating(self.rating_system_sorting_name)
                                             - biggest_difference)
            value = random.random() * inverse_skill_difference
            for j in range(real_players_to_consider):
                value -= untreated_players[j + 1].get_rating(self.rating_system_sorting_name) - biggest_difference
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


def generate_stairs_matchmaking_matches(self: Simulation, n: int):
    """Select a certain number of players to get n matches, sort the
    players, and pair them with their neighbour.
    """
    self.sort_players_by_rating()
    selection_probability = n * 2 / len(self.players)
    selected_players = []
    for player in self.players:
        if random.random() < selection_probability:
            selected_players.append(player)
    if len(selected_players) % 2 != 0:
        selected_players.remove(random.choices(selected_players)[0])
    for i in range(len(selected_players) // 2):
        self.untreated_matches.append(
            self.match_simulation_function(selected_players[i * 2], selected_players[i * 2 + 1])
        )


def generate_random_batch_matchmaking_matches(self: Simulation, n: int, players_to_consider=50):
    """Select a certain number of players to get n matches, sort the
    players, and pair them, starting at the top with a random player up
    to 'players_to_consider' players under them.
    """
    players_to_consider = min(players_to_consider, n // 2)  # Capping at half the players, else it is the same as above
    self.sort_players_by_rating()
    selection_probability = n * 2 / len(self.players)
    selected_players = []
    for player in self.players:
        if random.random() < selection_probability:
            selected_players.append(player)
    if len(selected_players) % 2 != 0:
        selected_players.remove(random.choices(selected_players)[0])
    for i in range(len(selected_players) // 2):
        first = 0
        second = int(random.random() * (players_to_consider if len(selected_players) - 1 > players_to_consider
                                        else len(selected_players) - 1)) + 1
        self.untreated_matches.append(
            self.match_simulation_function(selected_players[first], selected_players[second])
        )
        selected_players.pop(second)
        selected_players.pop(first)


def generate_random_skill_adjusted_matchmaking_matches(self: Simulation, n: int, players_to_consider=50):
    """Select a certain number of players to get n matches, sort the
    players, and pair them with their neighbour.
    """
    players_to_consider = min(players_to_consider, n // 2)  # Capping at half the players, else it is the same as above
    self.sort_players_by_rating()
    selection_probability = n * 2 / len(self.players)
    selected_players = []
    for player in self.players:
        if random.random() < selection_probability:
            selected_players.append(player)
    if len(selected_players) % 2 != 0:
        selected_players.remove(random.choices(selected_players)[0])
    for i in range(len(selected_players) // 2):
        first = 0
        second = 1
        real_players_to_consider = (players_to_consider if len(selected_players) - 1 > players_to_consider
                                    else len(selected_players) - 1)
        biggest_difference = selected_players[real_players_to_consider].get_rating(self.rating_system_sorting_name)
        inverse_skill_difference = 0
        for j in range(real_players_to_consider):
            inverse_skill_difference += (selected_players[j + 1].get_rating(self.rating_system_sorting_name)
                                         - biggest_difference)
        value = random.random() * inverse_skill_difference
        for j in range(real_players_to_consider):
            value -= selected_players[j + 1].get_rating(self.rating_system_sorting_name) - biggest_difference
            if value < 0:
                second = j + 1
                break
        self.untreated_matches.append(
            self.match_simulation_function(selected_players[first], selected_players[second])
        )
        selected_players.pop(second)
        selected_players.pop(first)


# Skill random number generators
def generate_flat_skill():
    """Generate a logarithmic random number between 1e-15 and 1e15."""
    return 10 ** ((random.random() - 0.5) * 30)


def generate_gaussian_skill():
    return 10 ** random.gauss(0.0, 1.2)
    # return 10 ** random.gauss(0, 6.0)


# Player generator
def generate_players(n: int, skill_generator):
    """Generate a list of players with skill from to the
    skill_generator Callable.
    """
    players = []
    starting_ratings = {}
    for system in all_systems:
        starting_ratings[system.name] = system.starting_rating
    for i in range(n):
        skill = skill_generator()
        players.append(Player(i, skill))
        players[-1].ratings = starting_ratings.copy()
    return players


# Match resolver
def bradley_terry_simulate_match(player1: Player, player2: Player):
    # Expected is hardcoded in "calculate final rating errors" for Bradley-Terry
    if random.random() < player1.skill / (player1.skill + player2.skill):
        win = 1
    else:
        win = 0
    return Match(player1, player2, win)


# Matchmaking Policies
def immediate_total_random_match_generation(simulation: Simulation, n_matches: int):
    """Generate n_matches matches and calculate all players' ratings."""
    simulation.generate_matches(n_matches)
    simulation.treat_matches()


def batched_match_generation(simulation: Simulation, n_matches: tuple[int, int]):
    """Generate matches in rounds, calculating the players' ratings
    after each round.
    """
    for _ in range(n_matches[0]):
        simulation.generate_matches(n_matches[1])
        simulation.treat_matches()


def continuous_match_generation(simulation: Simulation, n_rounds: int):
    """Generate matches continuously, simulating players queuing for a
    match in-game.
    """
    queue = ContinuousMatchmaking.Queue()
    queue.rating_system_sorting_name = simulation.rating_system_sorting_name
    for i in range(n_rounds):
        queue.manage_queue(simulation.players)
        simulation.untreated_matches = queue.matchmaker(simulation.match_simulation_function)
        simulation.treat_matches()


# Loss metrics
def calculate_final_rating_errors(simulation: Simulation, system: Rating_System):
    """The mean square error of the ratings to the true skill of the
    player using each rating system's expected win rate function.
    """
    bradley_error = 0
    for player in simulation.players:
        for opponent in simulation.players:
            if player is not opponent:
                expected = system.estimating_function(
                    player.ratings[system.name],
                    opponent.ratings[system.name])
                # Warning: True expected is hardcoded for Bradley-Terry
                true_expected = player.skill / (
                        player.skill + opponent.skill)
                bradley_error += (true_expected - expected) ** 2
    return bradley_error / (len(simulation.players) * (len(simulation.players) - 1))


def calculate_all_match_skill_disparities(simulation: Simulation):
    """The mean square error of the imbalance of each generated match.
    A more imbalanced match is worse than one closer to 0.5 probability.
    """
    mean_square_error = 0
    for match in simulation.matches:
        mean_square_error += ((0.5 - match.player1.skill / (match.player1.skill + match.player2.skill)) * 2)**2
    return mean_square_error / len(simulation.matches)


def calculate_wait_time(simulation: Simulation):
    total_long_waits = 0
    total_players_long = 0
    for player in simulation.players:
        long_waits = 0
        for match in player.matches:
            if (match.player1 == player and match.wait_time_player1 > 50
                    or match.player2 == player and match.wait_time_player2 > 50):
                long_waits += 1
        total_long_waits += long_waits
        if long_waits > 5:
            total_players_long += 1
            # print(f"{player} with {long_waits} matches over 50 rounds waiting.")
    print(f"Number of long waits over 50: {total_long_waits} with {total_players_long} player(s) having long waits.")
    error = 0
    for match in simulation.matches:
        error += match.wait_time_player1 ** 2 + match.wait_time_player2 ** 2
    return error / len(simulation.matches)


# Simulation Runner
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
    wait_error = {}
    for system in all_systems:
        if should_separate_simulations_by_system:
            simulation = simulations[system.name]
        bradley_error = calculate_all_match_skill_disparities(simulation)
        print(f"{bradley_error} is the error for {system.name}.")
        wait_time = calculate_wait_time(simulation)
        print(f"Wait time error of {wait_time} for {len(simulation.matches)} matches.")
        return_error[system.name] = bradley_error
        wait_error[system.name] = wait_time
        # Other prints
        # print(f"One of the skills of a random player is {simulation.players[0].skill}.")
        # for match in simulation.players[0].matches:
        #     print(match.player1_rating, match.player2_rating)
    return return_error, wait_error


def run_numerous_simulations(k: int):
    overall_error = None
    wait_error = None
    for _ in range(k):
        error, w_error = run_simulation(1000, generate_gaussian_skill,
                                        100000, bradley_terry_simulate_match, None,
                                        continuous_match_generation, True)
        if overall_error is None:
            overall_error = error
        if wait_error is None:
            wait_error = w_error
        else:
            for r_system in all_systems:
                overall_error[r_system.name] += error[r_system.name]
            for r_system in all_systems:
                wait_error[r_system.name] += w_error[r_system.name]
    for r_system in all_systems:
        print(f"The average error of {r_system.name} was "
              f"{overall_error[r_system.name] / k} with wait time of {wait_error[r_system.name] / k}.")


run_numerous_simulations(15)
