import random
from enum import Enum
import asyncio
import json
import os
from game import Game, Outcome
from emojis import emojis, emoji_numbers, emoji_letters

class HexTicTacToeGame(Game):
    def __init__(self, player1, player2, settings):
        Game.__init__(self, player1, player2, settings)
        self.last_move = None
        self.game_type = "Hexagonal Tic Tac Toe"
        self.add_reactions = False
        self.gameboard = [[self.empty_piece for w in range(self.settings["width"])] for h in range(self.settings["height"])]
        # Place Player 1's first move at the central spot upfront (as per Connect-6 rules)
        center_row = self.settings["height"] // 2
        center_col = self.settings["width"] // 2
        self.gameboard[center_row][center_col] = self.player1_piece
        self.last_move = (center_row, center_col)
        self.switch_turns()

    def parse_move_string(self, move):
        if not isinstance(move, str):
            return None
        move = move.strip().lower()
        if len(move) == 0:
            return None
        parts = move.split()
        if len(parts) == 0 or len(parts) > 2:
            return None

        def parse_single(p):
            if len(p) < 2:
                return None
            col_char = p[0]
            if col_char < 'a' or col_char > 'z':
                return None
            try:
                row_num = int(p[1:])
            except ValueError:
                return None
            col = ord(col_char) - ord('a')
            row = row_num - 1
            if 0 <= col < self.settings["width"] and 0 <= row < self.settings["height"]:
                return (row, col)
            return None

        coords = []
        for p in parts:
            coord = parse_single(p)
            if coord is None:
                return None
            coords.append(coord)

        if len(coords) == 1:
            return coords[0]
        return coords

    def is_formatted_move(self, move):
        return self.parse_move_string(move) is not None

    def is_legal_move(self, move):
        coord = self.parse_move_string(move)
        if coord is None:
            return False
        if not isinstance(coord, list):
            return False
        if len(coord) != 2:
            return False
        (r1, c1), (r2, c2) = coord[0], coord[1]
        # distinct squares
        if r1 == r2 and c1 == c2:
            return False
        # both must be empty
        if self.gameboard[r1][c1] != self.empty_piece or self.gameboard[r2][c2] != self.empty_piece:
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
        # header: blank corner then column letter emojis
        string_of_grid += "⬛"
        for num in range(1, self.settings["width"] + 1):
            string_of_grid += emoji_letters[num - 1] + " "
        string_of_grid += "\n"
        for h in range(self.settings["height"]):
            # row number emoji at start of each row
            string_of_grid += emoji_numbers[h] + "\u200B"
            # Align pieces to rhombus shape
            string_of_grid += "--" * (h+1)
            for w in range(self.settings["width"]):
                string_of_grid += self.gameboard[h][w] + " "
            string_of_grid += "\n"

        return string_of_grid

    def make_move(self, move):
        coord = self.parse_move_string(move)
        if coord is None:
            return

        # Expecting a pair of moves
        if isinstance(coord, list):
            first, second = coord[0], coord[1]
            (r1, c1), (r2, c2) = first, second
            # ensure both empty and distinct
            if (r1 == r2 and c1 == c2) or self.gameboard[r1][c1] != self.empty_piece or self.gameboard[r2][c2] != self.empty_piece:
                return
            # place first then second; both belong to the same player for that turn
            piece = self.get_piece_to_move()
            self.gameboard[r1][c1] = piece
            # check for immediate win after first placement
            self.last_move = (r1, c1)
            self.resolve_outcome()
            if self.outcome is not None:
                return
            self.gameboard[r2][c2] = piece
            # set last_move to both moves for outcome checking
            self.last_move = [ (r1, c1), (r2, c2) ]

    def get_settings_string(self):
        return f"Width: {self.settings['width']}, Height: {self.settings['height']}, Connect: {self.settings['connection_k']}"

    def _has_any_legal_moves_for_piece(self, piece):
        # retained for compatibility; legal move is simply any empty cell
        for r in range(self.settings["height"]):
            for c in range(self.settings["width"]):
                if self.gameboard[r][c] == self.empty_piece:
                    return True
        return False

    def resolve_outcome(self):
        if self.last_move is None:
            self.outcome = None
            return

        # allow last_move to be a single tuple or a list of tuples
        moves_to_check = []
        if isinstance(self.last_move, list):
            moves_to_check = self.last_move
        elif isinstance(self.last_move, tuple):
            # could be a single (row,col)
            if len(self.last_move) == 2 and isinstance(self.last_move[0], int):
                moves_to_check = [self.last_move]
            else:
                moves_to_check = list(self.last_move)
        else:
            self.outcome = None
            return

        for move in moves_to_check:
            last_row, last_col = move
            last_piece = self.gameboard[last_row][last_col]

            # directions for hex grid (as represented on a square array with extra diagonal): check three axes
            directions = [ (0,1), (1,0), (1,-1) ]
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

        self.outcome = Outcome.tie

correction_message = "Invalid command format. Please use \"!challenge @[player]\" and optionally add -w [width], and -h [height]."

def parse_settings(args):
    mnk = [13, 13, 6]

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
            return (False, {}, "Width and height must be between 1 and 25.")
            break

    parsed_settings["width"] = mnk[0]
    parsed_settings["height"] = mnk[1]
    parsed_settings["connection_k"] = mnk[2]

    return (True, parsed_settings, "")

def get_settings_string(settings):
    return f"Width: {settings['width']}, Height: {settings['height']}, Connect: {settings['connection_k']}"
