from direct.showbase.ShowBase import ShowBase
from panda3d.core import Filename, GeomVertexFormat, GeomVertexData, GeomVertexWriter
from panda3d.core import Geom, GeomTriangles, GeomNode, NodePath
import os
import math

# Global created by ShowBase
base: ShowBase

class Skydome:
	"""A skydome that surrounds the scene with a panoramic texture"""

	def __init__(self, engine, texture_path, scale=500, segments=64):
		self.engine = engine
		self._visible = True

		# Create sphere procedurally
		self.node = self._create_sphere(scale, segments)

		# Load and apply texture
		self._load_texture(texture_path)

		# Don't let lighting affect the skydome
		self.node.setLightOff()

		# Render behind everything
		self.node.setBin('background', 0)
		self.node.setDepthWrite(False)

		# Attach to render
		self.node.reparentTo(base.render)

	def _create_sphere(self, radius, segments):
		"""Create an inverted sphere (visible from inside)"""
		format = GeomVertexFormat.get_v3t2()
		vdata = GeomVertexData('skydome', format, Geom.UHStatic)

		vertex = GeomVertexWriter(vdata, 'vertex')
		texcoord = GeomVertexWriter(vdata, 'texcoord')

		# Generate vertices - full sphere
		for i in range(segments + 1):
			lat = math.pi * i / segments  # 0 (top) to pi (bottom)
			for j in range(segments + 1):
				lon = 2 * math.pi * j / segments

				x = radius * math.sin(lat) * math.cos(lon)
				y = radius * math.sin(lat) * math.sin(lon)
				z = radius * math.cos(lat)

				vertex.addData3(x, y, z)

				# UV mapping for equirectangular texture
				u = j / segments
				v = 1.0 - i / segments
				texcoord.addData2(u, v)

		# Generate triangles
		tris = GeomTriangles(Geom.UHStatic)
		for i in range(segments):
			for j in range(segments):
				p0 = i * (segments + 1) + j
				p1 = p0 + 1
				p2 = p0 + (segments + 1)
				p3 = p2 + 1

				# Winding for inside visibility
				tris.addVertices(p0, p1, p2)
				tris.addVertices(p1, p3, p2)

		tris.closePrimitive()

		geom = Geom(vdata)
		geom.addPrimitive(tris)

		node = GeomNode('skydome')
		node.addGeom(geom)

		np = NodePath(node)
		np.setTwoSided(True)  # Visible from both sides
		return np

	def _load_texture(self, texture_path):
		"""Load texture with proper path handling"""
		try:
			if os.path.isabs(texture_path):
				tex = base.loader.loadTexture(Filename.fromOsSpecific(texture_path))
			else:
				tex = base.loader.loadTexture(texture_path)

			if tex:
				self.node.setTexture(tex, 1)
		except Exception as e:
			print(f"Could not load skydome texture: {e}")

	def set_texture(self, texture_path):
		"""Change the skydome texture"""
		self._load_texture(texture_path)

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
		self.visible = True

	def hide(self):
		self.visible = False

	def update(self, dt):
		"""Follow camera position so sky appears infinitely far"""
		if self.engine.renderer.camera:
			pos = self.engine.renderer.camera.position
			self.node.setPos(pos[0], pos[1], pos[2])

	def destroy(self):
		if self.node:
			self.node.removeNode()
			self.node = None