from direct.showbase.ShowBase import ShowBase
from panda3d.core import NodePath

# Global created by ShowBase
base: ShowBase

class MeshObject:
	"""A 3D mesh with position, rotation, scale, and visibility"""

	def __init__(self, engine, name='MeshObject', model_path=None, position=None, rotation=None, scale=None, collision_enabled=False):
		self.engine = engine
		self.name = name
		self.model = None
		self.texture = None

		# Create a node for transforms
		self.node = NodePath(name)
		self.node.reparentTo(base.render)

		# Transform
		self._position = [0, 0, 0]
		self._rotation = [0, 0, 0]
		self._scale = [1, 1, 1]

		# Visibility
		self._visible = True

		# Load model if path provided
		if model_path:
			self.load_model(model_path)

		# Apply initial transforms
		if position:
			self.position = position
		if rotation:
			self.rotation = rotation
		if scale:
			self.scale = scale

		if collision_enabled:
			self.engine.utils.add_mesh_collider(self, self.engine.physics)

	# Position
	@property
	def position(self):
		return self._position

	@position.setter
	def position(self, value):
		self._position = list(value)
		self.node.setPos(*self._position)

	# Rotation
	@property
	def rotation(self):
		return self._rotation

	@rotation.setter
	def rotation(self, value):
		self._rotation = list(value)
		# HPR = heading, pitch, roll
		self.node.setHpr(self._rotation[1], self._rotation[0], self._rotation[2])

	# Scale
	@property
	def scale(self):
		return self._scale

	@scale.setter
	def scale(self, value):
		if isinstance(value, (int, float)):
			self._scale = [value, value, value]
		else:
			self._scale = list(value)
		self.node.setScale(*self._scale)

	# Visibility
	@property
	def visible(self):
		return self._visible

	@visible.setter
	def visible(self, value):
		self._visible = value
		if value:
			self.node.show()
		else:
			self.node.hide()

	def show(self):
		"""Show the mesh"""
		self.visible = True

	def hide(self):
		"""Hide the mesh"""
		self.visible = False

	def load_model(self, path):
		"""Load a 3D model"""
		try:
			self.model = base.loader.loadModel(path)
			if self.model:
				self.model.reparentTo(self.node)
				self._clamp_textures()
			return True
		except Exception as e:
			print(f"Could not load model {path}: {e}")
			return False

	def _clamp_textures(self):
		"""Prevent texture edge bleeding into transparent areas"""
		from panda3d.core import SamplerState, LColor

		if not self.model:
			return

		for tex_stage in self.model.findAllTextureStages():
			tex = self.model.findTexture(tex_stage)
			if tex:
				tex.setWrapU(SamplerState.WM_border_color)
				tex.setWrapV(SamplerState.WM_border_color)
				tex.setBorderColor(LColor(0, 0, 0, 1))

	def load_texture(self, path):
		"""Load and apply a texture"""
		try:
			self.texture = base.loader.loadTexture(path)
			if self.texture and self.model:
				self.model.setTexture(self.texture)
			return True
		except Exception as e:
			print(f"Could not load texture {path}: {e}")
			return False

	def set_texture(self, texture):
		"""Set an already loaded texture"""
		self.texture = texture
		if self.model and texture:
			self.model.setTexture(texture)

	def set_color(self, r, g, b, a=1):
		"""Set solid color on the mesh"""
		if self.model:
			self.model.setColor(r, g, b, a)

	def render(self, renderer):
		"""Called in render loop"""
		pass

	def destroy(self):
		"""Clean up"""
		self.node.removeNode()
		self.node = None
		self.model = None

	def __repr__(self):
		return f"MeshObject('{self.name}')"
