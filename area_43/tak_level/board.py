from area_43.tak_level.board_block import BoardBlock


class Board:
    def __init__(self, engine, size=5):
        self.engine = engine
        self.size = size
        self.blocks = []
        self._create()

    def _create(self):
        for y in range(self.size):
            for x in range(self.size):
                color = BoardBlock.BLACK if (x + y) % 2 == 0 else BoardBlock.WHITE
                #block = BoardBlock(self.engine, color, x=x * 2, y=y * 2, z=-0.125)
                block = BoardBlock(self.engine, color, x=x * 2, y=y * 2, z=0.125)
                self.blocks.append(block)

    def destroy(self):
        for block in self.blocks:
            block.destroy()
        self.blocks = []
