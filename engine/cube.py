from .mesh_object import MeshObject
from panda3d.core import (
	GeomVertexFormat, GeomVertexData, GeomVertexWriter,
	Geom, GeomTriangles, GeomNode
)
from direct.showbase.ShowBase import ShowBase

# Global created by ShowBase
base: ShowBase

class Cube:
	"""A cube entity that uses a MeshObject"""

	def __init__(self, engine, name='Cube', size=1, color=(1, 1, 1, 1)):
		self.engine = engine
		self.name = name
		self.mesh = MeshObject(engine, name)
		self._create_cube_geometry(size, color)

	def _create_cube_geometry(self, size, color):
		"""Create a cube mesh procedurally"""
		half = size / 2

		# Vertices for a cube
		vertices = [
			# Front face
			(-half, -half, -half), (half, -half, -half), (half, -half, half), (-half, -half, half),
			# Back face
			(-half, half, -half), (half, half, -half), (half, half, half), (-half, half, half),
			# Left face
			(-half, -half, -half), (-half, half, -half), (-half, half, half), (-half, -half, half),
			# Right face
			(half, -half, -half), (half, half, -half), (half, half, half), (half, -half, half),
			# Bottom face
			(-half, -half, -half), (half, -half, -half), (half, half, -half), (-half, half, -half),
			# Top face
			(-half, -half, half), (half, -half, half), (half, half, half), (-half, half, half),
		]

		# Normals for each face
		normals = [
			(0, -1, 0), (0, -1, 0), (0, -1, 0), (0, -1, 0),  # Front
			(0, 1, 0), (0, 1, 0), (0, 1, 0), (0, 1, 0),  # Back
			(-1, 0, 0), (-1, 0, 0), (-1, 0, 0), (-1, 0, 0),  # Left
			(1, 0, 0), (1, 0, 0), (1, 0, 0), (1, 0, 0),  # Right
			(0, 0, -1), (0, 0, -1), (0, 0, -1), (0, 0, -1),  # Bottom
			(0, 0, 1), (0, 0, 1), (0, 0, 1), (0, 0, 1),  # Top
		]

		# Create vertex data
		format = GeomVertexFormat.get_v3n3c4()
		vdata = GeomVertexData('cube', format, Geom.UHStatic)
		vdata.setNumRows(24)

		vertex = GeomVertexWriter(vdata, 'vertex')
		normal = GeomVertexWriter(vdata, 'normal')
		color_writer = GeomVertexWriter(vdata, 'color')

		for i, v in enumerate(vertices):
			vertex.addData3(*v)
			normal.addData3(*normals[i])
			color_writer.addData4(*color)

		# Create triangles (two per face)
		tris = GeomTriangles(Geom.UHStatic)
		for face in range(6):
			base_idx = face * 4
			tris.addVertices(base_idx, base_idx + 1, base_idx + 2)
			tris.addVertices(base_idx, base_idx + 2, base_idx + 3)
		tris.closePrimitive()

		# Create geom
		geom = Geom(vdata)
		geom.addPrimitive(tris)

		node = GeomNode(self.name)
		node.addGeom(geom)

		# Attach to mesh
		self.mesh.model = self.mesh.node.attachNewNode(node)
		self.mesh.model.setTwoSided(True)

	# Delegate to mesh
	@property
	def position(self):
		return self.mesh.position

	@position.setter
	def position(self, value):
		self.mesh.position = value

	@property
	def rotation(self):
		return self.mesh.rotation

	@rotation.setter
	def rotation(self, value):
		self.mesh.rotation = value

	@property
	def scale(self):
		return self.mesh.scale

	@scale.setter
	def scale(self, value):
		self.mesh.scale = value

	@property
	def visible(self):
		return self.mesh.visible

	@visible.setter
	def visible(self, value):
		self.mesh.visible = value

	def show(self):
		self.mesh.show()

	def hide(self):
		self.mesh.hide()

	def set_color(self, r, g, b, a=1):
		"""Change cube color"""
		if self.mesh.model:
			self.mesh.model.setColor(r, g, b, a)

	def update(self, dt):
		"""Override for custom logic"""
		pass

	def render(self, renderer):
		"""Render the cube"""
		self.mesh.render(renderer)

	def destroy(self):
		self.mesh.destroy()