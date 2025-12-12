from direct.showbase.ShowBase import ShowBase
from panda3d.core import Fog as PandaFog, Vec4

base: ShowBase


class DistanceFog:
	"""Global distance-based fog (Silent Hill style)"""

	def __init__(self, engine, name='distance_fog', color=(0.5, 0.5, 0.5), density=0.03,
				 mode='exponential', linear_range=(0, 100), fog_enabled=True):
		self.engine = engine
		self.name = name
		self._color = list(color)
		self._density = density
		self._enabled = fog_enabled
		self._mode = mode
		self._linear_range = linear_range

		self.fog = PandaFog(name)
		self.fog.setColor(Vec4(*self._color, 1))
		self.node = base.render.attachNewNode(self.fog)

		if self._mode == 'linear':
			self.fog.setLinearRange(*self._linear_range)
		else:
			self.fog.setExpDensity(self._density)

		if self._enabled:
			base.render.setFog(self.fog)

	def update(self):
		"""Call each frame - required for linear fog to follow camera"""
		if self._mode == 'linear' and self.node:
			cam_pos = base.camera.getPos(base.render)
			self.node.setPos(cam_pos)

	@property
	def color(self):
		return self._color

	@color.setter
	def color(self, value):
		self._color = list(value)
		self.fog.setColor(Vec4(*self._color, 1))

	@property
	def density(self):
		return self._density

	@density.setter
	def density(self, value):
		self._density = value
		if self._mode == 'exponential':
			self.fog.setExpDensity(self._density)

	@property
	def enabled(self):
		return self._enabled

	@enabled.setter
	def enabled(self, value):
		self._enabled = value
		if value:
			base.render.setFog(self.fog)
		else:
			base.render.clearFog()

	def set_exponential(self, density):
		self._mode = 'exponential'
		self._density = density
		self.fog.setExpDensity(density)

	def set_linear(self, start, end):
		self._mode = 'linear'
		self._linear_range = (start, end)
		self.fog.setLinearRange(start, end)

	def turn_on(self):
		self.enabled = True

	def turn_off(self):
		self.enabled = False

	def destroy(self):
		base.render.clearFog()
		if self.node:
			self.node.removeNode()
			self.node = None
		self.fog = None