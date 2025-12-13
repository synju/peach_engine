from area_43.entities.entity_objects.interactive_cube import InteractiveCube
from area_43.player import Player
from engine.fog_linear import LinearDistanceFog
from engine.light import AmbientLight, DirectionalLight
from engine.mesh_object import MeshObject
from engine.scene import Scene
from engine.skybox import Skybox
from engine.fog_distance import DistanceFog
from engine.fog_volume import FogVolume

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

		# Interactive Objects
		self.interactive_objects = None

		# Player
		self.player = None

		# Interactive Cube
		self.cube = None

		# Fog
		self.fog = None
		self.fog_mode = None
		self.fog_distance = None
		self.fog_linear = None

		# Level
		self.level = None

	def on_enter(self):
		super().on_enter()

		# Interactive Objects
		self.interactive_objects = []

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
		#self.ambient_light = AmbientLight(self.engine, 'ambient', color=(0.3, 0.3, 0.3, 1), light_enabled=True)
		#self.sun_light = DirectionalLight(self.engine, 'sun', color=(1, 1, 1, 1), direction=(-1, 1, -1), position=(0, 0, 10), light_enabled=True)

		# Player
		self.player = Player(self.engine, self.engine.physics, position=(5.11, -2.12, 0.7), rotation=(-3, 124), near_clip=0.01)
		self.engine.renderer.set_camera(self.player.camera)

		# Interactive Cube
		self.cube = InteractiveCube(self.engine, position=[1, -0.75, 0.5], rotation=[0, 0, 0], scale=0.2, collision_enabled=True,debug_mode=False)
		self.cube.set_interact(self.some_function)

		# Fog Volume (Quake 3 Arena)
		#self.fog = FogVolume(self.engine, position=(4.4, -2.9, 1.9), size=(9.5, 7.5, 3.6), color=(1, 1, 1), density=0.1, debug_mode=False)

		# Fog Distance (Silent Hill)
		#self.fog = DistanceFog(self.engine, color=(1.0, 1.0, 1.0), density=0.1)

		# Ranged Distance Fog
		#self.fog = LinearDistanceFog(self.engine, color=(1.0, 1.0, 1.0), start=0, end=10, density=2.0)
		#self.fog = LinearDistanceFog(self.engine, color=(0, 0, 0), start=0, end=5, density=1.25)
		#self.fog = LinearDistanceFog(self.engine, color=(1.0, 0, 0), start=1, end=15, density=2.0)

		# Entities
		self.level = MeshObject(
			self.engine,
			'engine',
			'entities/models/misc.gltf',
			position=[0, 0, 0],
			rotation=[0, 0, 0],
			scale=0.2,
			collision_enabled=True
		)

	def some_function(self):
		print("interacted")

	def handle_input(self, input_handler):
		super().handle_input(input_handler)

		# Skip all input if console is open
		if self.engine.scene_handler.console.is_open:
			return

		# Reset player position
		if input_handler.is_key_down('f5'):
			self.player.reset()

		# Player
		self.player.handle_input(input_handler)

	def update(self, dt):
		super().update(dt)

		# Skybox
		self.skybox.update(dt)

		# Physics
		self.engine.physics.doPhysics(dt)

		# Player
		# Skip player update if console is open
		if not self.engine.scene_handler.console.is_open:
			self.player.update(dt)

		# Interactive objects
		for obj in self.interactive_objects:
			obj.update(dt)

		# Fog
		#self.fog.update()

		# Lighting
		self.ambient_light.update()
		#self.sun_light.update()

	def on_exit(self):
		super().on_exit()

		# Skybox
		self.skybox.destroy()

		# Lighting
		self.ambient_light.destroy()
		#self.sun_light.destroy()

		# Interactive Cube
		self.cube.destroy()

		# Fog
		#self.fog.destroy()

		# Player
		self.player.destroy()

		# Level
		self.level.destroy()
