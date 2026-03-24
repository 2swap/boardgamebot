import random
from enum import Enum
import asyncio
import json
import os
from game import Game, Outcome
from emojis import emojis

class Connect4Game(Game):
    def __init__(self, player1, player2, settings):
        Game.__init__(self, player1, player2, settings)
        self.last_move = None
        self.game_type = "Connect 4"
        self.player1_piece = "🔴"
        self.player2_piece = "🟡"
        self.empty_piece = "⚪"
        self.add_reactions = True
        self.gameboard = [[self.empty_piece for w in range(self.settings["width"])] for h in range(self.settings["height"])]

    def is_formatted_move(self, move):
        return move.isdigit() and int(move) >= 1 and int(move) <= self.settings["width"]
    
    def is_legal_move(self, move):
        move = int(move) - 1
        return self.gameboard[0][move] == self.empty_piece
    
    def who_gains_elo(self):
        if self.outcome == Outcome.Player1Win:
            return None
        else:
            return self.player2

    def who_loses_elo(self):
        if self.outcome == Outcome.Player1Win:
            return None
        else:
            return self.player1

    def to_grid(self):
        string_of_grid = "\n";
        for num in range(1, self.settings["width"] + 1):
            string_of_grid += emojis[num - 1] + "\u200B"
        string_of_grid += "\n"
        for h in range(self.settings["height"]):
            for w in range(self.settings["width"]):
                string_of_grid += self.gameboard[h][w]
            string_of_grid += "\n"

        return string_of_grid

    def make_move(self, move):
        # if not an int, fail out
        if not move.isdigit():
            return
        move = int(move) - 1
        for i in range(self.settings["height"] - 1, -1, -1):
            if(self.gameboard[i][move] == self.empty_piece):
                self.gameboard[i][move] = self.get_piece_to_move()
                self.last_move = (i, move)
                break

    def get_settings_string(self):
        return f"Width: {self.width}, Height: {self.height}, Connect: {self.connect}"

    def resolve_outcome(self):
        if self.last_move is None:
            self.outcome = None
            return

        last_row, last_col = self.last_move
        player_piece = self.gameboard[last_row][last_col]

        directions = [(0, 1), (1, 0), (1, 1), (1, -1)]
        for dr, dc in directions:
            count = 1
            for d in [1, -1]:
                r, c = last_row + d * dr, last_col + d * dc
                while 0 <= r < self.settings["height"] and 0 <= c < self.settings["width"] and self.gameboard[r][c] == player_piece:
                    count += 1
                    r += d * dr
                    c += d * dc

            if count >= self.settings["connect_n"]:
                self.outcome = Outcome.Player1Win if player_piece == self.player1_piece else Outcome.Player2Win
                return

        if all(self.gameboard[0][c] != self.empty_piece for c in range(self.settings["width"])):
            self.outcome = Outcome.Tie
            return

        self.outcome = None

correction_message = "Invalid command format. Please use \"!challenge @[player]\" and optionally add -w [width], -h [height], and -k [connection length]."

def parse_settings(args):
    mnk = [7, 6, 4]

    parsed_settings = {}

    for mnk_index, flag in enumerate(["-w", "-h", "-k"]):
        if flag in args:
            index = args.index(flag)
            if index + 1 < len(args):
                try:
                    mnk[mnk_index] = int(args[index + 1])
                    args.pop(index)
                    args.pop(index)
                except ValueError:
                    return (False, {}, correction_message + f" Invalid integer value for {flag}.")
            else:
                return (False, {}, correction_message + f" Missing value for {flag}.")

    if len(args) > 0:
        return (False, {}, correction_message + " Unrecognized extra arguments: " + " ".join(args))

    for param in mnk:
        if param <= 0 or param > 15:
            return (False, {}, "Width, height, and connection length must be between 1 and 15.")
            break

    parsed_settings["width"] = mnk[0]
    parsed_settings["height"] = mnk[1]
    parsed_settings["connect_n"] = mnk[2]

    return (True, parsed_settings, "")

def get_settings_string(settings):
    return f"Width: {settings['width']}, Height: {settings['height']}, Connect: {settings['connect_n']}"
