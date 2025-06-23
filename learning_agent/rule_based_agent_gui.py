import pygame
import random
from enum import Enum
from dataclasses import dataclass
from typing import Set, Tuple

# --- Logic Classes ---
class Action(Enum):
    MOVE_UP = "up"
    MOVE_DOWN = "down"
    MOVE_LEFT = "left"
    MOVE_RIGHT = "right"
    STAY = "stay"

@dataclass
class Position:
    x: int
    y: int
    
    def __add__(self, other):
        return Position(self.x + other.x, self.y + other.y)
    
    def __eq__(self, other):
        return self.x == other.x and self.y == other.y
    
    def __hash__(self):
        return hash((self.x, self.y))

class Environment:
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.agent_pos = Position(width // 2, height // 2)
        self.goal_pos = self._generate_random_position(exclude=[self.agent_pos])
        self.obstacles: Set[Tuple[int, int]] = self._generate_obstacles()
    
    def _generate_random_position(self, exclude: list) -> Position:
        while True:
            pos = Position(random.randint(0, self.width - 1), 
                           random.randint(0, self.height - 1))
            if pos not in exclude:
                return pos
    
    def _generate_obstacles(self) -> Set[Tuple[int, int]]:
        obstacles = set()
        for _ in range(self.width * self.height // 10):
            obs = self._generate_random_position(exclude=[self.agent_pos, self.goal_pos])
            obstacles.add((obs.x, obs.y))
        return obstacles
    
    def is_valid_position(self, pos: Position) -> bool:
        return (0 <= pos.x < self.width and 
                0 <= pos.y < self.height and 
                (pos.x, pos.y) not in self.obstacles)
    
    def move_agent(self, action: Action) -> bool:
        action_map = {
            Action.MOVE_UP: Position(0, -1),
            Action.MOVE_DOWN: Position(0, 1),
            Action.MOVE_LEFT: Position(-1, 0),
            Action.MOVE_RIGHT: Position(1, 0),
            Action.STAY: Position(0, 0)
        }
        
        new_pos = self.agent_pos + action_map[action]
        if self.is_valid_position(new_pos):
            self.agent_pos = new_pos
            return True
        return False
    
    def get_state(self) -> dict:
        return {
            'agent_pos': self.agent_pos,
            'goal_pos': self.goal_pos,
            'distance_to_goal': abs(self.agent_pos.x - self.goal_pos.x) + 
                                abs(self.agent_pos.y - self.goal_pos.y),
            'at_goal': self.agent_pos == self.goal_pos
        }

class SmartReflexAgent:
    def __init__(self):
        self.name = "Smart Reflex Agent"
        self.last_failed_action = None
    
    def choose_action(self, state: dict) -> Action:
        agent_pos = state['agent_pos']
        goal_pos = state['goal_pos']
        
        if state['at_goal']:
            return Action.STAY
        
        dx = goal_pos.x - agent_pos.x
        dy = goal_pos.y - agent_pos.y
        
        if abs(dx) > abs(dy):
            preferred_action = Action.MOVE_RIGHT if dx > 0 else Action.MOVE_LEFT
        else:
            preferred_action = Action.MOVE_DOWN if dy > 0 else Action.MOVE_UP
        
        if preferred_action == self.last_failed_action:
            if preferred_action in (Action.MOVE_UP, Action.MOVE_DOWN):
                return Action.MOVE_LEFT if random.random() < 0.5 else Action.MOVE_RIGHT
            else:
                return Action.MOVE_UP if random.random() < 0.5 else Action.MOVE_DOWN
        
        return preferred_action

# --- Pygame Simulation ---
def run_simulation_with_graphics():
    pygame.init()
    
    grid_size = 10
    cell_size = 50
    screen = pygame.display.set_mode((grid_size * cell_size, grid_size * cell_size))
    pygame.display.set_caption("Smart Reflex Agent")
    clock = pygame.time.Clock()

    env = Environment(grid_size, grid_size)
    agent = SmartReflexAgent()

    running = True
    steps = 0

    def draw_environment():
        screen.fill((255, 255, 255))
        for x in range(grid_size):
            for y in range(grid_size):
                rect = pygame.Rect(x * cell_size, y * cell_size, cell_size, cell_size)
                pygame.draw.rect(screen, (220, 220, 220), rect, 1)

        for ox, oy in env.obstacles:
            pygame.draw.rect(screen, (255, 0, 0), pygame.Rect(ox * cell_size, oy * cell_size, cell_size, cell_size))

        goal = env.goal_pos
        pygame.draw.rect(screen, (0, 255, 0), pygame.Rect(goal.x * cell_size, goal.y * cell_size, cell_size, cell_size))

        agent_pos = env.agent_pos
        pygame.draw.rect(screen, (0, 0, 255), pygame.Rect(agent_pos.x * cell_size, agent_pos.y * cell_size, cell_size, cell_size))

        pygame.display.flip()

    while running and steps < 100:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        state = env.get_state()
        if state['at_goal']:
            print(f"Goal reached in {steps} steps!")
            break

        action = agent.choose_action(state)
        success = env.move_agent(action)
        if not success:
            agent.last_failed_action = action
        else:
            agent.last_failed_action = None

        draw_environment()
        steps += 1
        clock.tick(5)  # Slow down for visualization

    if not state['at_goal']:
        print("Agent failed to reach goal.")

    pygame.quit()

if __name__ == "__main__":
    run_simulation_with_graphics()
