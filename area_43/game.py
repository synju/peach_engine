from engine.peach_engine import PeachEngine
from area_43.scenes.workshop import WorkshopScene

if __name__ == '__main__':
    # Create engine
    engine = PeachEngine(
        width=1280,
        height=720,
        title="Area 43",
        fps=60,
    )
    engine.debug_enabled = False

    # Add scenes
    engine.scene_handler.add_scene('workshop', WorkshopScene(engine))

    # Set starting scene
    engine.scene_handler.set_scene('workshop')

    # Run the engine\
    engine.run()