import random


class QueueingPlayer:
    def __init__(self, player, current_time: int):
        self.player = player
        self.join_time = current_time
        self.box = []  # Box must be handled by the matchmaking policy and is not handled by the queue manager


class Queue:
    matchmaking_queue: list[QueueingPlayer]
    current_time: int

    def __init__(self):
        self.matchmaking_queue = []
        self.current_time = 0
        self.box_updater = basic_box_update  # Callable(box, rating_system_sorting_name, turns_waiting=0)
        self.rating_system_sorting_name = "elo"

    def manage_queue(self, players, probability=0.0005):
        # A number of variables in this function are hard coded
        for player in players:
            value = random.random()
            has_had_recent_match = False  # player.matches and player.matches[-1].time + 200 > self.current_time
            # or value < 0.25 and player.matches and player.matches[-1].time + 20 == self.current_time
            # or value < 0.05 and player.name < 100
            if not has_had_recent_match and value < probability and not player.is_currently_in_queue:
                self.matchmaking_queue.append(QueueingPlayer(player, self.current_time))
                player.is_currently_in_queue = True
        self.current_time += 1

    def matchmaker(self, match_simulation_function):
        self.matchmaking_queue.sort(key=lambda x: x.player.get_rating(self.rating_system_sorting_name), reverse=True)
        for queueing_player in self.matchmaking_queue:
            queueing_player.box = self.box_updater(queueing_player.box,
                                                   queueing_player.player.get_rating(self.rating_system_sorting_name),
                                                   self.rating_system_sorting_name,
                                                   self.current_time - queueing_player.join_time - 1)
        new_matches = []
        i = 0
        # Players are matched with the first player (thus closest in rating) which has an overlapping box.
        while i < len(self.matchmaking_queue):
            queueing_player = self.matchmaking_queue[i]
            match_found = False
            for queueing_opponent in self.matchmaking_queue:
                if queueing_player is queueing_opponent:
                    continue
                good_match = True
                # Boxes Policy 1: Box overlaps
                for k in range(len(queueing_player.box)):
                    if (max(queueing_player.box[k][0], queueing_opponent.box[k][0])
                            > min(queueing_player.box[k][1], queueing_opponent.box[k][1])):
                        good_match = False
                        break
                # Boxes Policy 2: Both boxes contain each other's rating
                # if not (queueing_player.box[0][0] <
                #         queueing_opponent.player.get_rating(self.rating_system_sorting_name)
                #         < queueing_player.box[0][1] and queueing_opponent.box[0][0] <
                #         queueing_player.player.get_rating(self.rating_system_sorting_name) <
                #         queueing_opponent.box[0][1]):
                #     good_match = False
                #     break
                if good_match:
                    new_matches.append(match_simulation_function(queueing_player.player, queueing_opponent.player))
                    new_matches[-1].time = self.current_time
                    player_wait_time = self.current_time - queueing_player.join_time - 1
                    opponent_wait_time = self.current_time - queueing_opponent.join_time - 1
                    new_matches[-1].wait_time_player1 = player_wait_time
                    new_matches[-1].wait_time_player2 = opponent_wait_time
                    queueing_player.player.is_currently_in_queue = False
                    queueing_opponent.player.is_currently_in_queue = False
                    self.matchmaking_queue.remove(queueing_player)
                    self.matchmaking_queue.remove(queueing_opponent)
                    match_found = True
                    break
            if not match_found:
                i += 1
        return new_matches


def basic_box_update(box, player_rating, rating_system_sorting_name, turns_waiting=0):
    opening = 100
    if turns_waiting == 0:
        if rating_system_sorting_name == "openskill":
            return [[player_rating - opening/50, player_rating + opening/50]]
        else:
            return [[player_rating - opening, player_rating + opening]]
        # if player_rating < 1000:
        #     return [[player_rating - 130, player_rating + 130]]
        # elif player_rating < 1500:
        #     return [[player_rating - 100, player_rating + 100]]
        # else:
        #     return [[player_rating - player_rating / 15, player_rating + player_rating / 15]]
    else:
        if rating_system_sorting_name == "openskill":
            return [[box[0][0] - opening/400, box[0][1] + opening/400]]
        else:
            return [[box[0][0] - opening/8.333, box[0][1] + opening/8.333]]
