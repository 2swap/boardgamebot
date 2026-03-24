import random
from enum import Enum
import asyncio
import json
import os
from game import Game, Outcome
from emojis import emojis, emoji_numbers, emoji_letters

class OthelloGame(Game):
    def __init__(self, player1, player2, settings):
        Game.__init__(self, player1, player2, settings)
        self.last_move = None
        self.game_type = "Othello"
        self.empty_piece = "🟢"
        self.add_reactions = False
        self.gameboard = [[self.empty_piece for w in range(self.settings["width"])] for h in range(self.settings["height"])]
        # initialize center four pieces for Othello if board large enough
        h = self.settings["height"]
        w = self.settings["width"]
        if h >= 2 and w >= 2:
            mid_h = h // 2
            mid_w = w // 2
            # standard starting positions: two pieces for each player in center
            # assign player2 to (mid_h-1, mid_w-1) and (mid_h, mid_w)
            # assign player1 to (mid_h-1, mid_w) and (mid_h, mid_w-1)
            try:
                self.gameboard[mid_h-1][mid_w-1] = self.player2_piece
                self.gameboard[mid_h][mid_w] = self.player2_piece
                self.gameboard[mid_h-1][mid_w] = self.player1_piece
                self.gameboard[mid_h][mid_w-1] = self.player1_piece
            except Exception:
                # if indices out of range for small boards, ignore
                pass

    def parse_move_string(self, move):
        if not isinstance(move, str):
            return None
        move = move.strip().lower()
        if len(move) < 2:
            return None
        col_char = move[0]
        if col_char < 'a' or col_char > 'z':
            return None
        try:
            row_num = int(move[1:])
        except ValueError:
            return None
        col = ord(col_char) - ord('a')
        row = row_num - 1
        if 0 <= col < self.settings["width"] and 0 <= row < self.settings["height"]:
            return (row, col)
        return None

    def _flips_for_move(self, row, col, piece):
        if self.gameboard[row][col] != self.empty_piece:
            return []
        enemy_piece = self.player1_piece if piece == self.player2_piece else self.player2_piece
        flips = []
        directions = [(-1,0),(1,0),(0,-1),(0,1),(-1,-1),(-1,1),(1,-1),(1,1)]
        for dr, dc in directions:
            r, c = row + dr, col + dc
            path = []
            while 0 <= r < self.settings["height"] and 0 <= c < self.settings["width"] and self.gameboard[r][c] == enemy_piece:
                path.append((r, c))
                r += dr
                c += dc
            if path and 0 <= r < self.settings["height"] and 0 <= c < self.settings["width"] and self.gameboard[r][c] == piece:
                flips.extend(path)
        return flips

    def is_formatted_move(self, move):
        return self.parse_move_string(move) is not None

    def is_legal_move(self, move):
        coord = self.parse_move_string(move)
        if coord is None:
            return False
        row, col = coord
        piece_to_place = self.get_piece_to_move()
        flips = self._flips_for_move(row, col, piece_to_place)
        return len(flips) > 0

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
        piece = self.get_piece_to_move()
        flips = self._flips_for_move(row, col, piece)
        if not flips:
            return
        self.gameboard[row][col] = piece
        for r, c in flips:
            self.gameboard[r][c] = piece
        self.last_move = (row, col)

    def get_settings_string(self):
        return f"Width: {self.settings['width']}, Height: {self.settings['height']}"

    def _has_any_legal_moves_for_piece(self, piece):
        for r in range(self.settings["height"]):
            for c in range(self.settings["width"]):
                if self.gameboard[r][c] != self.empty_piece:
                    continue
                if len(self._flips_for_move(r, c, piece)) > 0:
                    return True
        return False

    def resolve_outcome(self):
        # Game ends when neither player has a legal move
        p1_moves = self._has_any_legal_moves_for_piece(self.player1_piece)
        p2_moves = self._has_any_legal_moves_for_piece(self.player2_piece)
        if not p1_moves and not p2_moves:
            # count pieces
            p1_count = 0
            p2_count = 0
            for r in range(self.settings["height"]):
                for c in range(self.settings["width"]):
                    if self.gameboard[r][c] == self.player1_piece:
                        p1_count += 1
                    elif self.gameboard[r][c] == self.player2_piece:
                        p2_count += 1
            if p1_count > p2_count:
                self.outcome = Outcome.Player1Win
            elif p2_count > p1_count:
                self.outcome = Outcome.Player2Win
            else:
                self.outcome = Outcome.Tie
            return
        self.outcome = None

correction_message = "Invalid command format. Please use \"!challenge @[player]\" and optionally add -w [width], and -h [height]."

def parse_settings(args):
    mnk = [8, 8]

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
        if param <= 0 or param > 9:
            return (False, {}, "Width and height must be between 1 and 9.")
            break

    parsed_settings["width"] = mnk[0]
    parsed_settings["height"] = mnk[1]

    return (True, parsed_settings, "")

def get_settings_string(settings):
    return f"Width: {settings['width']}, Height: {settings['height']}"
