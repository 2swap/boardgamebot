from enum import Enum
from elo_manager import elo_manager
from emojis import emojis

class Outcome(Enum):
    Tie = 0
    Player1Win = 1
    Player2Win = 2

class Game():
    def __init__(self, player1, player2, settings):
        self.player1 = player1
        self.player2 = player2
        self.player1_piece = "⚫"
        self.player2_piece = "⚪"
        self.turn = 1
        self.settings = settings
        self.outcome = None
        self.empty_piece = "🟠"
        self.game_type = None

    async def send_game_message(self, channel):
        # Only ping user if it's their turn, otherwise display their name without pinging them
        player1_mention = self.player1.mention if self.turn == 1 else self.player1.name
        player2_mention = self.player2.mention if self.turn == 2 else self.player2.name

        # include ELOs at the start of the game message
        elo1 = elo_manager.get_elo(self.player1, self.game_type)
        elo2 = elo_manager.get_elo(self.player2, self.game_type)

        message_content  = f"{self.player1_piece} {player1_mention} ({elo1})\n"
        message_content += f"{self.player2_piece} {player2_mention} ({elo2})\n"
        message_content += self.to_grid();

        message = await channel.send(message_content)
        id = message.id

        return id

    def get_move_format_instructions(self):
        raise NotImplementedError("get_move_format_instructions method must be implemented by subclass")

    def who_gains_elo(self):
        raise NotImplementedError("who_gains_elo method must be implemented by subclass")

    def who_loses_elo(self):
        raise NotImplementedError("who_loses_elo method must be implemented by subclass")

    def get_player_to_move(self):
        return self.player1 if self.turn == 1 else self.player2

    def get_piece_to_move(self):
        return self.player1_piece if self.turn == 1 else self.player2_piece

    def forfeit(self, player):
        if self.outcome is not None:
            return
        if player == self.player1:
            self.outcome = Outcome.Player2Win
        elif player == self.player2:
            self.outcome = Outcome.Player1Win

    async def send_gameend_message(self, channel, timed_out=False):
        print("Game between " + self.player1.name + " and " + self.player2.name + " ended.")
        # Update ELOs and get before/after values
        diff = elo_manager.update_elos_for_game(self, self.game_type)

        if self.outcome == Outcome.Player1Win or self.outcome == Outcome.Player2Win:
            winner = self.player1.mention if self.outcome == Outcome.Player1Win else self.player2.mention
            loser  = self.player2.mention if self.outcome == Outcome.Player1Win else self.player1.mention
            winner_piece = self.player1_piece if self.outcome == Outcome.Player1Win else self.player2_piece
            loser_piece  = self.player2_piece if self.outcome == Outcome.Player1Win else self.player1_piece
            message_content = f"WINNER: {winner_piece} {winner} (+{diff}) {winner_piece}\n"
            if timed_out:
                message_content += f"{loser} timed out!\n"
        else:
            message_content = f":tada: DRAW! :tada:\n"

        message_content = message_content + self.to_grid()

        await channel.send(message_content)

    def switch_turns(self):
        self.turn = 2 if self.turn == 1 else 1

    def to_grid(self):
        raise NotImplementedError("to_grid method must be implemented by subclass")

    def is_formatted_move(self, move):
        raise NotImplementedError("is_formatted_move method must be implemented by subclass")

    def is_legal_move(self, move):
        raise NotImplementedError("is_legal_move method must be implemented by subclass")

    def make_move(self, move):
        raise NotImplementedError("make_move method must be implemented by subclass")

    def resolve_outcome(self):
        raise NotImplementedError("resolve_outcome method must be implemented by subclass")
