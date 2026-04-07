import os
import json

class EloManager:
    def __init__(self, elo_path: str = None):
        dirname = os.path.dirname(__file__)
        if elo_path:
            self.elo_path = os.path.abspath(elo_path)
        else:
            self.elo_path = os.path.abspath(os.path.join(dirname, "..", "elos.json"))
        self.elos = {}
        self._load_elos()

    def get_leaderboard(self, game):
        # Generate a leaderboard string for the top 10 players across all game types.
        player_to_summed_elo = {}
        games_to_consider = [game] if game else self.elos.keys()
        for game_type in games_to_consider:
            keys = self.elos.get(game_type, {}).keys()
            for key in keys:
                player_to_summed_elo[key] = player_to_summed_elo.get(key, 0) + self.elos[game_type][key]
        # Sort players by summed ELO and get top 10
        elos = sorted(player_to_summed_elo.items(), key=lambda x: x[1], reverse=True)
        ret = "ELO Leaderboard " + (f"for {game}" if game else "across all games") + ":\n"
        for i in range(min(10, len(elos))):
            user_id = int(elos[i][0])
            elo = elos[i][1]
            user_mention = f"<@{user_id}>"
            ret += f"{i + 1}. {user_mention} - {elo}\n"
        return ret

    def _load_elos(self):
        print("Loading ELOs.")
        if os.path.exists(self.elo_path):
            try:
                with open(self.elo_path, "r") as f:
                    self.elos = json.load(f)
            except Exception:
                self.elos = {}
                self._save_elos()
        else:
            # create file
            self.elos = {}
            self._save_elos()
        print("ELOs loaded.")

    def _save_elos(self):
        print("Saving ELOs.")
        try:
            os.makedirs(os.path.dirname(self.elo_path), exist_ok=True)
            with open(self.elo_path, "w") as f:
                json.dump(self.elos, f, indent=2)
        except Exception:
            pass
        print("ELOs saved.")

    def get_elo(self, user, game_type):
        key = str(getattr(user, "id", user))
        if game_type not in self.elos:
            return 1200
        try:
            if key in self.elos[game_type]:
                return int(self.elos[game_type][key])
        except Exception:
            return 1200
        return 1200

    def set_elo(self, user, game_type, new_elo):
        key = str(user.id)
        self.elos.setdefault(game_type, {})[key] = int(new_elo)
        self._save_elos()

    def update_winner_loser_from_diff(self, winner, loser, game_type, diff):
        old_winner_elo = self.get_elo(winner, game_type)
        new_winner_elo = old_winner_elo + diff
        self.set_elo(winner, game_type, new_winner_elo)

        old_loser_elo = self.get_elo(loser, game_type)
        new_loser_elo = old_loser_elo - diff
        self.set_elo(loser, game_type, new_loser_elo)

    def update_elos_for_game(self, game, game_type):
        winner = game.who_gains_elo()
        loser = game.who_loses_elo()
        if winner is None or loser is None:
            print("No ELO change for this game.")
            return 0

        keyw = str(winner.id)
        keyl = str(loser.id)
        oldw = self.get_elo(winner, game_type)
        oldl = self.get_elo(loser, game_type)

        K = 32
        # expected scores
        expected_winner = 1 / (1 + 10 ** ((oldl - oldw) / 400))
        expected_loser = 1 / (1 + 10 ** ((oldw - oldl) / 400))
        # actual scores
        actual_winner = 1
        actual_loser = 0
        # ELO change
        diff = int(K * (actual_winner - expected_winner))

        self.update_winner_loser_from_diff(winner, loser, game_type, diff)

        return diff

elo_manager = EloManager()
