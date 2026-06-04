from engine.mesh_object import MeshObject
from panda3d.core import (
    GeomVertexFormat, GeomVertexData, GeomVertexWriter,
    Geom, GeomTriangles, GeomNode
)
from direct.showbase.ShowBase import ShowBase

base: ShowBase


class Box:
    def __init__(self, engine, name='Box', width=1, length=1, height=1, color=(1, 1, 1, 1), collision_enabled=False):
        self.engine = engine
        self.name = name
        self.mesh = MeshObject(engine, name)
        self._create_box_geometry(width, length, height, color)
        if collision_enabled:
            self.engine.utils.add_mesh_collider(self.mesh, self.engine.physics)

    def _create_box_geometry(self, width, length, height, color):
        half_w = width / 2
        half_l = length / 2
        half_h = height / 2

        vertices = [
            (-half_w, -half_l, -half_h), (half_w, -half_l, -half_h), (half_w, -half_l, half_h), (-half_w, -half_l, half_h),
            (-half_w, half_l, -half_h), (half_w, half_l, -half_h), (half_w, half_l, half_h), (-half_w, half_l, half_h),
            (-half_w, -half_l, -half_h), (-half_w, half_l, -half_h), (-half_w, half_l, half_h), (-half_w, -half_l, half_h),
            (half_w, -half_l, -half_h), (half_w, half_l, -half_h), (half_w, half_l, half_h), (half_w, -half_l, half_h),
            (-half_w, -half_l, -half_h), (half_w, -half_l, -half_h), (half_w, half_l, -half_h), (-half_w, half_l, -half_h),
            (-half_w, -half_l, half_h), (half_w, -half_l, half_h), (half_w, half_l, half_h), (-half_w, half_l, half_h),
        ]

        normals = [
            (0, -1, 0), (0, -1, 0), (0, -1, 0), (0, -1, 0),
            (0, 1, 0), (0, 1, 0), (0, 1, 0), (0, 1, 0),
            (-1, 0, 0), (-1, 0, 0), (-1, 0, 0), (-1, 0, 0),
            (1, 0, 0), (1, 0, 0), (1, 0, 0), (1, 0, 0),
            (0, 0, -1), (0, 0, -1), (0, 0, -1), (0, 0, -1),
            (0, 0, 1), (0, 0, 1), (0, 0, 1), (0, 0, 1),
        ]

        format = GeomVertexFormat.get_v3n3c4()
        vdata = GeomVertexData('box', format, Geom.UHStatic)
        vdata.setNumRows(24)

        vertex = GeomVertexWriter(vdata, 'vertex')
        normal = GeomVertexWriter(vdata, 'normal')
        color_writer = GeomVertexWriter(vdata, 'color')

        for i, v in enumerate(vertices):
            vertex.addData3(*v)
            normal.addData3(*normals[i])
            color_writer.addData4(*color)

        tris = GeomTriangles(Geom.UHStatic)
        for face in range(6):
            base_idx = face * 4
            tris.addVertices(base_idx, base_idx + 1, base_idx + 2)
            tris.addVertices(base_idx, base_idx + 2, base_idx + 3)
        tris.closePrimitive()

        geom = Geom(vdata)
        geom.addPrimitive(tris)

        node = GeomNode(self.name)
        node.addGeom(geom)

        self.mesh.node.attachNewNode(node)
        self.mesh.node.setTwoSided(True)

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

    def set_color(self, r, g, b, a=1):
        pass

    def show(self):
        pass

    def hide(self):
        pass

    def destroy(self):
        self.mesh.destroy()