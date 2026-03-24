"""Tests for the pie/swap rule in Hex and Snort games."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from game import Game
from games.snort import SnortGame
from games.hex import HexGame
from games.connect4 import Connect4Game


class MockUser:
    def __init__(self, name):
        self.name = name
        self.mention = f"@{name}"


@pytest.fixture
def players():
    return MockUser("Alice"), MockUser("Bob")


@pytest.fixture
def snort_game(players):
    p1, p2 = players
    return SnortGame(p1, p2, {"width": 5, "height": 5})


@pytest.fixture
def hex_game(players):
    p1, p2 = players
    return HexGame(p1, p2, {"width": 5, "height": 5})


# ---------------------------------------------------------------------------
# game.py base-class infrastructure
# ---------------------------------------------------------------------------

class TestGameSwapInfrastructure:
    def test_swap_disabled_by_default(self, players):
        """Base Game has swap_enabled=False and move_count=0 by default."""
        p1, p2 = players

        class MinimalGame(Game):
            def __init__(self, p1, p2, s):
                super().__init__(p1, p2, s)
                self.game_type = "test"

        g = MinimalGame(p1, p2, {})
        assert g.swap_enabled is False
        assert g.move_count == 0

    def test_can_swap_requires_correct_conditions(self, players):
        p1, p2 = players

        class MinimalGame(Game):
            def __init__(self, p1, p2, s):
                super().__init__(p1, p2, s)
                self.game_type = "test"
                self.swap_enabled = True

        g = MinimalGame(p1, p2, {})
        # turn=1, move_count=0  -> False
        assert g.can_swap() is False

        g.move_count = 1
        # turn=1, move_count=1  -> False (not player 2's turn)
        assert g.can_swap() is False

        g.turn = 2
        # turn=2, move_count=1  -> True
        assert g.can_swap() is True

        g.move_count = 2
        # turn=2, move_count=2  -> False (past first move)
        assert g.can_swap() is False

    def test_do_swap_exchanges_pieces(self, players):
        p1, p2 = players

        class MinimalGame(Game):
            def __init__(self, p1, p2, s):
                super().__init__(p1, p2, s)
                self.game_type = "test"

        g = MinimalGame(p1, p2, {})
        orig_p1 = g.player1_piece
        orig_p2 = g.player2_piece
        g.do_swap()
        assert g.player1_piece == orig_p2
        assert g.player2_piece == orig_p1


# ---------------------------------------------------------------------------
# Snort
# ---------------------------------------------------------------------------

class TestSnortSwap:
    def test_swap_enabled(self, snort_game):
        assert snort_game.swap_enabled is True

    def test_no_swap_before_first_move(self, snort_game):
        """Player 1 cannot swap (turn=1, move_count=0)."""
        assert snort_game.can_swap() is False
        assert snort_game.is_formatted_move("swap") is False
        assert snort_game.is_legal_move("swap") is False

    def test_swap_available_for_player2_first_move(self, snort_game):
        snort_game.make_move("a1")
        snort_game.turn = 2
        assert snort_game.can_swap() is True
        assert snort_game.is_formatted_move("swap") is True
        assert snort_game.is_legal_move("swap") is True

    def test_swap_case_insensitive(self, snort_game):
        snort_game.make_move("a1")
        snort_game.turn = 2
        assert snort_game.is_formatted_move("SWAP") is True
        assert snort_game.is_legal_move("  Swap  ") is True

    def test_swap_exchanges_pieces(self, snort_game):
        snort_game.make_move("a1")
        snort_game.turn = 2
        p1_piece_before = snort_game.player1_piece
        p2_piece_before = snort_game.player2_piece
        snort_game.make_move("swap")
        assert snort_game.player1_piece == p2_piece_before
        assert snort_game.player2_piece == p1_piece_before

    def test_swap_does_not_increment_move_count(self, snort_game):
        snort_game.make_move("a1")
        assert snort_game.move_count == 1
        snort_game.turn = 2
        snort_game.make_move("swap")
        assert snort_game.move_count == 1

    def test_no_swap_after_normal_second_move(self, snort_game):
        """Swap not available once player 2 has made a normal move."""
        snort_game.make_move("a1")
        snort_game.turn = 2
        snort_game.make_move("c3")
        assert snort_game.can_swap() is False

    def test_no_swap_after_post_swap_move(self, snort_game):
        """After swap + subsequent move, swap is no longer available."""
        snort_game.make_move("a1")
        snort_game.turn = 2
        snort_game.make_move("swap")
        snort_game.turn = 1
        snort_game.make_move("b1")
        snort_game.turn = 2
        assert snort_game.can_swap() is False

    def test_normal_move_still_works_for_player2(self, snort_game):
        """Player 2 can still make a normal move instead of swapping."""
        snort_game.make_move("a1")
        snort_game.turn = 2
        assert snort_game.is_legal_move("c3") is True
        snort_game.make_move("c3")
        assert snort_game.move_count == 2


# ---------------------------------------------------------------------------
# Hex
# ---------------------------------------------------------------------------

class TestHexSwap:
    def test_swap_enabled(self, hex_game):
        assert hex_game.swap_enabled is True

    def test_no_swap_before_first_move(self, hex_game):
        assert hex_game.can_swap() is False
        assert hex_game.is_formatted_move("swap") is False
        assert hex_game.is_legal_move("swap") is False

    def test_swap_available_for_player2_first_move(self, hex_game):
        hex_game.make_move("a1")
        hex_game.turn = 2
        assert hex_game.can_swap() is True
        assert hex_game.is_formatted_move("swap") is True
        assert hex_game.is_legal_move("swap") is True

    def test_swap_exchanges_pieces(self, hex_game):
        hex_game.make_move("a1")
        hex_game.turn = 2
        p1_before = hex_game.player1_piece
        p2_before = hex_game.player2_piece
        hex_game.make_move("swap")
        assert hex_game.player1_piece == p2_before
        assert hex_game.player2_piece == p1_before

    def test_swap_does_not_increment_move_count(self, hex_game):
        hex_game.make_move("a1")
        assert hex_game.move_count == 1
        hex_game.turn = 2
        hex_game.make_move("swap")
        assert hex_game.move_count == 1

    def test_no_swap_after_normal_second_move(self, hex_game):
        hex_game.make_move("a1")
        hex_game.turn = 2
        hex_game.make_move("b2")
        assert hex_game.can_swap() is False

    def test_normal_move_increments_move_count(self, hex_game):
        hex_game.make_move("a1")
        assert hex_game.move_count == 1
        hex_game.turn = 2
        hex_game.make_move("b2")
        assert hex_game.move_count == 2


# ---------------------------------------------------------------------------
# Other games should NOT have swap
# ---------------------------------------------------------------------------

class TestConnect4NoSwap:
    def test_swap_disabled(self, players):
        p1, p2 = players
        g = Connect4Game(p1, p2, {"width": 7, "height": 6})
        assert g.swap_enabled is False
        assert g.can_swap() is False
