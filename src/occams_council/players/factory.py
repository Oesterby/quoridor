from __future__ import annotations
from typing import Dict, Type, Optional, Any
from .agents.base import Agent
from .agents.human_agent import HumanAgent
from .agents.random_agent import RandomAgent
from .agents.llm_agent import LLMAgent

class AgentFactory:
    _registry: Dict[str, Type[Agent]] = {}

    @classmethod
    def register(cls, name: str, agent_cls: Type[Agent]) -> None:
        cls._registry[name] = agent_cls

    @classmethod
    def create(cls, config_str: str) -> Agent:
        """
        Create an agent from a configuration string.
        Format: "type:arg1,arg2" or just "type"
        Examples:
            - "human"
            - "random"
            - "llm:gpt-4o"
            - "llm:gpt-3.5-turbo,5" (model, max_attempts)
        """
        parts = config_str.split(":", 1)
        agent_type = parts[0].lower()
        args_str = parts[1] if len(parts) > 1 else ""
        
        if agent_type not in cls._registry:
            raise ValueError(f"Unknown agent type: {agent_type}. Available: {list(cls._registry.keys())}")
            
        agent_cls = cls._registry[agent_type]
        
        # Parse args
        args = [a.strip() for a in args_str.split(",")] if args_str else []
        
        # Instantiate
        # We might need specific logic for different agents if their init signatures vary widely.
        # For now, let's try to map args to init.
        try:
            if agent_type == "llm":
                model = args[0] if len(args) > 0 else None
                max_attempts = int(args[1]) if len(args) > 1 else 3
                return agent_cls(model=model, max_attempts=max_attempts)
            elif agent_type == "human":
                name = args[0] if len(args) > 0 else "Human"
                return agent_cls(name=name)
            elif agent_type == "random":
                return agent_cls()
            else:
                return agent_cls(*args)
        except Exception as e:
            raise ValueError(f"Failed to create agent '{agent_type}' with args {args}: {e}")

# Register default agents
AgentFactory.register("human", HumanAgent)
AgentFactory.register("random", RandomAgent)
AgentFactory.register("llm", LLMAgent)
