from .maze_generator import MazeGenerator
from .box import Box


class Maze:
    """Creates a 3D maze from maze generator output."""

    def __init__(self, engine, size=15, cell_height=3, cell_thickness=1, seed=None):
        self.engine = engine
        self.size = size
        self.cell_height = cell_height
        self.cell_thickness = cell_thickness
        self.boxes = []

        generator = MazeGenerator(size, size)
        self.grid = generator.generate(seed=seed)

    def spawn(self, offset_x=0, offset_y=0):
        """Spawn all maze geometry at given offset."""
        for y in range(self.size):
            for x in range(self.size):
                if self.grid[y][x]:
                    box = Box(
                        self.engine,
                        name=f"cell_{x}_{y}",
                        width=self.cell_thickness,
                        length=self.cell_thickness,
                        height=self.cell_height,
                        color=(0.3, 0.3, 0.3, 1),
                        collision_enabled=True,
                    )
                    box.set_position(offset_x + x, offset_y + y, self.cell_height / 2)
                    self.boxes.append(box)

    def destroy(self):
        """Clean up all boxes."""
        for box in self.boxes:
            box.destroy()
        self.boxes.clear()
