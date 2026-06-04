from area_43.maze_level.maze import Maze
from area_43.player import Player
from area_43.free_flying_camera import FreeFlyingCamera
from area_43.third_person_player import ThirdPersonPlayer
from engine.light import AmbientLight, DirectionalLight
from engine.scene import Scene
from engine.skybox import Skybox

class MazeScene(Scene):
	def __init__(self, engine):
		super().__init__(engine, 'maze')

		# Disable Grid
		self.engine.scene_handler.grid.hide()

		# Skybox
		self.skybox = None

		# Lighting
		self.ambient_light = None
		self.sun_light = None

		# Player (first person)
		self.player = None

		# Third Person Player
		self.third_person_player = None
		self.use_third_person = False  # Start in third person

		# Free Flying Camera
		self.free_cam = None
		self.use_free_cam = False

		# Level
		self.maze = None

	def on_enter(self):
		super().on_enter()

		# Skybox
		self.setup_skybox()

		# Lighting
		self.setup_lights()

		# Sound
		# self.setup_sound()

		# Players
		self.setup_players()

		# Cameras
		self.setup_cameras()

		# Level
		self.setup_level()

	def setup_skybox(self):
		self.skybox = Skybox(self.engine, faces={
			'right': ('assets/skydomes/sky_16_2k/sky_16_cubemap_2k/nx.png', 0, True),
			'left': ('assets/skydomes/sky_16_2k/sky_16_cubemap_2k/px.png', 0, True),
			'top': ('assets/skydomes/sky_16_2k/sky_16_cubemap_2k/py.png', 0, True),
			'bottom': ('assets/skydomes/sky_16_2k/sky_16_cubemap_2k/ny.png', 0, False),
			'front': ('assets/skydomes/sky_16_2k/sky_16_cubemap_2k/nz.png', 0, False),
			'back': ('assets/skydomes/sky_16_2k/sky_16_cubemap_2k/pz.png', 0, False),
		})

	def setup_lights(self):
		self.ambient_light = AmbientLight(self.engine, 'ambient', color=(0.3, 0.3, 0.3), light_enabled=True)
		self.sun_light = DirectionalLight(self.engine, 'sun', color=(1, 1, 1), direction=(-1, 1, -1), position=(0, 0, 10), light_enabled=True)

	def setup_sound(self):
		# Ambient sound
		self.engine.sound_player.play('wind', 'assets/sounds/wind_000.mp3', loop=True, volume=0.2)
		pass

	def setup_players(self):
		# First Person Player
		self.player = Player(
			self.engine,
			self.engine.physics,
			position=(2, 2, 3.0),
			rotation=(0, 0),
			near_clip=0.01,
			debug_mode=False
		)
		self.engine.renderer.set_camera(self.player.camera)
		self.engine.input_handler.set_mouse_locked(True)
		self.player.looking = True

		# Third Person Player (different spawn location)
		self.third_person_player = ThirdPersonPlayer(
			self.engine,
			self.engine.physics,
			position=(0, 0, 1.0),
			rotation=(0, 0),
			near_clip=0.01,
			debug_mode=True
		)

	def setup_cameras(self):
		# Set initial camera based on mode
		if self.use_third_person:
			self.engine.renderer.set_camera(self.third_person_player.camera)
		else:
			self.engine.renderer.set_camera(self.player.camera)

		# Create free camera
		self.free_cam = FreeFlyingCamera(self.engine, position=(0, -5, 3))

	def setup_level(self):
		self.maze = Maze(self.engine, size=15, wall_height=3, wall_thickness=1, seed=42)
		self.maze.spawn(offset_x=0, offset_y=0)

	def switch_to_first_person(self):
		"""Switch to first person player"""
		self.use_third_person = False
		self.engine.renderer.set_camera(self.player.camera)
		self.engine.input_handler.set_mouse_locked(True)
		self.player.looking = True
		self.engine.scene_handler.console.print("Switched to First Person")

	def switch_to_third_person(self):
		"""Switch to third person player"""
		self.use_third_person = True
		self.engine.renderer.set_camera(self.third_person_player.camera)
		self.engine.input_handler.set_mouse_locked(True)
		self.third_person_player.looking = True
		self.engine.scene_handler.console.print("Switched to Third Person")

	def handle_input(self, input_handler):
		super().handle_input(input_handler)

		# Skip all input if console is open
		if self.engine.scene_handler.console.is_open:
			return

		# Toggle between first and third person (F4)
		if input_handler.is_key_down('f4'):
			if self.use_third_person:
				self.switch_to_first_person()
			else:
				self.switch_to_third_person()
			return

		# Reset current player position
		if input_handler.is_key_down('f5'):
			if self.use_third_person:
				self.third_person_player.reset()
			else:
				self.player.reset()

		# Toggle Free Camera (Noclip)
		if input_handler.is_key_down('n'):
			# Flip use_free_cam
			self.use_free_cam = not self.use_free_cam

			# Noclip ON
			if self.use_free_cam:
				# Position
				if self.use_third_person:
					self.free_cam.position = self.third_person_player.position
				else:
					self.free_cam.position = self.player._position

				# Heading
				self.free_cam.heading = self.player.heading

				# Pitch
				self.free_cam.pitch = self.player.pitch

			# Noclip OFF
			if not self.use_free_cam:
				# Position
				if self.use_third_person:
					self.third_person_player.position= self.free_cam.position
				else:
					self.player._position = self.free_cam.position

				# Heading
				self.player.heading = self.free_cam.heading

				# Pitch
				self.player.pitch = self.free_cam.pitch

			# Console logging
			self.engine.scene_handler.console.print(f"Free cam: {'ON' if self.use_free_cam else 'OFF'}")

		# Send Input to active controller
		if self.use_free_cam:
			self.free_cam.handle_input(input_handler)
		elif self.use_third_person:
			self.third_person_player.handle_input(input_handler)
		else:
			self.player.handle_input(input_handler)

	def update(self, dt):
		super().update(dt)
		# Physics
		self.engine.physics.doPhysics(dt)

		# Player updates - Skip if console is open
		if not self.engine.scene_handler.console.is_open:
			if self.use_free_cam:
				self.free_cam.update(dt)
				# Keep active player's hitbox visible
				if self.use_third_person:
					self.third_person_player.update_debug_hitbox()
				else:
					self.player.update_debug_hitbox()
			elif self.use_third_person:
				self.third_person_player.update(dt)
			else:
				self.player.update(dt)

	def on_exit(self):
		super().on_exit()
		if self.ambient_light:
			self.ambient_light.destroy()
		if self.sun_light:
			self.sun_light.destroy()
		if self.skybox:
			self.skybox.destroy()
		if self.maze:
			self.maze.destroy()
		if self.player:
			self.player.destroy()
		if self.free_cam:
			self.free_cam.destroy()