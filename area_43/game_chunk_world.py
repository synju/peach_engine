from engine.peach_engine import PeachEngine
from area_43.scenes.chunk_world import ChunkWorldScene

if __name__ == '__main__':
    engine = PeachEngine(
        width=1280,
        height=720,
        title="Chunk World",
        fps=60,
    )
    engine.debug_enabled = False

    engine.scene_handler.add_scene('chunk_world', ChunkWorldScene(engine))
    engine.scene_handler.set_scene('chunk_world')

    engine.run()