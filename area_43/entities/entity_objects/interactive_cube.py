# interactive_cube.py
from engine.game_object import GameObject
from engine.mesh_object import MeshObject

class InteractiveCube(GameObject):
	"""Interactive cube that can be picked up or used"""

	def __init__(self, engine, position=(0, 0, 0), rotation=(0, 0, 0), scale=0.2, collision_enabled=True, debug_mode=False):
		super().__init__(engine, 'InteractiveCube', position, rotation, scale, debug_mode=debug_mode)

		# Mesh with transforms
		mesh = MeshObject(
			engine,
			'cube_mesh',
			'entities/models/cube.gltf',
			position=position,
			rotation=rotation,
			scale=scale,
			collision_enabled=collision_enabled
		)
		self.set_mesh(mesh)