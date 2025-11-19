import unittest
from src.occams_council.players.agents.llm_agent import LLMAgent

class TestLLMAgent(unittest.TestCase):
    def test_parse_response_with_rationale(self):
        agent = LLMAgent(model="gpt-5.1")
        
        # Case 1: Clean JSON
        raw1 = '{"rationale": "Blocking path", "move_id": "M12"}'
        mid1, rat1 = agent._parse_response(raw1)
        self.assertEqual(mid1, "M12")
        self.assertEqual(rat1, "Blocking path")
        
        # Case 2: Markdown wrapped
        raw2 = '```json\n{\n  "rationale": "Moving forward",\n  "move_id": "M5"\n}\n```'
        mid2, rat2 = agent._parse_response(raw2)
        self.assertEqual(mid2, "M5")
        self.assertEqual(rat2, "Moving forward")
        
        # Case 3: Invalid JSON
        raw3 = "I think M3 is good"
        mid3, rat3 = agent._parse_response(raw3)
        self.assertIsNone(mid3)
        self.assertIsNone(rat3)

    def test_algebraic_notation(self):
        agent = LLMAgent()
        # (0,0) -> a9
        self.assertEqual(agent._to_algebraic(0, 0), "a9")
        # (8,8) -> i1
        self.assertEqual(agent._to_algebraic(8, 8), "i1")
        # (4,4) -> e5
        self.assertEqual(agent._to_algebraic(4, 4), "e5")

    def test_dense_ascii_board(self):
        from src.occams_council.engine.state import GameState, Position, Wall
        agent = LLMAgent()
        state = GameState.new_game(2)
        # Move P1 to (1, 4) -> e8
        state.pawns[0] = Position(1, 4)
        # Add a horizontal wall at (0,0) -> a9h
        state.walls.add((0, 0, True))
        # Add a vertical wall at (2,2) -> c7v
        state.walls.add((2, 2, False))
        
        board_str = agent._generate_dense_ascii_board(state)
        
        # Check for P1 at e8
        # e is col index 4. 8 is row index 1.
        # Grid coords: row 1*2=2. col 4*2=8.
        # Line 2 should contain "1" at index ~8 (accounting for spacing/borders)
        # The string format is "row_label  row_content  row_label"
        # "8  . . . . 1 . . . .  8"
        self.assertIn("1", board_str)
        
        # Check for Horizontal Wall at (0,0)
        # Row 0, Col 0. Horizontal.
        # Grid row: 0*2+1 = 1.
        # Grid cols: 0, 1, 2.
        # Line 1 should have "---" at the start (after margin)
        # "   ---"
        self.assertIn("---", board_str)
        
        # Check for Vertical Wall at (2,2)
        # Row 2, Col 2. Vertical.
        # Grid col: 2*2+1 = 5.
        # Grid rows: 2*2=4, 2*2+1=5, 2*2+2=6.
        # Lines corresponding to grid rows 4,5,6 should have "|" at col 5.
        self.assertIn("|", board_str)

    def test_goals_and_rules(self):
        agent = LLMAgent()
        
        # 2 Players
        goals_2p = agent._get_goals_description(2)
        self.assertIn("P1: Reach Row 1", goals_2p)
        self.assertIn("P2: Reach Row 9", goals_2p)
        
        rules_2p = agent._get_rules_summary(2)
        self.assertNotIn("No double jumps", rules_2p)
        self.assertIn("Be the FIRST", rules_2p)
        
        # 4 Players
        goals_4p = agent._get_goals_description(4)
        self.assertIn("P1: Reach Row 1", goals_4p)
        self.assertIn("P2: Reach Col a", goals_4p)
        self.assertIn("P3: Reach Row 9", goals_4p)
        self.assertIn("P4: Reach Col i", goals_4p)
        
        rules_4p = agent._get_rules_summary(4)
        self.assertIn("No double jumps", rules_4p)
        self.assertIn("Be the FIRST", rules_4p)

if __name__ == '__main__':
    unittest.main()
