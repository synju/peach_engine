import math
from direct.showbase.ShowBase import ShowBase
from engine.camera import Camera

base: ShowBase


class OrbitalCamera(Camera):
	"""Third-person orbital camera that follows a target"""

	def __init__(self, engine, target=None, distance=5.0, height_offset=1.5, near_clip=0.1, far_clip=10000):
		super().__init__(engine, (0, 0, 0), (0, 0, 0), near_clip, far_clip)

		self.target = target
		self.distance = distance
		self.height_offset = height_offset

		# Zoom limits
		self.min_distance = 1.0
		self.max_distance = 20.0
		self.zoom_speed = 0.5

		# Orbit angles
		self.heading = 0
		self.pitch = 20  # Slight downward angle (positive = looking down)

		# Mouse sensitivity
		self.sensitivity = 100

		# Gamepad sensitivity
		self.gamepad_sensitivity_x = 1.5
		self.gamepad_sensitivity_y = 0.8
		self.trigger_zoom_speed = 0.1

		# Pitch limits
		self.min_pitch = -80
		self.max_pitch = 80

		# Register scroll events
		base.accept('wheel_up', self._zoom_in)
		base.accept('wheel_down', self._zoom_out)

	def _zoom_in(self):
		self.distance = max(self.min_distance, self.distance - self.zoom_speed)

	def _zoom_out(self):
		self.distance = min(self.max_distance, self.distance + self.zoom_speed)

	def set_target(self, target):
		"""Set the target to follow"""
		self.target = target

	def handle_input(self, input_handler):
		"""Handle mouse look and gamepad for orbiting"""
		# Mouse input
		dx, dy = input_handler.mouse_delta
		self.heading -= dx * self.sensitivity
		self.pitch -= dy * self.sensitivity
		self.pitch = max(self.min_pitch, min(self.max_pitch, self.pitch))

		# Gamepad right stick for camera
		if input_handler.is_gamepad_available():
			rx, ry = input_handler.get_right_stick()
			self.heading -= rx * self.gamepad_sensitivity_x
			self.pitch -= ry * self.gamepad_sensitivity_y
			self.pitch = max(self.min_pitch, min(self.max_pitch, self.pitch))

			# Triggers for zoom
			left_trig, right_trig = input_handler.get_triggers()
			if right_trig > 0.1:
				self.distance = max(self.min_distance, self.distance - right_trig * self.trigger_zoom_speed)
			if left_trig > 0.1:
				self.distance = min(self.max_distance, self.distance + left_trig * self.trigger_zoom_speed)

	def update(self, dt):
		"""Update camera position to orbit around target"""
		if not self.target:
			return

		# Get target position
		if hasattr(self.target, 'position'):
			target_pos = self.target.position
		elif hasattr(self.target, 'node') and self.target.node:
			pos = self.target.node.getPos()
			target_pos = [pos.x, pos.y, pos.z]
		else:
			return

		# Calculate desired camera position based on orbit angles
		heading_rad = math.radians(self.heading)
		pitch_rad = math.radians(self.pitch)

		# Offset from target
		offset_x = math.sin(heading_rad) * math.cos(pitch_rad) * self.distance
		offset_y = -math.cos(heading_rad) * math.cos(pitch_rad) * self.distance
		offset_z = math.sin(pitch_rad) * self.distance

		desired_pos = [
			target_pos[0] + offset_x,
			target_pos[1] + offset_y,
			target_pos[2] + self.height_offset + offset_z
		]

		# Raycast from target to desired position to check for walls
		from panda3d.core import Point3
		start = Point3(target_pos[0], target_pos[1], target_pos[2] + self.height_offset)
		end = Point3(desired_pos[0], desired_pos[1], desired_pos[2])

		result = self.engine.physics.rayTestClosest(start, end)

		if result.hasHit():
			# Move camera to just before hit point
			hit_pos = result.getHitPos()
			# Pull back slightly from wall
			direction = end - start
			direction.normalize()
			self.position = [
				hit_pos.x - direction.x * 0.2,
				hit_pos.y - direction.y * 0.2,
				hit_pos.z - direction.z * 0.2
			]
		else:
			self.position = desired_pos

		# Look at target
		self.rotation = [
			-self.pitch,
			self.heading,
			0
		]

		self._apply_transform()

	def set_heading(self, value):
		self.heading = value % 360

	def set_pitch(self, value):
		self.pitch = max(self.min_pitch, min(self.max_pitch, value))