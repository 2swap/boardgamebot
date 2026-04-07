import random
from enum import Enum
import asyncio
import json
import os
from game import Game, Outcome
from emojis import emoji_numbers, emoji_letters

class MancalaGame(Game):
    rules = (
        "Mancala (American Kalah) is a two-player strategy game where the objective is to collect more stones in your store than your opponent. The board consists of two rows of pits, each containing a certain number of stones, and two stores (one for each player). Players take turns selecting a pit on their side and distributing its stones counterclockwise into subsequent pits and their own store, but not the opponent's store. If the last stone lands in an empty pit on the player's side which is opposite a non-empty pit on the opponent's side, they capture that stone and any stones in the opposite pit. If the last stone lands in the player's store, they get an extra turn. The game ends when all pits on one side are empty, at which point the remaining stones on the other side are collected into that player's store. The player with the most stones in their store wins."
    )

    def __init__(self, player1, player2, settings):
        Game.__init__(self, player1, player2, settings)
        self.last_move = None
        self.game_type = "Mancala (American Kalah)"
        self.add_reactions = False
        # settings: pits per side and stones per pit
        self.pits = self.settings.get("pits", 6)
        self.stones = self.settings.get("stones", 4)
        # board layout:
        # indices 0..pits-1 -> player1 pits (left to right)
        # index pits -> player1 store
        # indices pits+1 .. 2*pits -> player2 pits (left to right)
        # index 2*pits+1 -> player2 store
        total_slots = 2 * self.pits + 2
        self.player1_store = self.pits
        self.player2_store = 2 * self.pits + 1
        # initialize pits with stones, stores with 0
        self.gameboard = [self.stones for _ in range(total_slots)]
        self.gameboard[self.player1_store] = 0
        self.gameboard[self.player2_store] = 0

    def get_move_format_instructions(self):
        # Accept moves as letters A.. up to the number of pits.
        return f"Select an option using letters A to {chr(ord('A') + self.pits - 1)} corresponding to the pits on your side (left to right)."

    def is_formatted_move(self, move):
        # Accept a single letter up to the number of pits
        if not isinstance(move, str) or len(move) == 0:
            return False
        if len(move) == 1 and move.isalpha():
            idx = ord(move.upper()) - ord('A')
            return 0 <= idx < self.pits
        return False

    def _letter_to_move_idx(self, move):
        # returns 0-based pit index for the player's side (0..pits-1) or None
        if len(move) == 1 and move.isalpha():
            return ord(move.upper()) - ord('A')
        return None

    def is_legal_move(self, move):
        move_idx = self._letter_to_move_idx(move)
        if move_idx is None:
            return False
        if self.turn == 1:
            pit_idx = move_idx
        else:
            pit_idx = self.pits + 1 + move_idx
        return self.gameboard[pit_idx] > 0

    def to_grid(self):
        # Emoji-only, monospace interface.
        # Each pit/store is represented as ORANGE + two emoji digits (tens, ones).
        ORANGE = "🟧"

        def two_digit_emojis(n):
            # cap at 99, represent as two digits using emoji_numbers[0..9]
            if n < 0:
                n = 0
            if n > 99:
                n = 99
            tens = n // 10
            ones = n % 10
            # Prepend with zero emoji
            modified_emoji_numbers = ["0️⃣"] + emoji_numbers
            # ensure indices within emoji_numbers available range
            tens_idx = min(tens, len(emoji_numbers) - 1)
            ones_idx = min(ones, len(emoji_numbers) - 1)
            tens_emoji = modified_emoji_numbers[tens_idx]
            if tens == 0:
                tens_emoji = ORANGE
            ones_emoji = modified_emoji_numbers[ones_idx]
            return tens_emoji + ones_emoji

        # build tokens for player1 pits (left to right) and player2 pits (left to right)
        p1_tokens = []
        p2_tokens = []
        for i in range(self.pits):
            p1_tokens.append(ORANGE + two_digit_emojis(self.gameboard[i]))
        for i in range(self.pits):
            p2_tokens.append(ORANGE + two_digit_emojis(self.gameboard[self.pits + 1 + i]))

        # stores
        left_store_token = ORANGE + two_digit_emojis(self.gameboard[self.player2_store])
        right_store_token = ORANGE + two_digit_emojis(self.gameboard[self.player1_store])

        # top row shows player2 pits reversed
        p2_rev = list(reversed(p2_tokens))
        top_row = ORANGE * 3 + ''.join(p2_rev) + ORANGE * 4
        # middle row shows stores with filler oranges to match width (3 emojis per pit)
        filler = ORANGE * (3 * self.pits)
        stores_row = left_store_token + filler + right_store_token + ORANGE
        # bottom row shows player1 pits left to right
        bottom_row = ORANGE * 3 + ''.join(p1_tokens) + ORANGE * 4

        # labels for current player: only shown for the player whose turn it is.
        labels_row = ""
        # label token will be ORANGE + letter_emoji + ORANGE to match width
        def label_token_for(idx):
            letter = emoji_letters[idx] if idx < len(emoji_letters) else emoji_letters[-1]
            return ORANGE + letter + ORANGE

        blank_row = ORANGE * (3 * self.pits + 7)
        if self.turn == 1:
            labels = [label_token_for(i) for i in range(self.pits)]
            labels_row = ORANGE * 3 + ''.join(labels) + ORANGE * 4
            grid = blank_row + "\n" + top_row + "\n" + stores_row + "\n" + bottom_row + "\n" + labels_row
        else:
            labels = [label_token_for(i) for i in range(self.pits - 1, -1, -1)]
            labels_row = ORANGE * 3 + ''.join(labels) + ORANGE * 4
            grid = labels_row + "\n" + top_row + "\n" + stores_row + "\n" + bottom_row + "\n" + blank_row

        return grid

    def make_move(self, move):
        # move is a letter A.. mapped to pit index 0..pits-1 or the corresponding emoji letter
        if not self.is_formatted_move(move):
            return
        move_idx = self._letter_to_move_idx(move)
        if move_idx is None:
            return
        if self.turn == 1:
            pit_idx = move_idx
            own_store = self.player1_store
            opponent_store = self.player2_store
            own_side = set(range(0, self.pits))
        else:
            pit_idx = self.pits + 1 + move_idx
            own_store = self.player2_store
            opponent_store = self.player1_store
            own_side = set(range(self.pits + 1, self.pits + 1 + self.pits))

        stones = self.gameboard[pit_idx]
        if stones == 0:
            return
        self.gameboard[pit_idx] = 0
        idx = pit_idx
        total_slots = len(self.gameboard)
        while stones > 0:
            idx = (idx + 1) % total_slots
            # skip opponent's store
            if idx == opponent_store:
                continue
            self.gameboard[idx] += 1
            stones -= 1

        self.last_move = idx

        # check for capture: last stone landed in an empty pit on player's side (and not a store)
        if idx in own_side and self.gameboard[idx] == 1:
            opposite_idx = (self.player2_store - 1) - idx if self.turn == 1 else (self.player1_store - 1) - (idx - (self.pits + 1))
            # compute opposite properly:
            # For player1 idx in 0..pits-1, opposite is (pits+1 .. pits + pits) mirrored:
            if self.turn == 1:
                opposite_idx = self.pits + 1 + (self.pits - 1 - idx)
            else:
                opposite_idx = (self.pits - 1 - (idx - (self.pits + 1)))
            if 0 <= opposite_idx < total_slots:
                captured = self.gameboard[opposite_idx]
                if captured > 0:
                    # capture the last stone plus opposite stones into own store
                    self.gameboard[own_store] += captured + self.gameboard[idx]
                    self.gameboard[opposite_idx] = 0
                    self.gameboard[idx] = 0

        # check for extra turn: if last stone landed in own store
        if idx == own_store:
            self.switch_turns()

    def resolve_outcome(self):
        # game over when all pits on one side are empty
        player1_side_empty = all(self.gameboard[i] == 0 for i in range(0, self.pits))
        player2_side_empty = all(self.gameboard[i] == 0 for i in range(self.pits + 1, self.pits + 1 + self.pits))

        if not (player1_side_empty or player2_side_empty):
            self.outcome = None
            return

        # collect remaining stones into respective stores
        for i in range(0, self.pits):
            self.gameboard[self.player1_store] += self.gameboard[i]
            self.gameboard[i] = 0
        for i in range(self.pits + 1, self.pits + 1 + self.pits):
            self.gameboard[self.player2_store] += self.gameboard[i]
            self.gameboard[i] = 0

        if self.gameboard[self.player1_store] > self.gameboard[self.player2_store]:
            self.outcome = Outcome.Player1Win
        elif self.gameboard[self.player2_store] > self.gameboard[self.player1_store]:
            self.outcome = Outcome.Player2Win
        else:
            self.outcome = Outcome.Tie

correction_message = "Invalid command format. Please optionally add -p [pits_per_side] and -s [stones_per_pit]."

def parse_settings(args):
    # defaults: 6 pits per side, 4 stones per pit
    ps = [6, 4]

    parsed_settings = {}

    for ps_index, flag in enumerate(["-p", "-s"]):
        if flag in args:
            index = args.index(flag)
            if index + 1 < len(args):
                try:
                    ps[ps_index] = int(args[index + 1])
                    args.pop(index)
                    args.pop(index)
                except ValueError:
                    return (False, {}, correction_message + f" Invalid integer value for {flag}.")
            else:
                return (False, {}, correction_message + f" Missing value for {flag}.")

    if len(args) > 0:
        return (False, {}, correction_message + " Unrecognized extra arguments: " + " ".join(args))

    pits, stones = ps
    if pits <= 0 or pits > 12 or stones <= 0 or stones > 20:
        return (False, {}, "Pits per side must be between 1 and 12 and stones per pit between 1 and 20.")

    parsed_settings["pits"] = pits
    parsed_settings["stones"] = stones

    return (True, parsed_settings, "")

def get_settings_string(settings):
    return f"Pits per side: {settings['pits']}, Stones per pit: {settings['stones']}"
