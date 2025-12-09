from panda3d.bullet import BulletWorld, BulletTriangleMesh, BulletTriangleMeshShape, BulletRigidBodyNode
from panda3d.core import TransformState

from area_43.player import Player
from engine.skybox import Skybox
from engine.scene import Scene
from engine.mesh_object import MeshObject
from area_43.first_person_camera import FirstPersonCamera
from engine.light import AmbientLight, DirectionalLight

class WorkshopScene(Scene):
	def __init__(self, engine):
		super().__init__(engine, 'workshop')

		# Disable Grid
		self.engine.scene_handler.grid.hide()

		# Skybox
		self.skybox = None

		# Lighting
		self.ambient_light = None
		self.sun_light = None

		# Physics
		self.physics = None

		# Player
		self.player = None

		# Camera
		self.first_person_camera = None

		# Floor
		self.floor_col = None
		self.floor = None

		# Models
		self.lockers = []
		self.locker = None

	def on_enter(self):
		super().on_enter()

		# Skybox
		self.skybox = Skybox(self.engine, faces={
			'right': ('assets/skydomes/sky_16_2k/sky_16_cubemap_2k/nx.png', 0, True),
			'left': ('assets/skydomes/sky_16_2k/sky_16_cubemap_2k/px.png', 0, True),
			'top': ('assets/skydomes/sky_16_2k/sky_16_cubemap_2k/py.png', 0, True),
			'bottom': ('assets/skydomes/sky_16_2k/sky_16_cubemap_2k/ny.png', 0, False),
			'front': ('assets/skydomes/sky_16_2k/sky_16_cubemap_2k/nz.png', 0, False),
			'back': ('assets/skydomes/sky_16_2k/sky_16_cubemap_2k/pz.png', 0, False),
		})

		# Lighting
		self.ambient_light = AmbientLight(self.engine, 'ambient', color=(0.3, 0.3, 0.3, 1), light_enabled=True)
		self.sun_light = DirectionalLight(self.engine, 'sun', color=(1, 1, 1, 1), direction=(-1, 1, -1), position=(0, 0, 10), light_enabled=True)

		# Player
		self.player = Player(self.engine, self.engine.physics, position=(2.5, -1, 1), rotation=(0,90), near_clip=0.01)
		self.engine.renderer.set_camera(self.player.camera)

		# Camera
		self.first_person_camera = FirstPersonCamera(
			self.engine,
			position=(0, 0, 1.6),
			rotation=(0, 55, 0),
			speed=2,
			fast_speed=15,
			near_clip=0.01
		)
		#self.engine.renderer.set_camera(self.first_person_camera)

		# Floor
		self.floor = MeshObject(self.engine, 'floor', 'entities/floor.gltf',position=[0, 0, 0], rotation=[0, 0, 0], scale=0.2,collision_enabled=True)
		#self.engine.utils.add_mesh_collider(self.floor, self.engine.physics)

		# Entities
		locker_start = 2.5
		locker_offset = 0.05
		locker_width = 1.0 + locker_offset
		for i in range(3):
			self.lockers.append(MeshObject(
				self.engine,
				'locker',
				'entities/locker_000.gltf',
				position=[0, locker_start - (locker_width * i), 0],
				rotation=[0, 0, 0],
				scale=0.2,
				collision_enabled=True
			))

	def handle_input(self, input_handler):
		super().handle_input(input_handler)

		# Reset player position
		if input_handler.is_key_down('f5'):
			self.player.reset()

		# Player
		self.player.handle_input(input_handler)

		# Let camera handle input
		#self.first_person_camera.handle_input(input_handler)

	def update(self, dt):
		super().update(dt)

		# Skybox
		self.skybox.update(dt)

		# Physics
		self.engine.physics.doPhysics(dt)

		# Player
		self.player.update(dt)

		# Update camera
		#self.first_person_camera.update(dt)

		# Lighting
		self.ambient_light.update()
		self.sun_light.update()

	def on_exit(self):
		super().on_exit()

		# Skybox
		self.skybox.destroy()

		# Lighting
		self.ambient_light.destroy()
		self.sun_light.destroy()

		# Floor
		self.floor.destroy()

		# Player
		self.player.destroy()

		# Locker
		for locker in self.lockers:
			locker.destroy()
		self.lockers.clear()