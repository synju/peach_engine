from .scene import Scene
from .first_person_camera import FirstPersonCamera
from .cube import Cube
from .light import AmbientLight, DirectionalLight

class DefaultScene(Scene):
	"""Default scene with a first-person camera"""

	def __init__(self, engine, name='default'):
		super().__init__(engine, name)
		self.first_person_camera = None
		self.cube = None
		self.ambient_light = None
		self.sun_light = None

	def on_enter(self):
		super().on_enter()

		# Create default camera looking at grid center
		# Panda3D: X=right, Y=forward, Z=up
		self.first_person_camera = FirstPersonCamera(
			self.engine,
			position=(15, 15, 15),
			rotation=(-45, 135, 0)
		)
		self.engine.renderer.set_camera(self.first_person_camera)

		# Setup lighting
		self.ambient_light = AmbientLight(self.engine, 'ambient', color=(0.3, 0.3, 0.3, 1))
		self.sun_light = DirectionalLight(self.engine, 'sun', color=(1, 1, 0.9, 1), direction=(-1, -1, -1), position=(5, 5, 10))

		# Create a demo cube
		self.cube = Cube(self.engine, 'demo_cube', size=2, color=(0.2, 0.6, 1.0, 1))
		self.cube.position = [0, 0, 1]

	def on_exit(self):
		super().on_exit()
		if self.cube:
			self.cube.destroy()
		if self.ambient_light:
			self.ambient_light.destroy()
		if self.sun_light:
			self.sun_light.destroy()

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

		# Update lights (checks debug mode)
		if self.ambient_light:
			self.ambient_light.update()
		if self.sun_light:
			self.sun_light.update()

		# Rotate the cube
		if self.cube:
			self.cube.rotation = [
				self.cube.rotation[0],
				self.cube.rotation[1] + 30 * dt,
				self.cube.rotation[2]
			]

	def render(self, renderer):
		super().render(renderer)

		# Render cube
		if self.cube:
			self.cube.render(renderer)