import random
from enum import Enum
import asyncio
import json
import os
from game import Game, Outcome
from emojis import emojis, emoji_numbers, emoji_letters
from coordinate_parser import parse_single_coordinate

class GomokuGame(Game):
    rules = (
        "Gomoku: Players alternate placing pieces on the board. "
        "The first player to form an unbroken line of the required length "
        "(horizontally, vertically, or diagonally) wins. "
        "If the board fills with no winner, the game is a draw. "
        "Move format: enter a coordinate such as 'a1'."
    )

    def __init__(self, player1, player2, settings):
        Game.__init__(self, player1, player2, settings)
        self.last_move = None
        self.game_type = "Gomoku"
        self.add_reactions = False
        self.gameboard = [[self.empty_piece for w in range(self.settings["width"])] for h in range(self.settings["height"])]

    def parse_move_string(self, move):
        if not isinstance(move, str):
            return None
        return parse_single_coordinate(move.strip(), self.settings["width"], self.settings["height"])

    def get_move_format_instructions(self):
        return "Enter a coordinate (e.g., 'a1')."

    def is_formatted_move(self, move):
        return self.parse_move_string(move) is not None

    def is_legal_move(self, move):
        coord = self.parse_move_string(move)
        if coord is None:
            return False
        row, col = coord
        if self.gameboard[row][col] != self.empty_piece:
            return False
        return True
    
    def who_gains_elo(self):
        if self.outcome == Outcome.Player1Win:
            return self.player1
        elif self.outcome == Outcome.Player2Win:
            return self.player2
        else:
            return None

    def who_loses_elo(self):
        if self.outcome == Outcome.Player1Win:
            return self.player2
        elif self.outcome == Outcome.Player2Win:
            return self.player1
        else:
            return None

    def to_grid(self):
        string_of_grid = "\n"
        # header: blank corner then column number emojis
        string_of_grid += ":black_large_square:"
        for num in range(1, self.settings["width"] + 1):
            string_of_grid += emoji_letters[num - 1] + "\u200B"
        string_of_grid += "\n"
        for h in range(self.settings["height"]):
            # row number emoji at start of each row
            string_of_grid += emoji_numbers[h] + "\u200B"
            for w in range(self.settings["width"]):
                string_of_grid += self.gameboard[h][w]
            string_of_grid += "\n"

        return string_of_grid

    def make_move(self, move):
        coord = self.parse_move_string(move)
        if coord is None:
            return
        row, col = coord
        if self.gameboard[row][col] == self.empty_piece:
            self.gameboard[row][col] = self.get_piece_to_move()
            self.last_move = (row, col)

    def get_settings_string(self):
        return f"Width: {self.settings['width']}, Height: {self.settings['height']}"

    def _has_any_legal_moves_for_piece(self, piece):
        # retained for compatibility; Gomoku legal move is simply any empty cell
        for r in range(self.settings["height"]):
            for c in range(self.settings["width"]):
                if self.gameboard[r][c] == self.empty_piece:
                    return True
        return False

    def resolve_outcome(self):
        if self.last_move is None:
            self.outcome = None
            return

        last_row, last_col = self.last_move
        last_piece = self.gameboard[last_row][last_col]

        # directions: horizontal, vertical, diag down-right, diag up-right
        directions = [ (0,1), (1,0), (1,1), (-1,1) ]
        for dr, dc in directions:
            count = 1
            # forward
            r, c = last_row + dr, last_col + dc
            while 0 <= r < self.settings["height"] and 0 <= c < self.settings["width"] and self.gameboard[r][c] == last_piece:
                count += 1
                r += dr
                c += dc
            # backward
            r, c = last_row - dr, last_col - dc
            while 0 <= r < self.settings["height"] and 0 <= c < self.settings["width"] and self.gameboard[r][c] == last_piece:
                count += 1
                r -= dr
                c -= dc
            if count >= self.settings["connection_k"]:
                if last_piece == self.player1_piece:
                    self.outcome = Outcome.Player1Win
                else:
                    self.outcome = Outcome.Player2Win
                return

        # check for draw (board full)
        for r in range(self.settings["height"]):
            for c in range(self.settings["width"]):
                if self.gameboard[r][c] == self.empty_piece:
                    self.outcome = None
                    return

        self.outcome = Outcome.Tie

correction_message = "Invalid command format. Please optionally add -w [width], -h [height], and -k [connectivity]."

def parse_settings(args):
    mnk = [15, 15, 5]

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
            return (False, {}, "Width, height, and connectivity must be between 1 and 15.")
            break

    parsed_settings["width"] = mnk[0]
    parsed_settings["height"] = mnk[1]
    parsed_settings["connection_k"] = mnk[2]

    if parsed_settings["connection_k"] < parsed_settings["width"] and parsed_settings["connection_k"] < parsed_settings["height"]:
        return (False, {}, "Error: Connection length exceeds board size!")

    return (True, parsed_settings, "")

def get_settings_string(settings):
    return f"Width: {settings['width']}, Height: {settings['height']}, Connectivity: {settings['connection_k']}"
