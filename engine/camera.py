import math
from direct.showbase.ShowBase import ShowBase

# Global created by ShowBase
base: ShowBase

class Camera:
	"""Base camera class for Panda3D (Z-up coordinate system)"""

	def __init__(self, engine, position=(0, 0, 2), rotation=(0, 0, 0), near_clip=0.1, far_clip=10000):
		self.engine = engine
		# Position as [x, y, z] - Panda3D: X=right, Y=forward, Z=up
		self.position = list(position)
		# Rotation as [pitch, heading, roll]
		self.rotation = list(rotation)
		self.active = False

		# Clipping distances
		self._near_clip = near_clip
		self._far_clip = far_clip

	def activate(self):
		"""Activate this camera"""
		self.active = True
		self._apply_clip_distances()
		self._apply_transform()

	def deactivate(self):
		"""Deactivate this camera"""
		self.active = False

	def _apply_clip_distances(self):
		"""Apply near/far clip distances to lens"""
		base.camLens.setNear(self._near_clip)
		base.camLens.setFar(self._far_clip)

	@property
	def near_clip(self):
		return self._near_clip

	@near_clip.setter
	def near_clip(self, value):
		self._near_clip = value
		if self.active:
			base.camLens.setNear(value)

	@property
	def far_clip(self):
		return self._far_clip

	@far_clip.setter
	def far_clip(self, value):
		self._far_clip = value
		if self.active:
			base.camLens.setFar(value)

	def _apply_transform(self):
		"""Apply position and rotation to Panda3D camera"""
		if not self.active:
			return

		base.camera.setPos(self.position[0], self.position[1], self.position[2])
		# HPR = heading, pitch, roll
		base.camera.setHpr(self.rotation[1], self.rotation[0], self.rotation[2])

	def handle_input(self, input_handler):
		"""Override in subclass"""
		pass

	def update(self, dt):
		"""Override in subclass"""
		pass