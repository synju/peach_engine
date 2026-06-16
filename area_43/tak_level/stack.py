from area_43.tak_level.board_block import BoardBlock
from area_43.tak_level.flat import Flat


class Stack:
    def __init__(self, board_x, board_y):
        self.x = board_x * BoardBlock.WIDTH
        self.y = board_y * BoardBlock.LENGTH
        self.flats = []

    def push(self, engine, color):
        layer_index = len(self.flats)
        flat = Flat(engine, color=color, x=self.x, y=self.y, layer_index=layer_index)
        self.flats.append(flat)
        return flat

    def pop(self):
        flat = self.flats.pop()
        flat.destroy()
        return flat

    def get_top(self):
        return self.flats[-1] if self.flats else None

    def height(self):
        return len(self.flats)

    def destroy(self):
        for flat in self.flats:
            flat.destroy()
        self.flats = []
