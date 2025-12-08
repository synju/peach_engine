from engine.skybox import Skybox
from engine.scene import Scene
from engine.mesh_object import MeshObject
from pod_hotel.first_person_camera import FirstPersonCamera
from engine.light import AmbientLight, DirectionalLight

class WorkshopScene(Scene):
	def __init__(self, engine):
		super().__init__(engine, 'workshop')

		# Skybox
		self.skybox = None

		# Lighting
		self.ambient_light = None
		self.sun_light = None

		# Camera
		self.first_person_camera = None

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

		# Camera
		self.first_person_camera = FirstPersonCamera(
			self.engine,
			position=(0, 0, 1.6),
			rotation=(0, 55, 0),
			speed=2,
			fast_speed=15,
			near_clip=0.01
		)
		self.engine.renderer.set_camera(self.first_person_camera)

		# Entities
		locker_start = 5
		locker_offset = 0.05
		locker_width = 1.0+ locker_offset
		self.lockers.append(MeshObject(self.engine, 'locker', 'entities/locker_000.gltf', position=[-5, locker_start, 0], rotation=[0, 0, 0], scale=0.2))
		self.lockers.append(MeshObject(self.engine, 'locker', 'entities/locker_000.gltf', position=[-5, locker_start - (locker_width * 1), 0], rotation=[0, 0, 0], scale=0.2))
		self.lockers.append(MeshObject(self.engine, 'locker', 'entities/locker_000.gltf', position=[-5, locker_start - (locker_width * 2), 0], rotation=[0, 0, 0], scale=0.2))

	def handle_input(self, input_handler):
		super().handle_input(input_handler)

		# Let camera handle input
		if self.first_person_camera:
			self.first_person_camera.handle_input(input_handler)

	def update(self, dt):
		super().update(dt)

		# Skybox
		self.skybox.update(dt)

		# Update camera
		self.first_person_camera.update(dt)

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

		# Locker
		for locker in self.lockers:
			locker.destroy()
		self.lockers.clear()