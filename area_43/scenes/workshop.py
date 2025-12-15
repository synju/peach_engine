from area_43.entities.entity_creatures.spike_monster import SpikeMonster
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

		# Interactive Cube
		self.cube = None

		# Fog
		self.fog = None

		# Post-Processing Stack
		self.pp_stack = None

		# Level
		self.level = None

		# Monsters
		self.monster = None

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
		self.sun_light = DirectionalLight(self.engine, 'sun', color=(1, 1, 1, 1), direction=(-1, 1, -1), position=(0, 0, 10), light_enabled=True)
		self.bulb = PointLight(self.engine, 'sun', color=(1, 1, 1, 1), position=(5, -3, 3), light_enabled=False)

		# Player
		self.player = Player(self.engine, self.engine.physics, position=(5.11, -2.12, 0.7), rotation=(0, 35), near_clip=0.01)
		self.engine.renderer.set_camera(self.player.camera)

		# Interactive Cube
		self.cube = InteractiveCube(self.engine, position=[1, -0.75, 0.5], rotation=[0, 0, 0], scale=0.2, collision_enabled=True, debug_mode=False)
		self.cube.set_interact(self.some_function)

		# Fog Volume (Quake 3 Arena)
		# self.fog = FogVolume(self.engine, position=(4.4, -2.9, 1.9), size=(9.5, 7.5, 3.6), color=(1, 1, 1), density=0.1, debug_mode=False)

		# Fog Distance (Silent Hill)
		#	self.fog = DistanceFog(self.engine, color=(1.0, 1.0, 1.0), density=0.1)

		# Ranged Distance Fog
		# self.fog = LinearDistanceFog(self.engine, color=(1.0, 1.0, 1.0), start=0, end=10, density=0.5)
		# self.fog = LinearDistanceFog(self.engine, color=(0, 0, 0), start=0, end=5, density=1.25)
		# self.fog = LinearDistanceFog(self.engine, color=(1.0, 0, 0), start=1, end=15, density=2.0)

		# =============================================
		# Post-Processing Stack (all effects unified)
		# =============================================
		self.pp_stack = PostProcessingStack(self.engine)

		# HBAO - Ambient Occlusion (order 40)
		hbao = self.pp_stack.add_effect(HBAO(
			radius=0.3,
			intensity=1.0,
			samples=16,
			debug=False
		))
		hbao.enabled = True

		# Add fogs (so post effects apply on top)

		# # Option 1: Linear fog (start/end range)
		# self.pp_stack.add_effect(LinearFog(
		# 	color=(1.0, 1.0, 1.0),
		# 	start=0,
		# 	end=10,
		# 	density=10.0
		# ))

		# Option 2: Distance fog (exponential, Silent Hill style)
		self.pp_stack.add_effect(DistanceFog(
			color=(1.0, 1.0, 1.0),
			density=0.1
		))

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
		grain.enabled = True

		# Vignette
		vignette = self.pp_stack.add_effect(Vignette(
			intensity=0.5,
			radius=0.8,
			softness=0.5,
			debug=False
		))
		vignette.enabled = False

		horizontal_scanlines = self.pp_stack.add_effect(Scanlines(
			line_count=125.0,  # Number of lines
			thickness=0.5,  # 0-1, how thick the dark lines are
			opacity=0.05,  # 0-1, how dark
			scroll_speed=-3,  # 0=static, positive=down, negative=up
			softness=0.1,  # Edge blur (0.1-0.5), higher = smoother, less flicker
			direction=0,  # 0=horizontal, 1=vertical
		))
		horizontal_scanlines.enabled = True

		vertical_scanlines = self.pp_stack.add_effect(Scanlines(
			line_count=400.0,  # Number of lines
			thickness=0.3,  # 0-1, how thick the dark lines are
			opacity=0.025,  # 0-1, how dark
			scroll_speed=0,  # 0=static, positive=down, negative=up
			softness=0.1,  # Edge blur (0.1-0.5), higher = smoother, less flicker
			direction=1,  # 0=horizontal, 1=vertical
		))
		vertical_scanlines.enabled = True

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
		lottes.enabled = True

		# Level
		self.level = MeshObject(self.engine, 'engine', 'entities/models/misc.gltf', position=[0, 0, 0], rotation=[0, 0, 0], scale=0.2, collision_enabled=True)

		# Monsters
		self.monster = SpikeMonster(
			self.engine,
			position=[3, 0, 0],
			rotation=[0, 0, 0],
			scale=0.2
		)
		self.monster.set_target(self.player)

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

		# Player - Skip player update if console is open
		if not self.engine.scene_handler.console.is_open:
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
		self.monster.update(dt)

	def on_exit(self):
		super().on_exit()

		# Skybox
		self.skybox.destroy()

		# Lighting
		self.ambient_light.destroy()
		self.sun_light.destroy()

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

		# Level
		self.level.destroy()

		# Monsters
		self.monster.destroy()
