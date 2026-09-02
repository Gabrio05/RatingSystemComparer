from typing import NamedTuple
from collections.abc import Callable
import math
from openskill.models import BradleyTerryFull


# Elo
def elo_expected(rating1: float, rating2: float):
    scale = 400
    return 1 / (1 + 10 ** ((rating2 - rating1) / scale))


def elo(rating_player: float, rating_opponent: float, result: float):
    k = 32
    expected = elo_expected(rating_player, rating_opponent)
    change = k * (result - expected)
    return rating_player + change


# Glicko
glicko_q = math.log(10) / 400


def glicko_g(rating_deviation: float):
    return 1 / math.sqrt(1 + 3 * glicko_q ** 2 * rating_deviation ** 2 / math.pi ** 2)


def glicko_expected(rating_player: list[float], rating_opponent: list[float], skip_rd_calc: bool = False):
    if skip_rd_calc:
        rd_value = rating_opponent[1]
    else:
        rd_value = math.sqrt(rating_player[1] ** 2 + rating_opponent[1] ** 2)
    return 1 / (1 + 10 ** (-glicko_g(rd_value) * (rating_player[0] - rating_opponent[0]) / 400))


def glicko_d_square(rating_player: list[float], rating_opponent: list[float]):
    return (glicko_q ** 2 * glicko_g(rating_opponent[1]) ** 2
            * glicko_expected(rating_player, rating_opponent, True)
            * (1 - glicko_expected(rating_player, rating_opponent, True))
            ) ** -1


def glicko_pre_rd_update(rating: list[float]):
    c = 25
    return rating[0], min(math.sqrt(rating[1] ** 2 + c ** 2), 350)


def glicko(rating_player: list[float], rating_opponent: list[float], result: float):
    pre_rd = glicko_pre_rd_update(rating_player)[1]
    new_rating = (rating_player[0] + glicko_q / (1 / pre_rd ** 2 + 1 / glicko_d_square(rating_player, rating_opponent))
                  * glicko_g(rating_opponent[1]) * (result - glicko_expected(rating_player, rating_opponent, True)))
    new_rd = math.sqrt((1 / pre_rd ** 2 + 1 / glicko_d_square(rating_player, rating_opponent)) ** -1)
    return [new_rating, new_rd]


# Glicko-2
glicko_2_tau = 0.8
glicko_2_iteration_convergence = 0.000001


def glicko_to_glicko2_converter(rating_player: list[float]):
    new_rating = rating_player.copy()
    new_rating[0] = (rating_player[0] - 1500) * glicko_q
    new_rating[1] = rating_player[1] * glicko_q
    return new_rating


def glicko_2_g(rd: float):
    return 1 / math.sqrt(1 + 3 * rd ** 2 / math.pi ** 2)


def glicko_2_expected(rating_player: list[float], rating_opponent: list[float]):
    glicko_2_r = glicko_to_glicko2_converter(rating_player)
    glicko_2_o = glicko_to_glicko2_converter(rating_opponent)
    rd_value = math.sqrt(glicko_2_r[1] ** 2 + glicko_2_o[1] ** 2)
    return 1 / (1 + math.exp(-glicko_2_g(rd_value) * (glicko_2_r[0] - glicko_2_o[0])))


def glicko_2_expected_calc(rating_player: list[float], rating_opponent: list[float]):
    rd_value = rating_opponent[1]
    return 1 / (1 + math.exp(-glicko_2_g(rd_value) * (rating_player[0] - rating_opponent[0])))


def glicko_2_variance(rating_player: list[float], rating_opponent: list[float]):
    expected = glicko_2_expected_calc(rating_player, rating_opponent)
    return (glicko_2_g(rating_opponent[1]) ** 2 * expected * (1 - expected)) ** -1


def glicko_2_volatility_iteration(d, v, rd, sigma):
    def f(x):
        f1 = math.exp(x) * (d ** 2 - rd ** 2 - v - math.exp(x))
        f2 = 2 * (rd ** 2 + v + math.exp(x)) ** 2
        f3 = (x - a) / glicko_2_tau ** 2
        return f1 / f2 - f3

    a = math.log(sigma ** 2)
    big_a = a
    if d ** 2 > rd ** 2 + v:
        big_b = math.log(d ** 2 - rd ** 2 - v)
    else:
        k = 1
        while f(a - k * glicko_2_tau) < 0:
            k += 1
        big_b = a - k * glicko_2_tau
    f_a = f(big_a)
    f_b = f(big_b)
    while abs(big_b - big_a) > glicko_2_iteration_convergence:
        big_c = big_a + (big_a - big_b) * f_a / (f_b - f_a)
        f_c = f(big_c)
        if f_c * f_b <= 0:
            big_a = big_b
            f_a = f_b
        else:
            f_a = f_a / 2
        big_b = big_c
        f_b = f_c
    return math.exp(big_a / 2)


def glicko_2(rating_player: list[float], rating_opponent: list[float], result: float):
    glicko_2_r = glicko_to_glicko2_converter(rating_player)
    glicko_2_o = glicko_to_glicko2_converter(rating_opponent)
    var = glicko_2_variance(glicko_2_r, glicko_2_o)
    expected = glicko_2_expected_calc(glicko_2_r, glicko_2_o)
    delta = var * glicko_2_g(glicko_2_o[1]) * (result - expected)
    new_sigma = glicko_2_volatility_iteration(delta, var, glicko_2_r[1], glicko_2_r[2])
    # new_sigma = min(glicko_2_r[2], new_sigma)
    pre_phi = math.sqrt(glicko_2_r[1] ** 2 + new_sigma ** 2)
    new_phi = math.sqrt(1 / pre_phi ** 2 + 1 / var) ** -1
    new_mu = glicko_2_r[0] + new_phi ** 2 * glicko_2_g(glicko_2_o[1]) * (result - expected)
    return [new_mu / glicko_q + 1500, new_phi / glicko_q, new_sigma]


# Openskill
def openskill_expected(rating_player: list[float], rating_opponent: list[float]):
    model = BradleyTerryFull()
    p1 = model.create_rating(rating_player, "1")
    p2 = model.create_rating(rating_opponent, "2")
    return model.predict_win([[p1], [p2]])[0]


def openskill_rating(rating_player: list[float], rating_opponent: list[float], result: float):
    model = BradleyTerryFull()
    p1 = model.create_rating(rating_player, "1")
    p2 = model.create_rating(rating_opponent, "2")
    scores = [result, 1 - result]
    [p1, _] = model.rate([[p1], [p2]], scores=scores)
    return [p1[0].mu, p1[0].sigma]


# Random
def random_expected(_, _1):
    return 0.5


def random_rating(_, _1, _2):
    return 0


# Win Counter
def wins_expected(rating_player: float, rating_opponent: float):
    wins = rating_player + rating_opponent
    if wins == 0:
        return 0.5
    return rating_player / wins


def wins_rating(rating_player: float, _, result: float):
    return rating_player + (1 if result == 1 else 0)


# Win-Loss Difference
def difference_expected(rating_player: float, rating_opponent: float):
    difference = rating_player - rating_opponent
    if difference > 15:
        difference = 15
    elif difference < -15:
        difference = -15
    return (difference + 15) * (1 / 30)


def difference_rating(rating_player: float, _, result: float):
    return rating_player + (1 if result == 1 else -1)


# All rating systems
class RatingSystem(NamedTuple):
    """

    :var name: The identifying name of the rating system.
    :var starting_rating: Number(s) representing the initial rating of a player.
    :var estimating_function: A function taking two ratings which returns a
        number between 0 and 1 corresponding to the probability of the first rating winning.
    :var update_function: A function taking the player's and opponent's ratings
        and match results and returns the player's updated rating.
    """
    name: str
    starting_rating: float | list[float]
    estimating_function: Callable[[float | list[float], float | list[float]],
                                  float]
    update_function: Callable


elo_system = RatingSystem("elo", 1500.0, elo_expected, elo)
glicko_system = RatingSystem("glicko", [1500.0, 350.0], glicko_expected, glicko)
glicko_2_system = RatingSystem("glicko2", [1500.0, 350.0, 0.06], glicko_2_expected, glicko_2)
openskill_system = RatingSystem("openskill", [25.0, 25/3], openskill_expected, openskill_rating)
random_system = RatingSystem("random", 0, random_expected, random_rating)
wins_system = RatingSystem("wins", 0, wins_expected, wins_rating)
difference_system = RatingSystem("difference", 0, difference_expected, difference_rating)
# all_systems = [elo_system, glicko_system, glicko_2_system, openskill_system,
#                random_system, wins_system, difference_system]
# all_systems = [elo_system, glicko_system, glicko_2_system, openskill_system]
all_systems = [glicko_2_system]
