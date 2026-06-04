from engine.mesh_object import MeshObject
from panda3d.core import GeomVertexFormat, GeomVertexData, GeomVertexWriter
from panda3d.core import Geom, GeomTriangles, GeomNode


class Chunk:
    def __init__(
        self,
        engine,
        name="Chunk",
        size_x=16,
        size_y=16,
        size_z=16,
        offset_x=0,
        offset_y=0,
        offset_z=0,
        collision_enabled=False,
    ):
        self.engine = engine
        self.name = name
        self.size_x = size_x
        self.size_y = size_y
        self.size_z = size_z
        self.offset = (offset_x, offset_y, offset_z)
        self.voxels = [
            [[0 for _ in range(size_z)] for _ in range(size_y)] for _ in range(size_x)
        ]
        self.mesh = MeshObject(engine, name)
        self.mesh_node = None
        self.collision_body = None
        self.collision_np = None
        self._collision_enabled = collision_enabled
        self._build_mesh()

    def set_voxel(self, x, y, z, voxel_type):
        if 0 <= x < self.size_x and 0 <= y < self.size_y and 0 <= z < self.size_z:
            self.voxels[x][y][z] = voxel_type
            self._build_mesh()

    def get_voxel(self, x, y, z):
        if 0 <= x < self.size_x and 0 <= y < self.size_y and 0 <= z < self.size_z:
            return self.voxels[x][y][z]
        return 0

    def _is_face_exposed(self, x, y, z, face):
        nx, ny, nz = x, y, z
        if face == 0:  # -X
            nx -= 1
        elif face == 1:  # +X
            nx += 1
        elif face == 2:  # -Y
            ny -= 1
        elif face == 3:  # +Y
            ny += 1
        elif face == 4:  # -Z (down)
            nz -= 1
        elif face == 5:  # +Z (up)
            nz += 1

        if (
            nx < 0
            or nx >= self.size_x
            or ny < 0
            or ny >= self.size_y
            or nz < 0
            or nz >= self.size_z
        ):
            return True

        return self.voxels[nx][ny][nz] == 0

    def _build_mesh(self):
        if self.mesh_node:
            self.mesh_node.removeNode()

        if self._collision_enabled and self.collision_np:
            self.collision_np.removeNode()
            self.collision_np = None
            self.collision_body = None

        format = GeomVertexFormat.get_v3n3c4()
        vdata = GeomVertexData("chunk_verts", format, Geom.UHStatic)

        vertex = GeomVertexWriter(vdata, "vertex")
        normal = GeomVertexWriter(vdata, "normal")
        color = GeomVertexWriter(vdata, "color")

        tris = GeomTriangles(Geom.UHStatic)
        vertex_index = 0

        for x in range(self.size_x):
            for y in range(self.size_y):
                for z in range(self.size_z):
                    if self.voxels[x][y][z] == 0:
                        continue

                    world_x = x + self.offset[0]
                    world_y = y + self.offset[1]
                    world_z = z + self.offset[2]

                    for face in range(6):
                        if not self._is_face_exposed(x, y, z, face):
                            continue

                        self._add_face(
                            vertex,
                            normal,
                            color,
                            tris,
                            world_x,
                            world_y,
                            world_z,
                            face,
                            vertex_index,
                        )
                        vertex_index += 4

        if vertex_index == 0:
            return

        vdata.setNumRows(vertex_index)
        geom = Geom(vdata)
        geom.addPrimitive(tris)

        node = GeomNode(self.name)
        node.addGeom(geom)

        self.mesh_node = self.mesh.node.attachNewNode(node)

        if self._collision_enabled:
            self.engine.utils.add_mesh_collider(self.mesh, self.engine.physics)

    def _add_face(self, vertex, normal, color, tris, x, y, z, face, vertex_index):
        h = 0.5

        # Colors: Red, Green, Blue, Black, White, Grey
        face_colors = [
            (1.0, 0.0, 0.0, 1.0),  # face 0: Red (-X)
            (0.0, 1.0, 0.0, 1.0),  # face 1: Green (+X)
            (0.0, 0.0, 1.0, 1.0),  # face 2: Blue (-Y)
            (0.0, 0.0, 0.0, 1.0),  # face 3: Black (+Y)
            (1.0, 1.0, 1.0, 1.0),  # face 4: White (-Z)
            (0.5, 0.5, 0.5, 1.0),  # face 5: Grey (+Z)
        ]
        fc = face_colors[face]

        if face == 0:  # -X (left)
            verts = [
                (x - h, y - h, z - h),
                (x - h, y + h, z - h),
                (x - h, y + h, z + h),
                (x - h, y - h, z + h),
            ]
            norms = [(-1, 0, 0)] * 4
        elif face == 1:  # +X (right)
            verts = [
                (x + h, y - h, z + h),
                (x + h, y + h, z + h),
                (x + h, y + h, z - h),
                (x + h, y - h, z - h),
            ]
            norms = [(1, 0, 0)] * 4
        elif face == 2:  # -Y (back)
            verts = [
                (x + h, y - h, z - h),
                (x + h, y - h, z + h),
                (x - h, y - h, z + h),
                (x - h, y - h, z - h),
            ]
            norms = [(0, -1, 0)] * 4
        elif face == 3:  # +Y (front)
            verts = [
                (x - h, y + h, z - h),
                (x - h, y + h, z + h),
                (x + h, y + h, z + h),
                (x + h, y + h, z - h),
            ]
            norms = [(0, 1, 0)] * 4
        elif face == 4:  # -Z (bottom)
            verts = [
                (x - h, y - h, z - h),
                (x + h, y - h, z - h),
                (x + h, y + h, z - h),
                (x - h, y + h, z - h),
            ]
            norms = [(0, 0, -1)] * 4
        elif face == 5:  # +Z (top)
            verts = [
                (x - h, y - h, z + h),
                (x - h, y + h, z + h),
                (x + h, y + h, z + h),
                (x + h, y - h, z + h),
            ]
            norms = [(0, 0, 1)] * 4

        for i, v in enumerate(verts):
            vertex.addData3(*v)
            normal.addData3(*norms[i])
            color.addData4(*fc)

        # Flip winding order for Red, Green, Grey, White faces (0, 1, 4, 5)
        if face in (0, 1, 4, 5):
            tris.addVertices(vertex_index, vertex_index + 2, vertex_index + 1)
            tris.addVertices(vertex_index, vertex_index + 3, vertex_index + 2)
        else:
            tris.addVertices(vertex_index, vertex_index + 1, vertex_index + 2)
            tris.addVertices(vertex_index, vertex_index + 2, vertex_index + 3)
        tris.closePrimitive()

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
        if self.collision_np:
            self.collision_np.removeNode()
            self.collision_np = None
        if self.collision_body:
            self.engine.physics.removeRigidBody(self.collision_body)
            self.collision_body = None
        self.mesh.destroy()
