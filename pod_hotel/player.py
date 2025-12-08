import math
from direct.showbase.ShowBase import ShowBase
from panda3d.core import NodePath
from engine.camera import Camera

base: ShowBase


class PlayerCamera(Camera):
	"""Camera controlled by Player - no direct input"""

	def __init__(self, engine, near_clip=0.1, far_clip=10000):
		super().__init__(engine, (0, 0, 0), (0, 0, 0), near_clip, far_clip)

	def handle_input(self, input_handler):
		pass

	def update(self, dt):
		pass


class Player:
	"""First-person player controller with built-in camera"""

	def __init__(self, engine, position=(0, 0, 0), near_clip=0.1, far_clip=10000):
		self.engine = engine

		# Node for player
		self.node = NodePath('player')
		self.node.reparentTo(base.render)

		# Position & rotation
		self._position = list(position)
		self._heading = 0
		self._pitch = 0

		# Physical properties
		self.height = 1.8
		self.crouch_height = 1.0
		self.eye_offset = 0.1

		# Movement speeds (m/s)
		self.walk_speed = 2.0
		self.jog_speed = 4.0
		self.sprint_speed = 7.0
		self.crouch_speed = 1.5

		# State
		self.is_crouching = False
		self.is_sprinting = False
		self.is_moving = False

		# Mouse look
		self.sensitivity = 100
		self.looking = False

		# Built-in camera
		self.camera = PlayerCamera(engine, near_clip, far_clip)

		# Apply initial position
		self.position = position

	@property
	def position(self):
		return self._position

	@position.setter
	def position(self, value):
		self._position = list(value)
		self.node.setPos(*self._position)
		self._update_camera()

	@property
	def heading(self):
		return self._heading

	@heading.setter
	def heading(self, value):
		self._heading = value % 360
		self._update_camera()

	@property
	def pitch(self):
		return self._pitch

	@pitch.setter
	def pitch(self, value):
		self._pitch = max(-89, min(89, value))
		self._update_camera()

	@property
	def eye_height(self):
		h = self.crouch_height if self.is_crouching else self.height
		return h - self.eye_offset

	@property
	def current_speed(self):
		if self.is_crouching:
			return self.crouch_speed
		elif self.is_sprinting:
			return self.sprint_speed
		else:
			return self.jog_speed

	def _update_camera(self):
		self.camera.position = [
			self._position[0],
			self._position[1],
			self._position[2] + self.eye_height
		]
		self.camera.rotation = [self._pitch, self._heading, 0]
		self.camera._apply_transform()

	def handle_input(self, input_handler):
		if input_handler.is_mouse_pressed(3):
			if not self.looking:
				input_handler.set_mouse_locked(True)
				self.looking = True

			dx, dy = input_handler.mouse_delta
			self.heading -= dx * self.sensitivity
			self.pitch += dy * self.sensitivity
		else:
			if self.looking:
				input_handler.set_mouse_locked(False)
				self.looking = False

		self.is_crouching = input_handler.is_key_pressed('control')
		self.is_sprinting = (
			input_handler.is_key_pressed('shift') and
			not self.is_crouching and
			input_handler.is_key_pressed('w')
		)

	def update(self, dt):
		if not self.looking:
			self._update_camera()
			return

		input_handler = self.engine.input_handler

		move_x = 0
		move_y = 0

		if input_handler.is_key_pressed('w'):
			move_y += 1
		if input_handler.is_key_pressed('s'):
			move_y -= 1
		if input_handler.is_key_pressed('d'):
			move_x += 1
		if input_handler.is_key_pressed('a'):
			move_x -= 1

		self.is_moving = move_x != 0 or move_y != 0

		if self.is_moving:
			if move_x != 0 and move_y != 0:
				move_x *= 0.707
				move_y *= 0.707

			heading_rad = math.radians(self._heading)
			forward = [-math.sin(heading_rad), math.cos(heading_rad)]
			right = [math.cos(heading_rad), math.sin(heading_rad)]

			speed = self.current_speed * dt
			self._position[0] += (forward[0] * move_y + right[0] * move_x) * speed
			self._position[1] += (forward[1] * move_y + right[1] * move_x) * speed
			self.node.setPos(*self._position)

		self._update_camera()

	def destroy(self):
		if self.node:
			self.node.removeNode()
			self.node = None