from engine.mesh_object import MeshObject
from panda3d.core import GeomVertexFormat, GeomVertexData, GeomVertexWriter
from panda3d.core import Geom, GeomTriangles, GeomNode


class Flat:
    BLACK = (0.1, 0.1, 0.1, 1.0)
    WHITE = (0.9, 0.9, 0.9, 1.0)

    def __init__(self, engine, color=WHITE, x=0, y=0, z=0):
        self.engine = engine
        self.color = color
        self.position = (x, y, z)
        self.mesh = MeshObject(engine, "Flat")
        self.mesh_node = None
        self._build_mesh()

    def _build_mesh(self):
        if self.mesh_node:
            self.mesh_node.removeNode()

        format = GeomVertexFormat.get_v3n3c4()
        vdata = GeomVertexData("flat_verts", format, Geom.UHStatic)

        vertex = GeomVertexWriter(vdata, "vertex")
        normal = GeomVertexWriter(vdata, "normal")
        color = GeomVertexWriter(vdata, "color")

        tris = GeomTriangles(Geom.UHStatic)
        vertex_index = 0

        # Dimensions: width=1.8, height=0.2, length=1.8
        w, h, l = 1.5, 0.5, 1.5
        hw, hh, hl = w / 2, h / 2, l / 2
        ox, oy, oz = self.position

        # 6 faces of a box
        faces = [
            # face 0: -X (left)
            {
                "verts": [
                    (ox - hw, oy - hl, oz - hh),
                    (ox - hw, oy + hl, oz - hh),
                    (ox - hw, oy + hl, oz + hh),
                    (ox - hw, oy - hl, oz + hh),
                ],
                "norms": [(-1, 0, 0)] * 4,
            },
            # face 1: +X (right)
            {
                "verts": [
                    (ox + hw, oy - hl, oz + hh),
                    (ox + hw, oy + hl, oz + hh),
                    (ox + hw, oy + hl, oz - hh),
                    (ox + hw, oy - hl, oz - hh),
                ],
                "norms": [(1, 0, 0)] * 4,
            },
            # face 2: -Y (back)
            {
                "verts": [
                    (ox + hw, oy - hl, oz - hh),
                    (ox + hw, oy - hl, oz + hh),
                    (ox - hw, oy - hl, oz + hh),
                    (ox - hw, oy - hl, oz - hh),
                ],
                "norms": [(0, -1, 0)] * 4,
            },
            # face 3: +Y (front)
            {
                "verts": [
                    (ox - hw, oy + hl, oz - hh),
                    (ox - hw, oy + hl, oz + hh),
                    (ox + hw, oy + hl, oz + hh),
                    (ox + hw, oy + hl, oz - hh),
                ],
                "norms": [(0, 1, 0)] * 4,
            },
            # face 4: -Z (bottom)
            {
                "verts": [
                    (ox - hw, oy - hl, oz - hh),
                    (ox + hw, oy - hl, oz - hh),
                    (ox + hw, oy + hl, oz - hh),
                    (ox - hw, oy + hl, oz - hh),
                ],
                "norms": [(0, 0, -1)] * 4,
            },
            # face 5: +Z (top)
            {
                "verts": [
                    (ox - hw, oy - hl, oz + hh),
                    (ox - hw, oy + hl, oz + hh),
                    (ox + hw, oy + hl, oz + hh),
                    (ox + hw, oy - hl, oz + hh),
                ],
                "norms": [(0, 0, 1)] * 4,
            },
        ]

        for i, face in enumerate(faces):
            verts = face["verts"]
            norms = face["norms"]

            for j, v in enumerate(verts):
                vertex.addData3(*v)
                normal.addData3(*norms[j])
                color.addData4(*self.color)

            # Flip winding for faces that need it (0, 1, 4, 5)
            if i in (0, 1, 4, 5):
                tris.addVertices(vertex_index, vertex_index + 2, vertex_index + 1)
                tris.addVertices(vertex_index, vertex_index + 3, vertex_index + 2)
            else:
                tris.addVertices(vertex_index, vertex_index + 1, vertex_index + 2)
                tris.addVertices(vertex_index, vertex_index + 2, vertex_index + 3)
            tris.closePrimitive()
            vertex_index += 4

        vdata.setNumRows(vertex_index)
        geom = Geom(vdata)
        geom.addPrimitive(tris)

        node = GeomNode("flat")
        node.addGeom(geom)

        self.mesh_node = self.mesh.node.attachNewNode(node)

    def set_position(self, x, y, z):
        self.position = (x, y, z)
        self._build_mesh()

    def show(self):
        if self.mesh_node:
            self.mesh_node.show()

    def hide(self):
        if self.mesh_node:
            self.mesh_node.hide()

    def destroy(self):
        if self.mesh_node:
            self.mesh_node.removeNode()
            self.mesh_node = None
        self.mesh.destroy()
