import random
from enum import Enum
import asyncio
import json
import os
from game import Game, Outcome
from emojis import emoji_numbers, emoji_letters
from coordinate_parser import parse_single_coordinate

class GrortGame(Game):
    game_type = "Grort"
    rules = (
        "Grort: Players alternate placing pieces on the board. "
        "A piece may not be placed orthogonally adjacent to any opponent piece. "
        "When neither player can move, the player with the largest connected group of pieces wins. "
        "The pie/swap rule is active: after Player 1's first move, Player 2 may type 'swap' "
        "to switch sides instead of placing a piece. "
        "Move format: enter a coordinate such as 'a1'."
    )

    def __init__(self, player1, player2, settings):
        Game.__init__(self, player1, player2, settings)
        self.last_move = None
        self.add_reactions = False
        self.swap_enabled = True
        self.gameboard = [[self.empty_piece for w in range(self.settings["width"])] for h in range(self.settings["height"])]

    def parse_move_string(self, move):
        if not isinstance(move, str):
            return None
        return parse_single_coordinate(move.strip(), self.settings["width"], self.settings["height"])

    def get_move_format_instructions(self):
        return "Enter a coordinate (e.g., 'a1')."

    def is_formatted_move(self, move):
        if self.can_swap() and move.strip().lower() == "swap":
            return True
        return self.parse_move_string(move) is not None

    def is_legal_move(self, move):
        if self.can_swap() and move.strip().lower() == "swap":
            return True
        coord = self.parse_move_string(move)
        if coord is None:
            return False
        row, col = coord
        if self.gameboard[row][col] != self.empty_piece:
            return False
        piece_to_place = self.get_piece_to_move()
        enemy_piece = self.player1_piece if piece_to_place == self.player2_piece else self.player2_piece
        # check orthogonal adjacency for enemy pieces
        for dr, dc in [(-1,0),(1,0),(0,-1),(0,1)]:
            r, c = row + dr, col + dc
            if 0 <= r < self.settings["height"] and 0 <= c < self.settings["width"]:
                if self.gameboard[r][c] == enemy_piece:
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
        if self.can_swap() and move.strip().lower() == "swap":
            self.do_swap()
            return
        coord = self.parse_move_string(move)
        if coord is None:
            return
        row, col = coord
        if self.gameboard[row][col] == self.empty_piece:
            self.gameboard[row][col] = self.get_piece_to_move()
            self.last_move = (row, col)
            self.move_count += 1

    def get_settings_string(self):
        return f"Width: {self.settings['width']}, Height: {self.settings['height']}"

    def _has_any_legal_moves_for_piece(self, piece):
        enemy_piece = self.player1_piece if piece == self.player2_piece else self.player2_piece
        for r in range(self.settings["height"]):
            for c in range(self.settings["width"]):
                if self.gameboard[r][c] != self.empty_piece:
                    continue
                illegal = False
                for dr, dc in [(-1,0),(1,0),(0,-1),(0,1)]:
                    rr, cc = r + dr, c + dc
                    if 0 <= rr < self.settings["height"] and 0 <= cc < self.settings["width"]:
                        if self.gameboard[rr][cc] == enemy_piece:
                            illegal = True
                            break
                if not illegal:
                    return True
        return False

    def _largest_group_size(self, piece):
        visited = [[False for _ in range(self.settings["width"])] for _ in range(self.settings["height"])]
        max_size = 0
        for r in range(self.settings["height"]):
            for c in range(self.settings["width"]):
                if visited[r][c] or self.gameboard[r][c] != piece:
                    continue
                # BFS/DFS to count connected component size (orthogonal connectivity)
                stack = [(r, c)]
                visited[r][c] = True
                size = 0
                while stack:
                    cr, cc = stack.pop()
                    size += 1
                    for dr, dc in [(-1,0),(1,0),(0,-1),(0,1)]:
                        nr, nc = cr + dr, cc + dc
                        if 0 <= nr < self.settings["height"] and 0 <= nc < self.settings["width"]:
                            if not visited[nr][nc] and self.gameboard[nr][nc] == piece:
                                visited[nr][nc] = True
                                stack.append((nr, nc))
                if size > max_size:
                    max_size = size
        return max_size

    def resolve_outcome(self):
        if self.last_move is None:
            self.outcome = None
            return

        last_row, last_col = self.last_move
        last_piece = self.gameboard[last_row][last_col]
        opponent_piece = self.player1_piece if last_piece == self.player2_piece else self.player2_piece

        # If opponent still has legal moves, game continues
        if self._has_any_legal_moves_for_piece(opponent_piece):
            self.outcome = None
            return

        elif self._has_any_legal_moves_for_piece(last_piece):
            self.switch_turn()
            self.outcome = None
            return

        # Game is over (opponent has no legal moves). Determine winner by largest connected group (Go-style connectivity).
        size1 = self._largest_group_size(self.player1_piece)
        size2 = self._largest_group_size(self.player2_piece)

        if size1 > size2:
            self.outcome = Outcome.Player1Win
        elif size2 > size1:
            self.outcome = Outcome.Player2Win
        else:
            # tie -> no winner
            self.outcome = None

correction_message = "Invalid command format. Please optionally add -w [width], and -h [height]."

def parse_settings(args):
    mnk = [5, 5]

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
