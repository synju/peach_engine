from engine.peach_engine import PeachEngine
from area_43.scenes.maze import MazeScene

if __name__ == '__main__':
    engine = PeachEngine(
        width=1280,
        height=720,
        title="Maze",
        fps=60,
    )
    engine.debug_enabled = False

    engine.scene_handler.add_scene('maze', MazeScene(engine))
    engine.scene_handler.set_scene('maze')

    engine.run()