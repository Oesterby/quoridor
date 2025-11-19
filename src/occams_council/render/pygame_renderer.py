from __future__ import annotations
import pygame
import sys
import argparse
import os
from typing import Tuple, List

# Try to load .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # Fallback: manual .env parsing
    try:
        with open(".env", "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ[key.strip()] = value.strip()
    except FileNotFoundError:
        pass
from ..engine.state import GameState, Position, Wall, BOARD_SIZE
from ..engine import rules
from ..players.hotseat import HotseatController
from ..players.agents.base import GameView, Agent
from ..players.factory import AgentFactory

CELL_SIZE = 60
PADDING = 40
BG_COLOR = (30, 30, 35)
GRID_COLOR = (180, 180, 180)
PLAYER_COLORS = [
    (50, 160, 255),   # P1: Blue
    (255, 140, 60),   # P2: Orange
    (60, 220, 100),   # P3: Green
    (220, 60, 220),   # P4: Purple
]
HIGHLIGHT_COLOR = (200, 220, 60)
TEXT_COLOR = (240, 240, 240)

class PygameHotseatUI:
    def __init__(self, player_specs: List[str] | None = None):
        pygame.init()
        self.font = pygame.font.SysFont("consolas", 20)
        w = h = PADDING * 2 + CELL_SIZE * BOARD_SIZE
        self.screen = pygame.display.set_mode((w, h))
        pygame.display.set_caption("Quoridor Hotseat")
        self.clock = pygame.time.Clock()
        
        # Default to 2 human players if not specified
        if not player_specs:
            player_specs = ["human", "human"]
            
        self.restart_game(player_specs)
        self.running = True
        self.wall_orientation_horizontal = True  # toggle with space

    def restart_game(self, player_specs: List[str]):
        num = len(player_specs)
        if num not in (2, 4):
            print(f"Warning: {num} players not supported. Defaulting to 2.")
            player_specs = player_specs[:2] if num > 2 else ["human", "human"]
            num = 2
            
        self.state = GameState.new_game(num_players=num)
        self.controller = HotseatController(self.state)
        self.controller.refresh_moves()
        
        self.agents: List[Agent] = []
        for i, spec in enumerate(player_specs):
            try:
                agent = AgentFactory.create(spec)
                # If human, ensure name is set
                if hasattr(agent, "name") and agent.name == "Human":
                    agent.name = f"Player {i+1}"
                self.agents.append(agent)
            except Exception as e:
                print(f"Error creating agent for '{spec}': {e}. Fallback to Random.")
                self.agents.append(AgentFactory.create("random"))

        self._sync_player_identities()

    def board_to_pixel(self, pos: Position) -> Tuple[int, int]:
        return PADDING + pos.col * CELL_SIZE, PADDING + pos.row * CELL_SIZE

    def draw_grid(self):
        for r in range(BOARD_SIZE + 1):
            y = PADDING + r * CELL_SIZE
            pygame.draw.line(
                self.screen,
                GRID_COLOR,
                (PADDING, y),
                (PADDING + BOARD_SIZE * CELL_SIZE, y),
                2,
            )
        for c in range(BOARD_SIZE + 1):
            x = PADDING + c * CELL_SIZE
            pygame.draw.line(
                self.screen,
                GRID_COLOR,
                (x, PADDING),
                (x, PADDING + BOARD_SIZE * CELL_SIZE),
                2,
            )

    def draw_pawns(self):
        for idx, pawn in enumerate(self.state.pawns):
            x, y = self.board_to_pixel(pawn)
            rect = pygame.Rect(x + 8, y + 8, CELL_SIZE - 16, CELL_SIZE - 16)
            color = PLAYER_COLORS[idx % len(PLAYER_COLORS)]
            pygame.draw.rect(self.screen, color, rect, border_radius=8)
            
            # Mark current player
            if idx == self.state.current_player:
                pygame.draw.rect(self.screen, (255, 255, 255), rect, 2, border_radius=8)

    def draw_walls(self):
        for r, c, horizontal in self.state.walls:
            base_x = PADDING + c * CELL_SIZE
            base_y = PADDING + r * CELL_SIZE
            if horizontal:
                rect = pygame.Rect(base_x, base_y + CELL_SIZE - 6, CELL_SIZE * 2, 12)
            else:
                rect = pygame.Rect(base_x + CELL_SIZE - 6, base_y, 12, CELL_SIZE * 2)
            pygame.draw.rect(self.screen, (120, 60, 60), rect, border_radius=3)

    def draw_wall_ghost(self):
        if self.state.winner is not None:
            return
        
        # Only draw ghost for human players
        if not self.active_agent().is_human:
            return
            
        keys = pygame.key.get_pressed()
        if not (keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]):
            return
        if self.state.shared_walls_remaining <= 0:
            return
        mx, my = pygame.mouse.get_pos()
        if mx < PADDING or my < PADDING:
            return
        col = (mx - PADDING) // CELL_SIZE
        row = (my - PADDING) // CELL_SIZE
        if not (0 <= row < BOARD_SIZE - 1 and 0 <= col < BOARD_SIZE - 1):
            return
        candidate = Wall(row, col, self.wall_orientation_horizontal)
        
        # Check legality
        is_legal = any(
            m.kind == "wall" and m.wall == candidate
            for m in self.controller.legal_moves
        )
        
        color = (200, 120, 120, 120) if is_legal else (255, 50, 50, 120)
        
        base_x = PADDING + col * CELL_SIZE
        base_y = PADDING + row * CELL_SIZE
        if candidate.horizontal:
            rect = pygame.Rect(base_x, base_y + CELL_SIZE - 6, CELL_SIZE * 2, 12)
        else:
            rect = pygame.Rect(base_x + CELL_SIZE - 6, base_y, 12, CELL_SIZE * 2)
        ghost_surface = pygame.Surface(rect.size, pygame.SRCALPHA)
        ghost_surface.fill(color)
        self.screen.blit(ghost_surface, rect.topleft)

    def draw_highlights(self):
        # Only highlight for human players
        if not self.active_agent().is_human:
            return
            
        for move in self.controller.legal_moves:
            if move.kind == "pawn" and move.to:
                x, y = self.board_to_pixel(move.to)
                pygame.draw.rect(
                    self.screen,
                    HIGHLIGHT_COLOR,
                    pygame.Rect(x + 20, y + 20, CELL_SIZE - 40, CELL_SIZE - 40),
                    2,
                )

    def draw_status(self):
        status = f"Player {self.state.current_player + 1} ({self.active_agent().name}) | Walls: {self.state.shared_walls_remaining} | {'H' if self.wall_orientation_horizontal else 'V'}"
        if self.state.winner is not None:
            status = f"Winner: Player {self.state.winner + 1} - Press ESC to quit"
        surf = self.font.render(status, True, TEXT_COLOR)
        self.screen.blit(surf, (PADDING, 8))

    def active_agent(self) -> Agent:
        return self.agents[self.state.current_player]

    def _sync_player_identities(self):
        metas = []
        for idx, ag in enumerate(self.agents):
            metas.append(
                {
                    "id": idx,
                    "name": getattr(ag, "name", f"Player {idx + 1}"),
                    "role": "human" if getattr(ag, "is_human", False) else "bot",
                }
            )
        self.controller.set_player_identities(metas)

    def handle_click(self, pos):
        if self.state.winner is not None:
            return
            
        agent = self.active_agent()
        if not agent.is_human:
            return

        mx, my = pos
        if mx < PADDING or my < PADDING:
            return
        col = (mx - PADDING) // CELL_SIZE
        row = (my - PADDING) // CELL_SIZE
        if not (0 <= row < BOARD_SIZE and 0 <= col < BOARD_SIZE):
            return
            
        keys = pygame.key.get_pressed()
        shift_down = keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]
        
        if shift_down:
            if self.state.shared_walls_remaining <= 0:
                return
            if not (0 <= row < BOARD_SIZE - 1 and 0 <= col < BOARD_SIZE - 1):
                return
            wall = Wall(row, col, self.wall_orientation_horizontal)
            for m in self.controller.legal_moves:
                if m.kind == "wall" and m.wall == wall:
                    if hasattr(agent, "set_pending"):
                        agent.set_pending(m)  # type: ignore
                        self.apply_agent_move(agent)
                    return
            return
            
        # Pawn move
        target = Position(row, col)
        for m in self.controller.legal_moves:
            if m.kind == "pawn" and m.to == target:
                if hasattr(agent, "set_pending"):
                    agent.set_pending(m)  # type: ignore
                    self.apply_agent_move(agent)
                return

    def toggle_orientation(self):
        self.wall_orientation_horizontal = not self.wall_orientation_horizontal

    def apply_agent_move(self, agent: Agent):
        if self.state.winner is not None:
            return
        view = GameView(self.state)
        move = agent.choose_move(view)
        
        # Validate
        # (Simplified validation: just check if move is in legal moves list)
        # Note: strict validation is good but for now we trust the agent/controller sync
        # Actually, we should validate because LLM might hallucinate
        
        legal_moves = list(view.legal_moves())
        if move not in legal_moves:
            print(f"Illegal move attempted by {agent.name}: {move}")
            # For human, this shouldn't happen via UI. For LLM, it might.
            # If LLM fails, we should probably have a fallback or retry, but LLMAgent handles that.
            return

        self.state = rules.apply_move(self.state, move)
        self.controller.state = self.state
        self.controller.refresh_moves()

    def maybe_ai_turn(self):
        if self.state.winner is not None:
            return
        agent = self.active_agent()
        if not agent.is_human:
            # Small delay for UX?
            # pygame.time.wait(100) # blocks UI, bad.
            # Better: check timer. But for now, just run it.
            self.apply_agent_move(agent)

    def loop(self):
        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.running = False
                    elif event.key == pygame.K_SPACE:
                        self.toggle_orientation()
                    # Hotkeys for quick restarts (2p)
                    elif event.key == pygame.K_1:
                        self.restart_game(["human", "human"])
                    elif event.key == pygame.K_2:
                        self.restart_game(["human", "random"])
                    elif event.key == pygame.K_3:
                        self.restart_game(["random", "human"])
                    elif event.key == pygame.K_4:
                        self.restart_game(["random", "random"])
                    elif event.key == pygame.K_5:
                        self.restart_game(["human", "llm"])
                    # 4 player demo
                    elif event.key == pygame.K_0:
                        self.restart_game(["human", "random", "random", "random"])
                        
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    self.handle_click(event.pos)
                    
                    
            self.screen.fill(BG_COLOR)
            self.draw_grid()
            self.draw_highlights()
            self.draw_pawns()
            self.draw_walls()
            self.draw_wall_ghost()
            self.draw_status()
            self.draw_status()
            pygame.display.flip()
            self.maybe_ai_turn()
            self.clock.tick(30)
        pygame.quit()


def main():
    parser = argparse.ArgumentParser(description="Quoridor Hotseat")
    parser.add_argument("players", nargs="*", help="Player specs (e.g. human random llm:gpt-4)")
    args = parser.parse_args()
    
    players = args.players if args.players else ["human", "human"]
    
    ui = PygameHotseatUI(players)
    ui.loop()


if __name__ == "__main__":
    main()
