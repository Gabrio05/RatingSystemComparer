from typing import NamedTuple
from collections.abc import Callable
import math


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
    return new_rating, new_rd


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


elo_system = RatingSystem("elo", 1500, elo_expected, elo)
glicko_system = RatingSystem("glicko", [1500, 350], glicko_expected, glicko)
all_systems = [elo_system, glicko_system]
