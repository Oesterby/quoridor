import unittest
from src.occams_council.players.factory import AgentFactory
from src.occams_council.players.agents.human_agent import HumanAgent
from src.occams_council.players.agents.random_agent import RandomAgent
from src.occams_council.players.agents.llm_agent import LLMAgent

class TestFactory(unittest.TestCase):
    def test_create_human(self):
        agent = AgentFactory.create("human")
        self.assertIsInstance(agent, HumanAgent)
        self.assertEqual(agent.name, "Human")

    def test_create_human_with_name(self):
        agent = AgentFactory.create("human:Alice")
        self.assertIsInstance(agent, HumanAgent)
        self.assertEqual(agent.name, "Alice")

    def test_create_random(self):
        agent = AgentFactory.create("random")
        self.assertIsInstance(agent, RandomAgent)

    def test_create_llm(self):
        agent = AgentFactory.create("llm")
        self.assertIsInstance(agent, LLMAgent)
        self.assertEqual(agent.model, "gpt-4o-mini") # default

    def test_create_llm_with_args(self):
        agent = AgentFactory.create("llm:gpt-4,5")
        self.assertIsInstance(agent, LLMAgent)
        self.assertEqual(agent.model, "gpt-4")
        self.assertEqual(agent.max_attempts, 5)

if __name__ == '__main__':
    unittest.main()
