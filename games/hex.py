import random
from enum import Enum
import asyncio
import json
import os
from game import Game, Outcome
from emojis import emojis, emoji_numbers, emoji_letters

class HexGame(Game):
    def __init__(self, player1, player2, settings):
        Game.__init__(self, player1, player2, settings)
        self.last_move = None
        self.game_type = "Hex"
        self.add_reactions = False
        self.gameboard = [[self.empty_piece for w in range(self.settings["width"])] for h in range(self.settings["height"])]

    def parse_move_string(self, move):
        if not isinstance(move, str):
            return None
        move = move.strip().lower()
        if len(move) == 0:
            return None
        parts = move.split()
        if len(parts) != 1:
            return None

        p = parts[0]
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

    def is_formatted_move(self, move):
        return self.parse_move_string(move) is not None

    def is_legal_move(self, move):
        coord = self.parse_move_string(move)
        if coord is None:
            return False
        if not isinstance(coord, tuple):
            return False
        r, c = coord
        if self.gameboard[r][c] != self.empty_piece:
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
        string_of_grid += "⬛⬛"
        for num in range(1, self.settings["width"] + 1):
            string_of_grid += emoji_letters[num - 1] + " "
        string_of_grid += "⬛\n"
        for h in range(self.settings["height"]+2):
            # row number emoji at start of each row
            is_top_or_bottom = (h == 0 or h == self.settings["height"] + 1)
            if is_top_or_bottom:
                string_of_grid += "⬛"
            else:
                string_of_grid += emoji_numbers[h-1] + "\u200B"
            # Align pieces to rhombus shape
            string_of_grid += "--" * (h+1) + self.player1_piece
            for w in range(self.settings["width"]):
                string_of_grid += (self.gameboard[h - 1][w] if not is_top_or_bottom else self.player2_piece) + " "
            string_of_grid += self.player1_piece + "\n"

        return string_of_grid

    def make_move(self, move):
        coord = self.parse_move_string(move)
        if coord is None:
            return

        if not isinstance(coord, tuple):
            return

        r, c = coord
        if self.gameboard[r][c] != self.empty_piece:
            return

        piece = self.get_piece_to_move()
        self.gameboard[r][c] = piece
        self.last_move = (r, c)
        self.resolve_outcome()

    def get_settings_string(self):
        return f"Width: {self.settings['width']}, Height: {self.settings['height']}"

    def _has_any_legal_moves_for_piece(self, piece):
        # any empty cell is a legal move
        for r in range(self.settings["height"]):
            for c in range(self.settings["width"]):
                if self.gameboard[r][c] == self.empty_piece:
                    return True
        return False

    def resolve_outcome(self):
        # In Hex, check if either player has a connecting path between their sides.
        h = self.settings["height"]
        w = self.settings["width"]

        def connected(piece):
            visited = set()
            stack = []
            if piece == self.player1_piece:
                # Player 1 connects left (col=0) to right (col=w-1)
                for r in range(h):
                    if self.gameboard[r][0] == piece:
                        stack.append((r, 0))
                        if 0 == w-1:
                            return True
                target = lambda rr, cc: cc == w - 1
            else:
                # Player 2 connects top (row=0) to bottom (row=h-1)
                for c in range(w):
                    if self.gameboard[0][c] == piece:
                        stack.append((0, c))
                        if 0 == h-1:
                            return True
                target = lambda rr, cc: rr == h - 1

            # neighbors in hex grid represented on 2D array
            neighbors = [(-1,0),(1,0),(0,-1),(0,1),(-1,1),(1,-1)]
            while stack:
                r, c = stack.pop()
                if (r, c) in visited:
                    continue
                visited.add((r, c))
                if target(r, c):
                    return True
                for dr, dc in neighbors:
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < h and 0 <= nc < w and self.gameboard[nr][nc] == piece and (nr, nc) not in visited:
                        stack.append((nr, nc))
            return False

        if connected(self.player1_piece):
            self.outcome = Outcome.Player1Win
            return
        if connected(self.player2_piece):
            self.outcome = Outcome.Player2Win
            return

        # No winner yet; check for full board (though in Hex this should imply a winner)
        for r in range(h):
            for c in range(w):
                if self.gameboard[r][c] == self.empty_piece:
                    self.outcome = None
                    return

        self.outcome = Outcome.tie

correction_message = "Invalid command format. Please use \"!challenge @[player]\" and optionally add -w [width], and -h [height]."

def parse_settings(args):
    mnk = [11, 11]

    parsed_settings = {}

    for mnk_index, flag in enumerate(["-w", "-h"]):
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
            return (False, {}, "Width and height must be between 1 and 15.")
            break

    parsed_settings["width"] = mnk[0]
    parsed_settings["height"] = mnk[1]

    return (True, parsed_settings, "")

def get_settings_string(settings):
    return f"Width: {settings['width']}, Height: {settings['height']}"
