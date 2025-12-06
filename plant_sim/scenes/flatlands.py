from engine.skybox import Skybox
from engine.scene import Scene
from engine.mesh_object import MeshObject
from plant_sim.first_person_camera import FirstPersonCamera


class FlatlandsScene(Scene):
	def __init__(self, engine):
		super().__init__(engine, 'flatlands')
		self.skybox = None
		self.first_person_camera = None
		self.tiny_living = None

	def on_enter(self):
		super().on_enter()
		self.skybox = Skybox(self.engine, faces={
			'right': ('assets/skydomes/sky_16_2k/sky_16_cubemap_2k/nx.png', 0, True),
			'left': ('assets/skydomes/sky_16_2k/sky_16_cubemap_2k/px.png', 0, True),
			'top': ('assets/skydomes/sky_16_2k/sky_16_cubemap_2k/py.png', 0, True),
			'bottom': ('assets/skydomes/sky_16_2k/sky_16_cubemap_2k/ny.png', 0, False),
			'front': ('assets/skydomes/sky_16_2k/sky_16_cubemap_2k/nz.png', 0, False),
			'back': ('assets/skydomes/sky_16_2k/sky_16_cubemap_2k/pz.png', 0, False),
		})

		# Load glTF model
		self.tiny_living = MeshObject(self.engine, 'tiny_living', 'assets/models/tinylivingpack/scene.gltf')
		self.tiny_living.position = [0, 0, 0]
		self.tiny_living.rotation = [90, 0, 0]

		# Create default camera looking at model
		# Panda3D: X=right, Y=forward, Z=up
		self.first_person_camera = FirstPersonCamera(
			self.engine,
			position=(0, -5.41, 1.5),
			rotation=(-14, 21, 0),
			speed=2,
			fast_speed=15,
			near_clip=0.01
		)
		self.engine.renderer.set_camera(self.first_person_camera)

	def handle_input(self, input_handler):
		super().handle_input(input_handler)

		# Let camera handle input
		if self.first_person_camera:
			self.first_person_camera.handle_input(input_handler)

	def update(self, dt):
		super().update(dt)

		# Update camera
		if self.first_person_camera:
			self.first_person_camera.update(dt)

		if self.skybox:
			self.skybox.update(dt)

	def on_exit(self):
		super().on_exit()
		if self.skybox:
			self.skybox.destroy()
		if self.tiny_living:
			self.tiny_living.destroy()