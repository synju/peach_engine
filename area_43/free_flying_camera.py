import math
from direct.showbase.ShowBase import ShowBase
from panda3d.core import Vec3

base: ShowBase

class FreeFlyingCamera:
	"""Free flying debug camera with WASD controls"""

	def __init__(self, engine, position=(0, 0, 5), rotation=(0, 0)):
		self.engine = engine

		self.position = list(position)
		self.heading = rotation[1]
		self.pitch = rotation[0]

		self.speed = 5.0
		self.fast_speed = 15.0
		self.sensitivity = 100

	def handle_input(self, input_handler):
		"""Handle mouse and keyboard input"""
		# Mouse look
		dx, dy = input_handler.mouse_delta
		self.heading -= dx * self.sensitivity
		self.pitch += dy * self.sensitivity
		self.pitch = max(-89, min(89, self.pitch))

	def update(self, dt):
		"""Update camera position"""
		input_handler = self.engine.input_handler

		move_x = 0
		move_y = 0
		move_z = 0

		if input_handler.is_key_pressed('w'):
			move_y += 1
		if input_handler.is_key_pressed('s'):
			move_y -= 1
		if input_handler.is_key_pressed('d'):
			move_x += 1
		if input_handler.is_key_pressed('a'):
			move_x -= 1
		if input_handler.is_key_pressed('space'):
			move_z += 1
		if input_handler.is_key_pressed('control'):
			move_z -= 1

		speed = self.fast_speed if input_handler.is_key_pressed('shift') else self.speed

		heading_rad = math.radians(self.heading)
		pitch_rad = math.radians(self.pitch)

		forward = Vec3(
			-math.sin(heading_rad) * math.cos(pitch_rad),
			math.cos(heading_rad) * math.cos(pitch_rad),
			math.sin(pitch_rad)
		)
		right = Vec3(math.cos(heading_rad), math.sin(heading_rad), 0)
		up = Vec3(0, 0, 1)

		move_dir = forward * move_y + right * move_x + up * move_z
		if move_dir.length() > 0:
			move_dir.normalize()

		self.position[0] += move_dir.x * speed * dt
		self.position[1] += move_dir.y * speed * dt
		self.position[2] += move_dir.z * speed * dt

		self._apply_transform()

	def _apply_transform(self):
		"""Apply position and rotation to Panda3D camera"""
		base.camera.setPos(*self.position)
		base.camera.setHpr(self.heading, self.pitch, 0)

	def destroy(self):
		pass