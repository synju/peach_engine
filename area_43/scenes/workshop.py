from area_43.creature_handler import CreatureHandler
from area_43.entities.entity_creatures.face_spider import FaceSpider
from area_43.entities.entity_creatures.spike_monster import SpikeMonster
from area_43.free_flying_camera import FreeFlyingCamera
from engine.effects.fog_distance import DistanceFog
from engine.effects.fog_linear import LinearFog


from engine.effects.scanlines import Scanlines
from engine.effects.shadow_mask import ShadowMask
from engine.light import AmbientLight, DirectionalLight, PointLight
from engine.mesh_object import MeshObject
from engine.scene import Scene
from engine.skybox import Skybox

from engine.effects.post_processing_stack import PostProcessingStack
from engine.effects.crt_lottes import CRTLottes
from engine.effects.crt_newpixie import CRTNewPixie
from engine.effects.dithering import Dithering
from engine.effects.film_grain import FilmGrain
from engine.effects.hbao import HBAO
from engine.effects.vhs_effect import VHSEffect
from engine.effects.vignette import Vignette

from area_43.player import Player
from area_43.entities.entity_objects.interactive_cube import InteractiveCube

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
		self.bulb = None

		# Physics
		self.physics = None

		# Interactive Objects
		self.interactive_objects = None

		# Player
		self.player = None

		# Free Flying Camera
		self.free_cam = None

		# Interactive Cube
		self.cube = None

		# Fog
		self.fog = None

		# Post-Processing Stack
		self.pp_stack = None

		# Level
		self.level = None

		# Creatures
		self.creatures = None
		self.monster = None

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
		self.setup_lights()

		# Ambient sound
		#self.engine.sound_player.play('wind', 'assets/sounds/wind_000.mp3', loop=True, volume=0.2)

		# Player
		self.player = Player(self.engine, self.engine.physics, position=(5.11, -2.12, 0.7), rotation=(0, 35), near_clip=0.01, debug_mode=False)
		self.engine.renderer.set_camera(self.player.camera)

		# Create free camera
		self.free_cam = FreeFlyingCamera(self.engine, position=(0, -5, 3))
		self.use_free_cam = False

		# Interactive Objects
		self.interactive_objects = []
		self.cube = InteractiveCube(self.engine, position=[1, -0.75, 0.5], rotation=[0, 0, 0], scale=0.2, collision_enabled=True, debug_mode=False)
		self.cube.set_interact(self.some_function)

		# Setup Post Processing Stack
		self.pp_stack = PostProcessingStack(self.engine)
		self.setup_effects()

		# Level
		self.level = MeshObject(self.engine, 'engine', 'entities/models/misc.gltf', position=[0, 0, 0], rotation=[0, 0, 0], scale=0.2, collision_enabled=True)

		# Creatures
		self.creatures = CreatureHandler()
		self.setup_creatures()

		# Set target for all at once
		self.creatures.set_target_all(self.player)

	def setup_lights(self):
		self.ambient_light = AmbientLight(self.engine, 'ambient', color=(0.3, 0.3, 0.3, 1), light_enabled=True)
		self.sun_light = DirectionalLight(self.engine, 'sun', color=(1, 1, 1, 1), direction=(-1, 1, -1), position=(0, 0, 10), light_enabled=True)
		self.bulb = PointLight(self.engine, 'sun', color=(1, 1, 1, 1), position=(5, -3, 3), light_enabled=False)

	def setup_effects(self):
		# Fog Volume (Quake 3 Arena)
		# self.fog = FogVolume(self.engine, position=(4.4, -2.9, 1.9), size=(9.5, 7.5, 3.6), color=(1, 1, 1), density=0.1, debug_mode=False)

		# Fog Distance (Silent Hill)
		#	self.fog = DistanceFog(self.engine, color=(1.0, 1.0, 1.0), density=0.1)

		# Ranged Distance Fog
		# self.fog = LinearDistanceFog(self.engine, color=(1.0, 1.0, 1.0), start=0, end=10, density=0.5)
		# self.fog = LinearDistanceFog(self.engine, color=(0, 0, 0), start=0, end=5, density=1.25)
		# self.fog = LinearDistanceFog(self.engine, color=(1.0, 0, 0), start=1, end=15, density=2.0)

		# HBAO - Ambient Occlusion (order 40)
		hbao = self.pp_stack.add_effect(HBAO(
			radius=0.3,
			intensity=1.0,
			samples=16,
			debug=False
		))
		hbao.enabled = False

		# Add fogs (so post effects apply on top)

		# # Option 1: Linear fog (start/end range)
		# self.pp_stack.add_effect(LinearFog(
		# 	color=(1.0, 1.0, 1.0),
		# 	start=0,
		# 	end=10,
		# 	density=1.0
		# ))

		# Option 2: Distance fog (exponential, Silent Hill style)
		# self.pp_stack.add_effect(DistanceFog(
		# 	color=(1.0, 1.0, 1.0),
		# 	density=0.2
		# ))

		# Option 3: Multiple volume fogs
		# self.pp_stack.add_effect(VolumeFog(
		#     position=[4.4, -2.9, 1.9],
		#     size=[9.5, 7.5, 3.6],
		#     color=(1, 1, 1),
		#     density=0.1
		# ))
		# self.pp_stack.add_effect(VolumeFog(
		#     position=[10, 0, 2],
		#     size=[5, 5, 5],
		#     color=(1, 0, 0),
		#     density=0.2
		# ))

		# Dithering
		dither = self.pp_stack.add_effect(Dithering(
			color_levels=1.0,
			strength=0.01,
			opacity=0.5,
			gamma=1.0,
			contrast=1.0,
			debug=False
		))
		dither.enabled = False

		# VHS
		vhs = self.pp_stack.add_effect(VHSEffect(
			scroll_speed=0.05,
			opacity=0.1,
			scale_x=0.1,
			scale_y=0.01,
			debug=False
		))
		vhs.enabled = False

		# Film Grain
		grain = self.pp_stack.add_effect(FilmGrain(
			intensity=0.1,
			size=1.0,
			speed=1,
			debug=False
		))
		grain.enabled = False

		# Vignette
		vignette = self.pp_stack.add_effect(Vignette(
			intensity=0.5,
			radius=0.8,
			softness=0.5,
			debug=False
		))
		vignette.enabled = False

		# Horizontal Scanlines
		horizontal_scanlines = self.pp_stack.add_effect(Scanlines(
			line_count=125.0,  # Number of lines
			thickness=0.5,  # 0-1, how thick the dark lines are
			opacity=0.05,  # 0-1, how dark
			scroll_speed=-3,  # 0=static, positive=down, negative=up
			softness=0.1,  # Edge blur (0.1-0.5), higher = smoother, less flicker
			direction=0,  # 0=horizontal, 1=vertical
		))
		horizontal_scanlines.enabled = False

		# Vertical Scanlines
		vertical_scanlines = self.pp_stack.add_effect(Scanlines(
			line_count=400.0,  # Number of lines
			thickness=0.3,  # 0-1, how thick the dark lines are
			opacity=0.025,  # 0-1, how dark
			scroll_speed=0,  # 0=static, positive=down, negative=up
			softness=0.1,  # Edge blur (0.1-0.5), higher = smoother, less flicker
			direction=1,  # 0=horizontal, 1=vertical
		))
		vertical_scanlines.enabled = False

		# Shadow Mask
		shadow = self.pp_stack.add_effect(ShadowMask(
			mask_type=0,  # Aperture grille (vertical RGB stripes)
			line_density=960.0,  # 640 RGB triplets across screen (like 640px wide CRT)
			intensity=0.5,  # Subtle
			dot_width=0.05,  # Thin phosphor lines (lower = thinner)
			brightness=1.6,  # Compensate for darkening
		))
		shadow.enabled = False

		# CRT-NewPixie: blur, phosphor
		newpixie = self.pp_stack.add_effect(CRTNewPixie(
			accumulate=1.0,
			blur_x=0.0,
			blur_y=0.0,
			curvature=4.2,
			interference=0.0,
			rolling_scanlines=0.2,
			brightness=1.0,
		))
		newpixie.enabled = False

		# CRT-Lottes: masks, scanlines
		lottes = self.pp_stack.add_effect(CRTLottes(
			mask_type=1,
			mask_strength=0.0,
			scanline_strength=0.0,
			scanline_count=480.0,
			scanline_hardness=1.0,
			bloom_amount=0.0,
			bloom_radius=0.0,
			curvature=4.0,
			corner_radius=0.05,
			brightness=1.0,
			saturation=1.0,
			vignette=0.0,
		))
		lottes.enabled = False

	def setup_creatures(self):
		self.creatures.add(SpikeMonster(self.engine, position=[3, 0, 0], scale=0.2, debug_mode=False))  # id 0
		self.creatures.add(FaceSpider(self.engine, position=[5, -3, 0], scale=0.1, debug_mode=False))  # id 1

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

		# Toggle free camera
		if input_handler.is_key_down('n'):
			self.use_free_cam = not self.use_free_cam
			if self.use_free_cam:
				# Start free cam near player
				self.free_cam.position = [
					self.player._position[0] - 3,
					self.player._position[1] - 3,
					self.player._position[2] + 2
				]
			self.engine.scene_handler.console.print(f"Free cam: {'ON' if self.use_free_cam else 'OFF'}")

		# Input to active controller
		if self.use_free_cam:
			self.free_cam.handle_input(input_handler)
		else:
			self.player.handle_input(input_handler)

	def update(self, dt):
		super().update(dt)

		# Skybox
		self.skybox.update(dt)

		# Physics
		self.engine.physics.doPhysics(dt)

		# Player - Skip player update if console is open
		if not self.engine.scene_handler.console.is_open:
			if self.use_free_cam:
				self.free_cam.update(dt)
				self.player._update_debug_hitbox()  # Keep hitbox visible
			else:
				self.player.update(dt)

		# Interactive objects
		for obj in self.interactive_objects:
			obj.update(dt)

		# Fog
		if self.fog:
			self.fog.update()

		# Post-Processing Stack
		if self.pp_stack:
			self.pp_stack.process(dt)

		# Lighting
		self.ambient_light.update()
		self.sun_light.update()

		# Monsters
		self.creatures.update(dt)

	def on_exit(self):
		super().on_exit()

		# Skybox
		self.skybox.destroy()

		# Lighting
		self.ambient_light.destroy()
		self.sun_light.destroy()

		# Sounds
		# self.engine.sound_player.stop_sound('wind')
		self.engine.sound_player.stop_all_sounds()

		# Interactive Cube
		self.cube.destroy()

		# Fog
		if self.fog:
			self.fog.destroy()

		# Post-Processing Stack
		if self.pp_stack:
			self.pp_stack.destroy()

		# Player
		self.player.destroy()

		# Free cam
		if self.free_cam:
			self.free_cam.destroy()

		# Level
		self.level.destroy()

		# Monsters
		self.creatures.destroy()