from panda3d.core import (
	GeomVertexFormat, GeomVertexData, GeomVertexWriter,
	Geom, GeomLines, GeomNode, NodePath
)

def create_line(start, end, color=(1, 1, 1, 1), name='line'):
	"""Create a single line between two points"""
	format = GeomVertexFormat.get_v3c4()
	vdata = GeomVertexData(name, format, Geom.UHStatic)
	vdata.setNumRows(2)

	vertex = GeomVertexWriter(vdata, 'vertex')
	color_writer = GeomVertexWriter(vdata, 'color')

	vertex.addData3(*start)
	vertex.addData3(*end)
	color_writer.addData4(*color)
	color_writer.addData4(*color)

	lines = GeomLines(Geom.UHStatic)
	lines.addVertices(0, 1)
	lines.closePrimitive()

	geom = Geom(vdata)
	geom.addPrimitive(lines)

	node = GeomNode(name)
	node.addGeom(geom)

	return NodePath(node)

def create_grid(size=30, color=(0.5, 0.5, 0.5, 1), name='grid'):
	"""Create a grid on the XY plane (Z=0) for Panda3D Z-up"""
	format = GeomVertexFormat.get_v3c4()
	vdata = GeomVertexData(name, format, Geom.UHStatic)

	half = size // 2
	num_lines = (size + 1) * 2
	vdata.setNumRows(num_lines * 2)

	vertex = GeomVertexWriter(vdata, 'vertex')
	color_writer = GeomVertexWriter(vdata, 'color')

	lines = GeomLines(Geom.UHStatic)
	vertex_index = 0

	# Lines along X axis (varying Y)
	for i in range(-half, half + 1):
		vertex.addData3(i, -half, 0)
		vertex.addData3(i, half, 0)
		color_writer.addData4(*color)
		color_writer.addData4(*color)
		lines.addVertices(vertex_index, vertex_index + 1)
		lines.closePrimitive()
		vertex_index += 2

	# Lines along Y axis (varying X)
	for i in range(-half, half + 1):
		vertex.addData3(-half, i, 0)
		vertex.addData3(half, i, 0)
		color_writer.addData4(*color)
		color_writer.addData4(*color)
		lines.addVertices(vertex_index, vertex_index + 1)
		lines.closePrimitive()
		vertex_index += 2

	geom = Geom(vdata)
	geom.addPrimitive(lines)

	node = GeomNode(name)
	node.addGeom(geom)

	return NodePath(node)