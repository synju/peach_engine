from direct.showbase.ShowBase import ShowBase
from panda3d.core import WindowProperties
from area_43.free_flying_camera import FreeFlyingCamera
from area_43.tak_level.board_block import BoardBlock
from area_43.tak_level.flat import Flat
from area_43.tak_level.table import Table
from engine.light import AmbientLight, DirectionalLight
from engine.scene import Scene
from engine.skybox import Skybox

base: ShowBase


class TakScene(Scene):
    def __init__(self, engine):
        super().__init__(engine, "tak_scene")

        # Disable Grid
        self.engine.scene_handler.grid.hide()

        # Skybox
        self.skybox = None

        # Lighting
        self.ambient_light = None
        self.sun_light = None

        # Free Flying Camera
        self.free_cam = None
        self.use_free_cam = False

        # Level
        self.board_blocks = []
        self.flats = []
        self.table = None

        # Mouse Boolean
        self.right_mouse_down = False

    def on_enter(self):
        super().on_enter()

        # Skybox
        self.setup_skybox()

        # Lighting
        self.setup_lights()

        # Sound
        # self.setup_sound()

        # Cameras
        self.setup_cameras()

        # Level
        self.setup_level()

    def setup_skybox(self):
        self.skybox = Skybox(
            self.engine,
            faces={
                "right": (
                    "assets/skydomes/sky_16_2k/sky_16_cubemap_2k/nx.png",
                    0,
                    True,
                ),
                "left": ("assets/skydomes/sky_16_2k/sky_16_cubemap_2k/px.png", 0, True),
                "top": ("assets/skydomes/sky_16_2k/sky_16_cubemap_2k/py.png", 0, True),
                "bottom": (
                    "assets/skydomes/sky_16_2k/sky_16_cubemap_2k/ny.png",
                    0,
                    False,
                ),
                "front": (
                    "assets/skydomes/sky_16_2k/sky_16_cubemap_2k/nz.png",
                    0,
                    False,
                ),
                "back": (
                    "assets/skydomes/sky_16_2k/sky_16_cubemap_2k/pz.png",
                    0,
                    False,
                ),
            },
        )

    def setup_lights(self):
        self.ambient_light = AmbientLight(
            self.engine, "ambient", color=(0.3, 0.3, 0.3), light_enabled=True
        )
        self.sun_light = DirectionalLight(
            self.engine,
            "sun",
            color=(1, 1, 1),
            direction=(-1, 1, -1),
            position=(0, 0, 10),
            light_enabled=True,
        )

    def setup_sound(self):
        # Ambient sound
        self.engine.sound_player.play(
            "wind", "assets/sounds/wind_000.mp3", loop=True, volume=0.2
        )

    def setup_cameras(self):
        # Setup free camera
        self.free_cam = FreeFlyingCamera(
            self.engine, position=(-4, -7, 4), rotation=(-20.76, -31.88)
        )
        self.engine.renderer.set_camera(self.free_cam)
        self.engine.input_handler.set_mouse_locked(locked=False)

    def setup_level(self):
        # Create 5x5 checkerboard
        for y in range(5):
            for x in range(5):
                color = BoardBlock.BLACK if (x + y) % 2 == 0 else BoardBlock.WHITE
                block = BoardBlock(self.engine, color, x=x * 2, y=y * 2, z=-0.125)
                self.board_blocks.append(block)

        # Create a stack of 4 flats on top of first board block
        z = 0.25
        colors = [Flat.BLACK, Flat.WHITE, Flat.BLACK, Flat.WHITE]
        for color in colors:
            flat = Flat(self.engine, color, x=0, y=0, z=z)
            self.flats.append(flat)
            z += 0.5

        # Create table beneath the board
        self.table = Table(self.engine, x=4, y=4, z=-0.75)

    def handle_input(self, input_handler):
        super().handle_input(input_handler)

        # Skip all input if console is open
        if self.engine.scene_handler.console.is_open:
            return

        # IF mouse 3 then
        if input_handler.is_mouse_pressed(3):
            if not self.right_mouse_down:
                self.right_mouse_down = True
                self.engine.input_handler.set_mouse_locked(locked=True)
        # ELSE
        else:
            self.engine.input_handler.set_mouse_locked(locked=False)

        # Send input to free cam
        self.free_cam.handle_input(input_handler)



    def update(self, dt):
        super().update(dt)

        # Physics
        self.engine.physics.doPhysics(dt)

        # Free Cam updates - Skip if console is open
        if not self.engine.scene_handler.console.is_open:
            self.free_cam.update(dt)

        # print xyz location of free camera here
        # print(
        #     f"FreeCam: X={self.free_cam.position[0]:.2f}, Y={self.free_cam.position[1]:.2f}, Z={self.free_cam.position[2]:.2f}"
        # )

        # print orientation of free camera
        # print(
        #     f"FreeCam: Pitch={self.free_cam.pitch:.2f}, Heading={self.free_cam.heading:.2f}"
        # )

    def on_exit(self):
        super().on_exit()
        if self.ambient_light:
            self.ambient_light.destroy()
        if self.sun_light:
            self.sun_light.destroy()
        if self.skybox:
            self.skybox.destroy()
        for block in self.board_blocks:
            block.destroy()
        for flat in self.flats:
            flat.destroy()
        if self.table:
            self.table.destroy()
        if self.free_cam:
            self.free_cam.destroy()
