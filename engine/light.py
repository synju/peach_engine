from direct.showbase.ShowBase import ShowBase
from panda3d.core import (
	AmbientLight as PandaAmbientLight,
	DirectionalLight as PandaDirectionalLight,
	PointLight as PandaPointLight,
	Vec4, BillboardEffect
)

# Global created by ShowBase
base: ShowBase

class Light:
	"""Base class for all lights"""

	def __init__(self, engine, name='Light', color=(1, 1, 1, 1), light_enabled=True):
		self.engine = engine
		self.name = name
		self._color = list(color)
		self._enabled = light_enabled
		self.light = None
		self.node = None
		self._position = [0, 0, 0]

		# Debug icon
		self._debug_icon = None

	def _create_debug_icon(self):
		"""Create billboard sprite for debug visualization"""
		if self._debug_icon:
			return

		from panda3d.core import CardMaker
		import os

		# Match light.png aspect ratio (251x365 = ~0.69 width/height)
		cm = CardMaker('light_icon')
		cm.setFrame(-0.35, 0.35, -0.5, 0.5)  # 0.7 wide x 1.0 tall

		self._debug_icon = base.render.attachNewNode(cm.generate())

		# Load texture - path relative to engine module
		try:
			from panda3d.core import Filename
			engine_dir = os.path.dirname(os.path.abspath(__file__))
			tex_path = os.path.join(engine_dir, 'assets', 'images', 'light.png')
			tex = base.loader.loadTexture(Filename.fromOsSpecific(tex_path))
			self._debug_icon.setTexture(tex)
			self._debug_icon.setTransparency(1)
		except Exception as e:
			print(f"Could not load light icon: {e}")
			# Fallback - just use yellow color
			self._debug_icon.setColor(1, 1, 0, 1)

		# Billboard effect - always faces camera
		self._debug_icon.setBillboardPointEye()
		self._debug_icon.setLightOff()  # Don't light the icon
		self._debug_icon.setBin('fixed', 100)  # Render on top

		# Position at light
		self._debug_icon.setPos(*self._position)

	def _update_debug_icon(self):
		"""Update debug icon visibility and position based on engine debug mode"""
		if self.engine.debug_enabled:
			if not self._debug_icon:
				self._create_debug_icon()
			self._debug_icon.setPos(*self._position)
			self._debug_icon.show()
		else:
			if self._debug_icon:
				self._debug_icon.hide()

	@property
	def color(self):
		return self._color

	@color.setter
	def color(self, value):
		self._color = list(value)
		if self.light:
			self.light.setColor(Vec4(*self._color))

	@property
	def enabled(self):
		return self._enabled

	@enabled.setter
	def enabled(self, value):
		self._enabled = value
		if self.node:
			if value:
				base.render.setLight(self.node)
			else:
				base.render.clearLight(self.node)

	@property
	def position(self):
		return self._position

	@position.setter
	def position(self, value):
		self._position = list(value)
		self._update_debug_icon()

	def turn_on(self):
		"""Turn the light on"""
		self.enabled = True

	def turn_off(self):
		"""Turn the light off"""
		self.enabled = False

	def toggle_light(self):
		"""Toggle light on/off"""
		self.enabled = not self._enabled

	def update(self):
		"""Call each frame to update debug icon visibility"""
		self._update_debug_icon()

	def destroy(self):
		if self._debug_icon:
			self._debug_icon.removeNode()
			self._debug_icon = None
		if self.node:
			base.render.clearLight(self.node)
			self.node.removeNode()
		self.light = None
		self.node = None


class AmbientLight(Light):
	"""Ambient light - illuminates everything equally"""

	def __init__(self, engine, name='AmbientLight', color=(0.2, 0.2, 0.2, 1), light_enabled=True):
		super().__init__(engine, name, color, light_enabled)

		self.light = PandaAmbientLight(name)
		self.light.setColor(Vec4(*self._color))

		self.node = base.render.attachNewNode(self.light)
		if self._enabled:
			base.render.setLight(self.node)

	def _update_debug_icon(self):
		"""Ambient light has no position - skip debug icon"""
		pass

class DirectionalLight(Light):
	"""Directional light - like the sun, parallel rays"""

	def __init__(self, engine, name='DirectionalLight', color=(1, 1, 1, 1), direction=(0, 0, -1), position=(0, 0, 10), light_enabled=True):
		super().__init__(engine, name, color, light_enabled)
		self._direction = list(direction)
		self._position = list(position)
		self._debug_arrow = None

		self.light = PandaDirectionalLight(name)
		self.light.setColor(Vec4(*self._color))

		self.node = base.render.attachNewNode(self.light)
		self.direction = direction
		if self._enabled:
			base.render.setLight(self.node)

	def _create_debug_arrow(self):
		"""Create arrow showing light direction"""
		if self._debug_arrow:
			self._debug_arrow.removeNode()

		from panda3d.core import GeomVertexFormat, GeomVertexData, GeomVertexWriter
		from panda3d.core import Geom, GeomLines, GeomNode, NodePath

		# Arrow length
		length = 3
		dx, dy, dz = self._direction
		# Normalize
		mag = (dx * dx + dy * dy + dz * dz) ** 0.5
		if mag > 0:
			dx, dy, dz = dx / mag, dy / mag, dz / mag

		# Arrow end point
		end = (
			self._position[0] + dx * length,
			self._position[1] + dy * length,
			self._position[2] + dz * length
		)

		# Create line geometry
		format = GeomVertexFormat.get_v3c4()
		vdata = GeomVertexData('arrow', format, Geom.UHStatic)
		vdata.setNumRows(2)

		vertex = GeomVertexWriter(vdata, 'vertex')
		color_writer = GeomVertexWriter(vdata, 'color')

		# Main line
		vertex.addData3(*self._position)
		vertex.addData3(*end)
		color_writer.addData4(1, 1, 0, 1)  # Yellow
		color_writer.addData4(1, 0.5, 0, 1)  # Orange at tip

		lines = GeomLines(Geom.UHStatic)
		lines.addVertices(0, 1)
		lines.closePrimitive()

		geom = Geom(vdata)
		geom.addPrimitive(lines)

		node = GeomNode('direction_arrow')
		node.addGeom(geom)

		self._debug_arrow = base.render.attachNewNode(node)
		self._debug_arrow.setRenderModeThickness(3)
		self._debug_arrow.setLightOff()
		self._debug_arrow.setBin('fixed', 100)

	def _update_debug_icon(self):
		"""Update debug icon and arrow visibility"""
		super()._update_debug_icon()

		if self.engine.debug_enabled:
			self._create_debug_arrow()
			self._debug_arrow.show()
		else:
			if self._debug_arrow:
				self._debug_arrow.hide()

	@property
	def direction(self):
		return self._direction

	@direction.setter
	def direction(self, value):
		self._direction = list(value)
		if self.node:
			self.node.lookAt(value[0], value[1], value[2])
		if self._debug_arrow and self.engine.debug_enabled:
			self._create_debug_arrow()

	@property
	def position(self):
		return self._position

	@position.setter
	def position(self, value):
		self._position = list(value)
		self._update_debug_icon()

	def destroy(self):
		if self._debug_arrow:
			self._debug_arrow.removeNode()
			self._debug_arrow = None
		super().destroy()


class PointLight(Light):
	"""Point light - emits from a position in all directions"""

	def __init__(self, engine, name='PointLight', color=(1, 1, 1, 1), position=(0, 0, 0), light_enabled=True):
		super().__init__(engine, name, color, light_enabled)

		self.light = PandaPointLight(name)
		self.light.setColor(Vec4(*self._color))

		self.node = base.render.attachNewNode(self.light)
		self.position = position
		if self._enabled:
			base.render.setLight(self.node)

	@property
	def position(self):
		return self._position

	@position.setter
	def position(self, value):
		self._position = list(value)
		if self.node:
			self.node.setPos(*self._position)
		self._update_debug_icon()