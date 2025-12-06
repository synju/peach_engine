from engine.peach_engine import PeachEngine
from plant_sim.scenes.flatlands import FlatlandsScene

if __name__ == '__main__':
    # Create engine
    engine = PeachEngine(
        width=1280,
        height=720,
        title="Plant Sim",
        fps=60
    )

    # Add scenes
    engine.scene_handler.add_scene('flatlands', FlatlandsScene(engine))

    # Set starting scene
    engine.scene_handler.set_scene('flatlands')

    # Run the engine
    engine.run()