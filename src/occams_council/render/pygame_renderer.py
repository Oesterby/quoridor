from __future__ import annotations
import pygame
from typing import Tuple
from ..engine.state import GameState, Position, Wall, BOARD_SIZE
from ..engine import rules
from ..players.hotseat import HotseatController
from ..players.agents.base import GameView, Agent
from ..players.agents.human_agent import HumanAgent
from ..players.agents.random_agent import RandomAgent
from ..players.agents.llm_agent import LLMAgent

CELL_SIZE = 60
PADDING = 40
BG_COLOR = (30, 30, 35)
GRID_COLOR = (180, 180, 180)
P1_COLOR = (50, 160, 255)
P2_COLOR = (255, 140, 60)
HIGHLIGHT_COLOR = (200, 220, 60)
TEXT_COLOR = (240, 240, 240)

FONT = None  # deprecated: using instance font


class PygameHotseatUI:
    def __init__(self):
        pygame.init()
        self.font = pygame.font.SysFont("consolas", 20)
        w = h = PADDING * 2 + CELL_SIZE * BOARD_SIZE
        self.screen = pygame.display.set_mode((w, h))
        pygame.display.set_caption("Quoridor Hotseat")
        self.clock = pygame.time.Clock()
        self.state = GameState()
        self.controller = HotseatController(self.state)
        self.controller.refresh_moves()
        # Agents (default Human vs LLM Bot). Change with number keys.
        self.agents: list[Agent] = [HumanAgent(), LLMAgent()]
        self._sync_player_identities()
        self.running = True
        self.wall_orientation_horizontal = True  # toggle with space

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
            color = P1_COLOR if idx == 0 else P2_COLOR
            pygame.draw.rect(self.screen, color, rect, border_radius=8)

    def draw_walls(self):
        for r, c, horizontal in self.state.walls:
            base_x = PADDING + c * CELL_SIZE
            base_y = PADDING + r * CELL_SIZE
            if horizontal:
                # horizontal wall spans two cells horizontally and thickness ~10
                rect = pygame.Rect(base_x, base_y + CELL_SIZE - 6, CELL_SIZE * 2, 12)
            else:
                rect = pygame.Rect(base_x + CELL_SIZE - 6, base_y, 12, CELL_SIZE * 2)
            pygame.draw.rect(self.screen, (120, 60, 60), rect, border_radius=3)

    def draw_wall_ghost(self):
        # Show ghost only if shift held, game running, walls available
        if self.state.winner is not None:
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
        # Anchor must be within valid wall placement grid (0..BOARD_SIZE-2)
        if not (0 <= row < BOARD_SIZE - 1 and 0 <= col < BOARD_SIZE - 1):
            return
        candidate = Wall(row, col, self.wall_orientation_horizontal)
        # Verify legality by checking cached legal wall moves
        is_legal = any(
            m.kind == "wall" and m.wall == candidate
            for m in self.controller.legal_moves
        )
        if not is_legal:
            return
        base_x = PADDING + col * CELL_SIZE
        base_y = PADDING + row * CELL_SIZE
        if candidate.horizontal:
            rect = pygame.Rect(base_x, base_y + CELL_SIZE - 6, CELL_SIZE * 2, 12)
        else:
            rect = pygame.Rect(base_x + CELL_SIZE - 6, base_y, 12, CELL_SIZE * 2)
        ghost_surface = pygame.Surface(rect.size, pygame.SRCALPHA)
        ghost_surface.fill((200, 120, 120, 120))  # semi-transparent RGBA
        self.screen.blit(ghost_surface, rect.topleft)

    def draw_highlights(self):
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
        status = f"Player {self.state.current_player + 1} turn | Shared Walls Left: {self.state.shared_walls_remaining} | Orientation: {'H' if self.wall_orientation_horizontal else 'V'}"
        if self.state.winner is not None:
            status = f"Winner: Player {self.state.winner + 1} - Press ESC to quit"
        surf = self.font.render(status, True, TEXT_COLOR)
        self.screen.blit(surf, (PADDING, 8))

    def active_agent(self) -> Agent:
        return self.agents[self.state.current_player]

    def set_players(self, spec: str):
        mapping = {"human": HumanAgent, "random": RandomAgent, "llm": LLMAgent}
        parts = [p.strip().lower() for p in spec.split(",") if p.strip()]
        if len(parts) == 2:
            new_agents: list[Agent] = []
            for p in parts:
                cls = mapping.get(p)
                if cls:
                    new_agents.append(cls())
            if len(new_agents) == 2:
                self.agents = new_agents
                self._sync_player_identities()

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
        mx, my = pos
        if mx < PADDING or my < PADDING:
            return
        col = (mx - PADDING) // CELL_SIZE
        row = (my - PADDING) // CELL_SIZE
        if not (0 <= row < BOARD_SIZE and 0 <= col < BOARD_SIZE):
            return
        keys = pygame.key.get_pressed()
        shift_down = keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]
        # If shift held: only attempt wall placement, suppress pawn movement
        if shift_down:
            if self.state.shared_walls_remaining <= 0:
                return
            # Wall anchors are within 0..BOARD_SIZE-2
            if not (0 <= row < BOARD_SIZE - 1 and 0 <= col < BOARD_SIZE - 1):
                return
            wall = Wall(row, col, self.wall_orientation_horizontal)
            for m in self.controller.legal_moves:
                if m.kind == "wall" and m.wall == wall:
                    agent = self.active_agent()
                    if agent.is_human and hasattr(agent, "set_pending"):
                        agent.set_pending(m)  # type: ignore
                        self.apply_agent_move(agent)
                    return
            return  # shift held but no legal wall here; do nothing
        # Normal click (no shift): try pawn move only
        target = Position(row, col)
        for m in self.controller.legal_moves:
            if m.kind == "pawn" and m.to == target:
                agent = self.active_agent()
                if agent.is_human and hasattr(agent, "set_pending"):
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
        # Validate move among legal moves
        legal_keys = {
            (
                m.kind,
                getattr(m.to, "row", None),
                getattr(m.to, "col", None),
                getattr(m.wall, "row", None),
                getattr(m.wall, "col", None),
                getattr(m.wall, "horizontal", None),
            )
            for m in view.legal_moves()
        }
        key = (
            move.kind,
            getattr(move.to, "row", None),
            getattr(move.to, "col", None),
            getattr(move.wall, "row", None),
            getattr(move.wall, "col", None),
            getattr(move.wall, "horizontal", None),
        )
        if key in legal_keys:
            self.state = rules.apply_move(self.state, move)
            self.controller.state = self.state
            self.controller.refresh_moves()

    def maybe_ai_turn(self):
        if self.state.winner is not None:
            return
        agent = self.active_agent()
        if not agent.is_human:
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
                    elif event.key == pygame.K_1:
                        self.set_players("human,human")
                    elif event.key == pygame.K_2:
                        self.set_players("human,random")
                    elif event.key == pygame.K_3:
                        self.set_players("random,human")
                    elif event.key == pygame.K_4:
                        self.set_players("random,random")
                    elif event.key == pygame.K_5:
                        self.set_players("human,llm")
                    elif event.key == pygame.K_6:
                        self.set_players("llm,human")
                    elif event.key == pygame.K_7:
                        self.set_players("random,llm")
                    elif event.key == pygame.K_8:
                        self.set_players("llm,random")
                    elif event.key == pygame.K_9:
                        self.set_players("llm,llm")
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    self.handle_click(event.pos)
            self.maybe_ai_turn()
            self.screen.fill(BG_COLOR)
            self.draw_grid()
            self.draw_highlights()
            self.draw_pawns()
            self.draw_walls()
            self.draw_wall_ghost()
            self.draw_status()
            pygame.display.flip()
            self.clock.tick(30)
        pygame.quit()


def main():
    ui = PygameHotseatUI()
    ui.loop()


if __name__ == "__main__":
    main()
