"""
Example usage of Peach Engine
"""
from peach_engine import PeachEngine
from default_scene import DefaultScene


if __name__ == '__main__':
    # Create engine
    engine = PeachEngine(
        width=1280,
        height=720,
        title="Peach Engine Demo",
        fps=60
    )

    # Add scenes
    engine.scene_handler.add_scene('default', DefaultScene(engine))

    # Set starting scene
    engine.scene_handler.set_scene('default')

    # Run the engine
    engine.run()