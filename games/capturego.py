import random
from enum import Enum
import asyncio
import json
import os
from game import Game, Outcome
from emojis import emoji_numbers, emoji_letters
from coordinate_parser import parse_single_coordinate

class CaptureGoGame(Game):
    game_type = "Capture Go"
    rules = (
        "Capture Go: Players alternate placing pieces on the board. "
        "If a move captures any opponent stones (removes them by surrounding them so they have no liberties), "
        "that player immediately wins. "
        "Move format: enter a coordinate such as 'a1'."
    )

    def __init__(self, player1, player2, settings):
        Game.__init__(self, player1, player2, settings)
        self.last_move = None
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

    def _flood_fill_group(self, board, start_row, start_col):
        piece = board[start_row][start_col]
        if piece == self.empty_piece:
            return ([], 0)
        visited = set()
        stack = [(start_row, start_col)]
        group = []
        liberties = set()
        while stack:
            r0, c0 = stack.pop()
            if (r0, c0) in visited:
                continue
            visited.add((r0, c0))
            group.append((r0, c0))
            for ddr, ddc in [(-1,0),(1,0),(0,-1),(0,1)]:
                r1, c1 = r0 + ddr, c0 + ddc
                if not (0 <= r1 < self.settings["height"] and 0 <= c1 < self.settings["width"]):
                    continue
                if board[r1][c1] == self.empty_piece:
                    liberties.add((r1, c1))
                elif board[r1][c1] == piece and (r1, c1) not in visited:
                    stack.append((r1, c1))
        return (group, len(liberties))

    def is_legal_move(self, move):
        coord = self.parse_move_string(move)
        if coord is None:
            return False
        row, col = coord
        if self.gameboard[row][col] != self.empty_piece:
            return False

        # simulate the move on a copy of the board to detect suicide vs captures
        board_copy = [r.copy() for r in self.gameboard]
        piece = self.get_piece_to_move()
        opponent_piece = self.player1_piece if piece == self.player2_piece else self.player2_piece
        board_copy[row][col] = piece

        # check for captures of adjacent opponent groups
        visited = set()
        captured_any = False
        for dr, dc in [(-1,0),(1,0),(0,-1),(0,1)]:
            nr, nc = row + dr, col + dc
            if not (0 <= nr < self.settings["height"] and 0 <= nc < self.settings["width"]):
                continue
            if board_copy[nr][nc] != opponent_piece:
                continue
            if (nr, nc) in visited:
                continue
            group, liberties = self._flood_fill_group(board_copy, nr, nc)
            for pos in group:
                visited.add(pos)
            if liberties == 0:
                captured_any = True
                for (r_cap, c_cap) in group:
                    board_copy[r_cap][c_cap] = self.empty_piece

        # If any opponent stones would be captured, the move is legal even if it would otherwise be suicidal
        if captured_any:
            return True

        # Otherwise, check liberties of the group containing the placed piece
        group, liberties = self._flood_fill_group(board_copy, row, col)
        if liberties == 0:
            return False

        return True
    
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
            piece = self.get_piece_to_move()
            self.gameboard[row][col] = piece
            self.last_move = (row, col)

            # Check for captures of adjacent opponent groups (orthogonal neighbors)
            opponent_piece = self.player1_piece if piece == self.player2_piece else self.player2_piece
            captured_total = 0

            visited = set()
            for dr, dc in [(-1,0),(1,0),(0,-1),(0,1)]:
                nr, nc = row + dr, col + dc
                if not (0 <= nr < self.settings["height"] and 0 <= nc < self.settings["width"]):
                    continue
                if self.gameboard[nr][nc] != opponent_piece:
                    continue
                if (nr, nc) in visited:
                    continue

                group, liberties = self._flood_fill_group(self.gameboard, nr, nc)
                for pos in group:
                    visited.add(pos)

                # If no liberties, place X emojis there
                if liberties == 0:
                    for (r_cap, c_cap) in group:
                        self.gameboard[r_cap][c_cap] = ":x:"
                    captured_total += len(group)

            if captured_total > 0:
                # current mover wins immediately
                if piece == self.player1_piece:
                    self.outcome = Outcome.Player1Win
                else:
                    self.outcome = Outcome.Player2Win

    def get_settings_string(self):
        return f"Width: {self.settings['width']}, Height: {self.settings['height']}"

    def resolve_outcome(self):
        # If a capture occurred during make_move, outcome will already be set
        if self.outcome is not None:
            return

        # check for draw (board full)
        for r in range(self.settings["height"]):
            for c in range(self.settings["width"]):
                if self.gameboard[r][c] == self.empty_piece:
                    self.outcome = None
                    return

        self.outcome = Outcome.Tie

correction_message = "Invalid command format. Please optionally add -w [width] and -h [height]."

def parse_settings(args):
    wh = [9, 9]

    parsed_settings = {}

    for wh_index, flag in enumerate(["-w", "-h"]):
        if flag in args:
            index = args.index(flag)
            if index + 1 < len(args):
                try:
                    wh[wh_index] = int(args[index + 1])
                    args.pop(index)
                    args.pop(index)
                except ValueError:
                    return (False, {}, correction_message + f" Invalid integer value for {flag}.")
            else:
                return (False, {}, correction_message + f" Missing value for {flag}.")

    if len(args) > 0:
        return (False, {}, correction_message + " Unrecognized extra arguments: " + " ".join(args))

    for param in wh:
        if param <= 0 or param > 15:
            return (False, {}, "Width and height must be between 1 and 15.")
            break

    parsed_settings["width"] = wh[0]
    parsed_settings["height"] = wh[1]

    return (True, parsed_settings, "")

def get_settings_string(settings):
    return f"Width: {settings['width']}, Height: {settings['height']}"
