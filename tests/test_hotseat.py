import unittest
import json
from src.occams_council.engine.state import GameState
from src.occams_council.players.hotseat import HotseatController

class TestHotseat(unittest.TestCase):
    def test_4_player_setup(self):
        state = GameState.new_game(4)
        controller = HotseatController(state)
        
        # Setup 4 player identities
        metas = [
            {"id": 0, "name": "P1", "role": "human"},
            {"id": 1, "name": "P2", "role": "bot"},
            {"id": 2, "name": "P3", "role": "bot"},
            {"id": 3, "name": "P4", "role": "bot"},
        ]
        controller.set_player_identities(metas)
        
        # This should not raise IndexError
        controller.refresh_moves()
        
        # Check if snapshot was generated (we can mock print or just check internal state if possible, 
        # but refresh_moves calls _emit_json_snapshot which prints. 
        # We mainly care that it didn't crash.)
        self.assertEqual(len(controller._players_meta), 4)

    def test_2_player_setup(self):
        state = GameState.new_game(2)
        controller = HotseatController(state)
        metas = [
            {"id": 0, "name": "Alice", "role": "human"},
            {"id": 1, "name": "Bob", "role": "human"},
        ]
        controller.set_player_identities(metas)
        controller.refresh_moves()
        self.assertEqual(len(controller._players_meta), 2)

if __name__ == '__main__':
    unittest.main()
