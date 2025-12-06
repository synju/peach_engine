import math
from .camera import Camera

class FirstPersonCamera(Camera):
	"""First person camera with WASD movement and mouse look"""

	def __init__(self, engine, position=(0, 0, 2), rotation=(0, 0, 0),
							 speed=10, fast_speed=25, sensitivity=100):
		super().__init__(engine, position, rotation)

		self.speed = speed
		self.fast_speed = fast_speed
		self.sensitivity = sensitivity
		self.looking = False

		# Store input handler reference
		self._input = None

	def handle_input(self, input_handler):
		"""Handle input for the camera"""
		if not self.active:
			return

		self._input = input_handler

		# Right mouse to look
		if input_handler.is_mouse_pressed(3):
			if not self.looking:
				input_handler.set_mouse_locked(True)
				self.looking = True

			# Mouse look
			dx, dy = input_handler.mouse_delta
			self.rotation[1] -= dx * self.sensitivity  # heading (left/right)
			self.rotation[0] += dy * self.sensitivity  # pitch (up/down)

			# Clamp pitch to prevent flipping
			self.rotation[0] = max(-90, min(90, self.rotation[0]))

			# Wrap heading around 0-360
			self.rotation[1] = self.rotation[1] % 360
		else:
			if self.looking:
				input_handler.set_mouse_locked(False)
				self.looking = False

	def update(self, dt):
		"""Update camera position"""
		if not self.active:
			return

		# Only move while looking
		if not self.looking or not self._input:
			self._apply_transform()
			return

		input_handler = self._input

		# Movement speed
		current_speed = self.fast_speed if input_handler.is_key_pressed('shift') else self.speed
		move_amount = current_speed * dt

		# Calculate forward and right vectors (Panda3D: X=right, Y=forward, Z=up)
		heading_rad = math.radians(self.rotation[1])
		# Forward is along Y axis, rotated by heading
		forward = [-math.sin(heading_rad), math.cos(heading_rad), 0]
		right = [math.cos(heading_rad), math.sin(heading_rad), 0]

		# WASD movement
		if input_handler.is_key_pressed('w'):
			self.position[0] += forward[0] * move_amount
			self.position[1] += forward[1] * move_amount
		if input_handler.is_key_pressed('s'):
			self.position[0] -= forward[0] * move_amount
			self.position[1] -= forward[1] * move_amount
		if input_handler.is_key_pressed('d'):
			self.position[0] += right[0] * move_amount
			self.position[1] += right[1] * move_amount
		if input_handler.is_key_pressed('a'):
			self.position[0] -= right[0] * move_amount
			self.position[1] -= right[1] * move_amount

		# Up/down (Z axis)
		if input_handler.is_key_pressed('space'):
			self.position[2] += move_amount
		if input_handler.is_key_pressed('control'):
			self.position[2] -= move_amount

		self._apply_transform()