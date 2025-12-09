from direct.showbase.ShowBase import ShowBase
from panda3d.core import TransformState
from panda3d.bullet import BulletTriangleMesh, BulletTriangleMeshShape, BulletRigidBodyNode

base: ShowBase

class Utils:
	"""Utility functions for the engine"""

	def __init__(self, engine):
		self.engine = engine

	def add_mesh_collider(self, mesh_object, physics_world):
		"""
		Add Bullet collision to a MeshObject.
		Attaches collision_body and collision_np to the mesh_object.
		"""
		mesh = BulletTriangleMesh()

		for geom_np in mesh_object.node.findAllMatches('**/+GeomNode'):
			geom_node = geom_np.node()
			mat = geom_np.getMat(base.render)
			ts = TransformState.makeMat(mat)
			for i in range(geom_node.getNumGeoms()):
				mesh.addGeom(geom_node.getGeom(i), True, ts)

		shape = BulletTriangleMeshShape(mesh, dynamic=False)
		body = BulletRigidBodyNode(f'{mesh_object.name}_collision')
		body.addShape(shape)

		mesh_object.collision_body = body
		mesh_object.collision_np = base.render.attachNewNode(body)
		physics_world.attachRigidBody(body)
