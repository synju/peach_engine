"""
Demo runner for Peach Engine
"""
from engine.peach_engine import PeachEngine
from engine.default_scene import DefaultScene


if __name__ == '__main__':
    engine = PeachEngine(
        width=1280,
        height=720,
        title="Peach Engine Demo",
        fps=60
    )

    engine.scene_handler.add_scene('default', DefaultScene(engine))
    engine.scene_handler.set_scene('default')
    engine.run()