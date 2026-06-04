import random


class MazeGenerator:
    """Generates a maze using recursive backtracking (DFS)."""

    def __init__(self, width, height):
        self.width = width if width > 0 else 1
        self.height = height if height > 0 else 1
        self.grid = []

    def generate(self, seed=None):
        """Generate maze using recursive backtracking. Returns 2D grid of booleans (True=wall, False=floor)."""
        if seed is not None:
            random.seed(seed)

        self.grid = [[True for _ in range(self.width)] for _ in range(self.height)]

        start_x = 1 if self.width > 1 else 0
        start_y = 1 if self.height > 1 else 0
        self.grid[start_y][start_x] = False
        self._carve(start_x, start_y)

        return self.grid

    def _carve(self, x, y):
        """Recursive backtracking from position."""
        directions = [(0, -2), (2, 0), (0, 2), (-2, 0)]
        random.shuffle(directions)

        for dx, dy in directions:
            nx, ny = x + dx, y + dy
            if 0 < nx < self.width - 1 and 0 < ny < self.height - 1 and self.grid[ny][nx]:
                self.grid[y + dy // 2][x + dx // 2] = False
                self.grid[ny][nx] = False
                self._carve(nx, ny)

    def is_wall(self, x, y):
        """Check if cell is a wall."""
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.grid[y][x]
        return True
