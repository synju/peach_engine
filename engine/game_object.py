# game_object.py
from direct.showbase.ShowBase import ShowBase
from panda3d.core import NodePath

base: ShowBase

class GameObject:
	"""Base game object - container for components - includes interaction support"""

	def __init__(self, engine, name='GameObject', position=(0, 0, 0), rotation=(0, 0, 0), scale=1):
		self.engine = engine
		self.name = name

		# Debug
		self.debug_mode = True
		self._debug_collision_visual = None

		# Root node
		self.node = NodePath(name)
		self.node.reparentTo(base.render)

		# Components
		self.mesh = None
		self.light = None
		self.sounds = {}

		# Transform
		self._position = list(position)
		self._rotation = list(rotation)
		if isinstance(scale, (int, float)):
			self._scale = [scale, scale, scale]
		else:
			self._scale = list(scale)

		# Interaction
		self._interact_callback = None
		self.interact_distance = 2.5

		# Apply initial transform
		self._apply_transform()

	def _apply_transform(self):
		self.node.setPos(*self._position)
		self.node.setHpr(self._rotation[1], self._rotation[0], self._rotation[2])
		self.node.setScale(*self._scale)

	@property
	def position(self):
		return self._position

	@position.setter
	def position(self, value):
		self._position = list(value)
		self._apply_transform()

	@property
	def rotation(self):
		return self._rotation

	@rotation.setter
	def rotation(self, value):
		self._rotation = list(value)
		self._apply_transform()

	@property
	def scale(self):
		return self._scale

	@scale.setter
	def scale(self, value):
		if isinstance(value, (int, float)):
			self._scale = [value, value, value]
		else:
			self._scale = list(value)
		self._apply_transform()

	# Components
	def set_mesh(self, mesh_object):
		"""Attach a MeshObject for rendering"""
		self.mesh = mesh_object

	def set_light(self, light):
		"""Attach a light"""
		self.light = light

	def add_sound(self, name, filepath):
		"""Add a sound effect"""
		self.sounds[name] = filepath

	def play_sound(self, name):
		"""Play a sound by name"""
		if name in self.sounds:
			self.engine.sound_player.play_effect(self.sounds[name])

	# Interaction
	def set_interact(self, callback):
		"""Set function to call when player interacts"""
		self._interact_callback = callback

		# Auto-register with current scene
		scene = self.engine.scene_handler.current_scene
		if scene and hasattr(scene, 'interactive_objects'):
			if self not in scene.interactive_objects:
				scene.interactive_objects.append(self)

	def interact(self):
		"""Called when player interacts with this object"""
		if self._interact_callback:
			self._interact_callback()
			return True
		return False

	@property
	def is_interactive(self):
		return self._interact_callback is not None

	@property
	def collision_body(self):
		"""Get collision body from mesh if it has one"""
		if self.mesh and hasattr(self.mesh, 'collision_body'):
			return self.mesh.collision_body
		return None

	def _update_debug_collision(self):
		"""Draw collision shape wireframe"""
		from panda3d.core import LineSegs

		if self._debug_collision_visual:
			self._debug_collision_visual.removeNode()
			self._debug_collision_visual = None

		if not self.debug_mode or not self.mesh or not self.mesh.node:
			return

		bounds = self.mesh.node.getTightBounds()
		if not bounds:
			return

		min_pt, max_pt = bounds

		lines = LineSegs()
		lines.setThickness(2)
		lines.setColor(0, 1, 1, 1)

		# Bottom face
		lines.moveTo(min_pt.x, min_pt.y, min_pt.z)
		lines.drawTo(max_pt.x, min_pt.y, min_pt.z)
		lines.drawTo(max_pt.x, max_pt.y, min_pt.z)
		lines.drawTo(min_pt.x, max_pt.y, min_pt.z)
		lines.drawTo(min_pt.x, min_pt.y, min_pt.z)

		# Top face
		lines.moveTo(min_pt.x, min_pt.y, max_pt.z)
		lines.drawTo(max_pt.x, min_pt.y, max_pt.z)
		lines.drawTo(max_pt.x, max_pt.y, max_pt.z)
		lines.drawTo(min_pt.x, max_pt.y, max_pt.z)
		lines.drawTo(min_pt.x, min_pt.y, max_pt.z)

		# Vertical edges
		lines.moveTo(min_pt.x, min_pt.y, min_pt.z)
		lines.drawTo(min_pt.x, min_pt.y, max_pt.z)
		lines.moveTo(max_pt.x, min_pt.y, min_pt.z)
		lines.drawTo(max_pt.x, min_pt.y, max_pt.z)
		lines.moveTo(max_pt.x, max_pt.y, min_pt.z)
		lines.drawTo(max_pt.x, max_pt.y, max_pt.z)
		lines.moveTo(min_pt.x, max_pt.y, min_pt.z)
		lines.drawTo(min_pt.x, max_pt.y, max_pt.z)

		self._debug_collision_visual = base.render.attachNewNode(lines.create())
		self._debug_collision_visual.setLightOff()

	# Lifecycle
	def update(self, dt):
		"""Override in subclass"""
		self._update_debug_collision()

	def destroy(self):
		if self._debug_collision_visual:
			self._debug_collision_visual.removeNode()
		if self.mesh:
			self.mesh.destroy()
		if self.light:
			self.light.destroy()
		if self.node:
			self.node.removeNode()
			self.node = None
