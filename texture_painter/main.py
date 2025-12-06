"""
Texture Painter Application
Uses ImGui for UI

Install dependency: pip install imgui[full]
"""
from engine.peach_engine import PeachEngine
from texture_painter.scenes.texture_painter_scene import TexturePainterScene

if __name__ == '__main__':
	# Create engine
	engine = PeachEngine(
		width=1400,
		height=900,
		title="Texture Painter",
		fps=60
	)

	# Disable debug mode for cleaner look
	engine.debug_enabled = False

	# Add scene
	engine.scene_handler.add_scene('painter', TexturePainterScene(engine))

	# Set starting scene
	engine.scene_handler.set_scene('painter')

	# Run the engine
	engine.run()