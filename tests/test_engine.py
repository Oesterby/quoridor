import unittest
from src.occams_council.engine.state import GameState, Position, Wall, BOARD_SIZE
from src.occams_council.engine import rules

class TestEngine(unittest.TestCase):
    def test_initial_state_2p(self):
        state = GameState.new_game(2)
        self.assertEqual(len(state.pawns), 2)
        self.assertEqual(state.pawns[0].row, 0)
        self.assertEqual(state.pawns[1].row, BOARD_SIZE - 1)
        self.assertEqual(state.current_player, 0)
        self.assertIsNone(state.winner)

    def test_initial_state_4p(self):
        state = GameState.new_game(4)
        self.assertEqual(len(state.pawns), 4)
        # P0: Top -> Bottom
        self.assertEqual(state.pawns[0].row, 0)
        # P1: Right -> Left
        self.assertEqual(state.pawns[1].col, BOARD_SIZE - 1)
        # P2: Bottom -> Top
        self.assertEqual(state.pawns[2].row, BOARD_SIZE - 1)
        # P3: Left -> Right
        self.assertEqual(state.pawns[3].col, 0)

    def test_pawn_moves_basic(self):
        state = GameState.new_game(2)
        moves = rules.generate_pawn_moves(state)
        # P0 at (0, 4). Can move (0, 3), (0, 5), (1, 4)
        # (0,3) is left, (0,5) is right, (1,4) is down. Up is out of bounds.
        self.assertEqual(len(moves), 3)
        destinations = {(m.to.row, m.to.col) for m in moves}
        self.assertIn((0, 3), destinations)
        self.assertIn((0, 5), destinations)
        self.assertIn((1, 4), destinations)

    def test_wall_placement_validity(self):
        state = GameState.new_game(2)
        # Place a wall
        wall = Wall(0, 0, True)
        moves = rules.generate_wall_moves(state)
        # Should be able to place it
        can_place = any(m.wall == wall for m in moves)
        self.assertTrue(can_place)

    def test_jump_over_opponent(self):
        state = GameState.new_game(2)
        # Move P0 and P1 to be adjacent
        state.pawns[0] = Position(4, 4)
        state.pawns[1] = Position(5, 4)
        state.current_player = 0
        
        moves = rules.generate_pawn_moves(state)
        # P0 can jump to (6, 4)
        destinations = {(m.to.row, m.to.col) for m in moves}
        self.assertIn((6, 4), destinations)

    def test_win_condition_2p(self):
        state = GameState.new_game(2)
        state.pawns[0] = Position(BOARD_SIZE - 1, 4) # P0 at goal
        state.check_winner()
        self.assertEqual(state.winner, 0)

    def test_win_condition_4p(self):
        state = GameState.new_game(4)
        state.pawns[1] = Position(4, 0) # P1 (Right->Left) at col 0
        state.check_winner()
        self.assertEqual(state.winner, 1)

if __name__ == '__main__':
    unittest.main()
