import math

from direct.showbase.ShowBase import ShowBase
from panda3d.bullet import BulletCapsuleShape, BulletRigidBodyNode, ZUp
from panda3d.core import NodePath, Point3, Vec3

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
	"""First-person player controller with built-in camera and physics"""

	def __init__(self, engine, physics_world, position=(0, 0, 0), rotation=(0, 0), near_clip=0.1, far_clip=10000):
		self.engine = engine
		self.physics = physics_world

		# Debug
		self.debug_mode = False
		self._debug_ray_line = None
		self._debug_ray_ball = None

		# Interaction Distance
		self.interact_distance = 1.1

		# Node for player
		self.node = NodePath('player')
		self.node.reparentTo(base.render)

		# Position & rotation
		self._position = list(position)
		self._heading = rotation[1]
		self._pitch = rotation[0]
		self.initial_position = list(position)
		self.initial_heading = rotation[1]
		self.initial_pitch = rotation[0]

		# Physical properties
		self.height = 1.8
		self.radius = 0.3
		self.crouch_height = 1.0
		self.eye_offset = 0.1

		# Crouch transition
		self._current_height = self.height
		self.crouch_speed_transition = 10.0

		# Velocity
		self.velocity = Vec3(0, 0, 0)

		# Physics tuning
		self.gravity = -20.0
		self.jump_force = 6.0
		self.air_control = 0.3
		self.ground_accel = 10.0
		self.air_accel = 2.0
		self.friction = 10.0
		self.max_slope = 0.7  # ~45 degrees

		# Movement speeds (m/s)
		self.jog_speed = 3.0
		self.sprint_speed = 5.0
		self.crouch_speed = 1.5

		# Lean/peek
		self._lean = 0  # -1 left, 0 center, 1 right
		self._current_lean = 0
		self.lean_distance = 0.4  # How far to lean sideways
		self.lean_angle = 15  # Head tilt in degrees
		self.lean_speed = 12.0  # Transition speed

		# State
		self.is_crouching = False
		self.is_sprinting = False
		self.is_moving = False
		self.is_grounded = False

		# Mouse look
		self.sensitivity = 100
		self.looking = False

		# Built-in camera
		self.camera = PlayerCamera(engine, near_clip, far_clip)

		# Setup physics collider
		self._setup_collider()

		# Apply initial position
		self.position = position

	def _setup_collider(self):
		"""Create capsule collider for player"""
		shape = BulletCapsuleShape(self.radius, self.height - (self.radius * 2), ZUp)

		self.body = BulletRigidBodyNode('player_body')
		self.body.addShape(shape)
		self.body.setKinematic(True)

		self.body_np = self.node.attachNewNode(self.body)
		self.body_np.setPos(0, 0, self.height / 2)

		self.physics.attachRigidBody(self.body)

	def _clip_velocity(self, velocity, normal):
		"""Remove velocity component going into surface (Quake style)"""
		backoff = velocity.dot(normal)
		if backoff < 0:
			return velocity - normal * backoff
		return velocity

	def _slide_move(self, dt):
		"""Smooth wall sliding with multiple iterations"""
		from panda3d.core import TransformState, BitMask32

		mask = BitMask32.allOn()

		# Work with horizontal velocity only
		original_vel = Vec3(self.velocity.x, self.velocity.y, 0)
		remaining = Vec3(original_vel * dt)

		max_iterations = 4

		for _ in range(max_iterations):
			if remaining.length() < 0.001:
				break

			start = Point3(
				self._position[0],
				self._position[1],
				self._position[2] + self.height / 2 + 0.1
			)
			end = Point3(
				start.x + remaining.x,
				start.y + remaining.y,
				start.z
			)

			ts_from = TransformState.makePos(start)
			ts_to = TransformState.makePos(end)

			shape = BulletCapsuleShape(self.radius, self.height - (self.radius * 2), ZUp)
			result = self.physics.sweepTestClosest(shape, ts_from, ts_to, mask)

			if result.hasHit() and result.getNode() != self.body:
				fraction = result.getHitFraction()
				normal = result.getHitNormal()

				# Only walls
				if abs(normal.z) < self.max_slope:
					# Move to contact point (with small buffer)
					safe_fraction = max(fraction - 0.01, 0)
					self._position[0] += remaining.x * safe_fraction
					self._position[1] += remaining.y * safe_fraction

					# Calculate remaining movement
					remaining = remaining * (1.0 - fraction)

					# Project remaining onto wall (slide)
					dot = remaining.x * normal.x + remaining.y * normal.y
					remaining.x -= normal.x * dot
					remaining.y -= normal.y * dot

					# Also clip velocity for next frame
					vel_dot = self.velocity.x * normal.x + self.velocity.y * normal.y
					if vel_dot < 0:
						self.velocity.x -= normal.x * vel_dot
						self.velocity.y -= normal.y * vel_dot
				else:
					# Floor/ceiling - just move
					self._position[0] += remaining.x
					self._position[1] += remaining.y
					break
			else:
				# No hit - move full remaining distance
				self._position[0] += remaining.x
				self._position[1] += remaining.y
				break

		# Vertical movement
		self._position[2] += self.velocity.z * dt

		self.node.setPos(*self._position)

	def _check_ground(self):
		"""Raycast down to check if grounded - multiple rays for edge detection"""
		# Check center + 8 points around the capsule edge
		offsets = [(0, 0)]  # center
		for i in range(8):
			angle = math.radians(i * 45)
			offsets.append((
				math.cos(angle) * self.radius * 0.8,
				math.sin(angle) * self.radius * 0.8
			))

		best_ground_z = None

		for ox, oy in offsets:
			start = Point3(
				self._position[0] + ox,
				self._position[1] + oy,
				self._position[2] + 0.5
			)
			end = Point3(
				self._position[0] + ox,
				self._position[1] + oy,
				self._position[2] - 0.1
			)

			result = self.physics.rayTestClosest(start, end)

			if result.hasHit():
				normal = result.getHitNormal()
				if normal.z >= self.max_slope:
					ground_z = result.getHitPos().z
					if best_ground_z is None or ground_z > best_ground_z:
						best_ground_z = ground_z

		if best_ground_z is not None:
			self.is_grounded = True
			if self._position[2] < best_ground_z:
				self._position[2] = best_ground_z
				self.velocity.z = 0
				self.node.setPos(*self._position)
		else:
			self.is_grounded = False

	def _can_lean(self, direction):
		"""Check if we can lean in direction (-1 left, 1 right)"""
		heading_rad = math.radians(self._heading)
		right_x = math.cos(heading_rad)
		right_y = math.sin(heading_rad)

		# Full lean offset in that direction
		offset_x = -right_x * direction * self.lean_distance
		offset_y = -right_y * direction * self.lean_distance

		start = Point3(
			self._position[0],
			self._position[1],
			self._position[2] + self.eye_height
		)
		end = Point3(
			self._position[0] + offset_x,
			self._position[1] + offset_y,
			self._position[2] + self.eye_height
		)

		result = self.physics.rayTestClosest(start, end)
		return not result.hasHit()

	def _update_debug_ray(self):
		"""Draw debug raycast visualization"""
		from panda3d.core import LineSegs

		# Remove old debug visuals
		if self._debug_ray_line:
			self._debug_ray_line.removeNode()
			self._debug_ray_line = None
		if self._debug_ray_ball:
			self._debug_ray_ball.removeNode()
			self._debug_ray_ball = None

		if not self.debug_mode:
			return

		distance = self.interact_distance
		heading_rad = math.radians(self._heading)
		pitch_rad = math.radians(self._pitch)

		dx = -math.sin(heading_rad) * math.cos(pitch_rad)
		dy = math.cos(heading_rad) * math.cos(pitch_rad)
		dz = math.sin(pitch_rad)

		start = Point3(
			self.camera.position[0],
			self.camera.position[1],
			self.camera.position[2]
		)
		end = Point3(
			start.x + dx * distance,
			start.y + dy * distance,
			start.z + dz * distance
		)

		# Raycast to find hit point
		result = self.physics.rayTestClosest(start, end)

		ball_color = (1, 0, 0, 1)  # Red by default

		if result.hasHit():
			hit_pos = result.getHitPos()
			hit_node = result.getNode()

			# Check if it's an interactable object
			scene = self.engine.scene_handler.current_scene
			if hasattr(scene, 'interactive_objects'):
				for obj in scene.interactive_objects:
					if obj.collision_body == hit_node:
						ball_color = (0, 1, 0, 1)  # Green for interactable
						break
		else:
			hit_pos = end

		# Draw line
		lines = LineSegs()
		lines.setThickness(3)
		lines.setColor(1, 0, 0, 1)
		lines.moveTo(start)
		lines.drawTo(hit_pos)
		self._debug_ray_line = base.render.attachNewNode(lines.create())

		# Draw sphere at hit point
		self._debug_ray_ball = base.loader.loadModel("models/misc/sphere")
		self._debug_ray_ball.setScale(0.010)
		self._debug_ray_ball.setPos(hit_pos)
		self._debug_ray_ball.setColor(*ball_color)
		self._debug_ray_ball.setLightOff()
		self._debug_ray_ball.reparentTo(base.render)

	def get_look_hit(self, distance=3.0):
		"""Raycast from eye in look direction, return hit node or None"""
		heading_rad = math.radians(self._heading)
		pitch_rad = math.radians(self._pitch)

		# Direction from pitch/heading
		dx = -math.sin(heading_rad) * math.cos(pitch_rad)
		dy = math.cos(heading_rad) * math.cos(pitch_rad)
		dz = math.sin(pitch_rad)  # Fixed sign

		start = Point3(
			self.camera.position[0],
			self.camera.position[1],
			self.camera.position[2]
		)
		end = Point3(
			start.x + dx * distance,
			start.y + dy * distance,
			start.z + dz * distance
		)

		result = self.physics.rayTestClosest(start, end)

		if result.hasHit():
			return result.getNode()
		return None

	def try_interact(self):
		"""Raycast and interact with object if found"""
		hit_node = self.get_look_hit(distance=self.interact_distance)
		if hit_node:
			scene = self.engine.scene_handler.current_scene
			if hasattr(scene, 'interactive_objects'):
				for obj in scene.interactive_objects:
					if obj.collision_body == hit_node:
						obj.interact()
						return True
		return False

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
		return self._current_height - self.eye_offset

	@property
	def current_speed(self):
		if self.is_crouching:
			return self.crouch_speed
		elif self.is_sprinting:
			return self.sprint_speed
		else:
			return self.jog_speed

	def _update_camera(self):
		# Calculate lean offset
		heading_rad = math.radians(self._heading)
		right_x = math.cos(heading_rad)
		right_y = math.sin(heading_rad)

		# Desired lean offset
		lean_offset_x = -right_x * self._current_lean * self.lean_distance
		lean_offset_y = -right_y * self._current_lean * self.lean_distance

		# Check if lean position is blocked
		if self._current_lean != 0:
			start = Point3(
				self._position[0],
				self._position[1],
				self._position[2] + self.eye_height
			)
			end = Point3(
				self._position[0] + lean_offset_x,
				self._position[1] + lean_offset_y,
				self._position[2] + self.eye_height
			)

			result = self.physics.rayTestClosest(start, end)

			if result.hasHit():
				# Reduce lean to just before hit
				fraction = result.getHitFraction() * 0.8  # Back off a bit
				lean_offset_x *= fraction
				lean_offset_y *= fraction

		self.camera.position = [
			self._position[0] + lean_offset_x,
			self._position[1] + lean_offset_y,
			self._position[2] + self.eye_height
		]
		self.camera.rotation = [
			self._pitch,
			self._heading,
			-self._current_lean * self.lean_angle
		]
		self.camera._apply_transform()

	def reset(self, position=None, rotation=None):
		"""Reset player to position and rotation"""
		if position:
			self._position = list(position)
		else:
			self._position = list(self.initial_position)

		if rotation:
			self._pitch = rotation[0]
			self._heading = rotation[1]
		else:
			self._pitch = self.initial_pitch
			self._heading = self.initial_heading

		self.velocity = Vec3(0, 0, 0)
		self._current_lean = 0
		self._lean = 0
		self._current_height = self.height
		self.is_grounded = False
		self.is_crouching = False
		self.is_sprinting = False

		self.node.setPos(*self._position)
		self._update_camera()

	def handle_input(self, input_handler):
		# Always looking - lock mouse on first input
		if not self.looking:
			input_handler.set_mouse_locked(True)
			self.looking = True

		# Mouse look
		dx, dy = input_handler.mouse_delta
		self.heading -= dx * self.sensitivity
		self.pitch += dy * self.sensitivity

		self.is_crouching = input_handler.is_key_pressed('control')
		self.is_sprinting = (
			input_handler.is_key_pressed('shift') and
			not self.is_crouching and
			input_handler.is_key_pressed('w')
		)

		# Jump
		if input_handler.is_key_down('space') and self.is_grounded:
			self.velocity.z = self.jump_force
			self.is_grounded = False

		# Lean
		if input_handler.is_key_pressed('q') and self._can_lean(1):
			self._lean = 1
		elif input_handler.is_key_pressed('e') and self._can_lean(-1):
			self._lean = -1
		else:
			self._lean = 0

		if input_handler.is_key_down('f'):
			self.try_interact()

	def update(self, dt):
		if not self.looking:
			self._update_camera()
			return

		input_handler = self.engine.input_handler

		# Get input direction
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

		# Normalize diagonal
		if move_x != 0 and move_y != 0:
			move_x *= 0.707
			move_y *= 0.707

		# Convert to world direction
		heading_rad = math.radians(self._heading)
		forward = Vec3(-math.sin(heading_rad), math.cos(heading_rad), 0)
		right = Vec3(math.cos(heading_rad), math.sin(heading_rad), 0)

		wish_dir = forward * move_y + right * move_x
		wish_speed = self.current_speed

		if self.is_grounded:
			# Apply friction
			speed = self.velocity.xy.length()
			if speed > 0:
				drop = speed * self.friction * dt
				self.velocity.x *= max(speed - drop, 0) / speed
				self.velocity.y *= max(speed - drop, 0) / speed

			# Accelerate
			if self.is_moving:
				current_speed = self.velocity.dot(wish_dir)
				add_speed = wish_speed - current_speed
				if add_speed > 0:
					accel = self.ground_accel * dt * wish_speed
					accel = min(accel, add_speed)
					self.velocity.x += wish_dir.x * accel
					self.velocity.y += wish_dir.y * accel
		else:
			# Air movement (limited)
			if self.is_moving:
				current_speed = self.velocity.dot(wish_dir)
				add_speed = wish_speed * self.air_control - current_speed
				if add_speed > 0:
					accel = self.air_accel * dt * wish_speed
					accel = min(accel, add_speed)
					self.velocity.x += wish_dir.x * accel
					self.velocity.y += wish_dir.y * accel

			# Gravity
			self.velocity.z += self.gravity * dt

		# Smooth crouch transition
		target_height = self.crouch_height if self.is_crouching else self.height
		if self._current_height != target_height:
			old_height = self._current_height
			diff = target_height - self._current_height
			self._current_height += diff * self.crouch_speed_transition * dt

			# Snap if close enough
			if abs(self._current_height - target_height) < 0.01:
				self._current_height = target_height

			# In air: keep head at same position (feet come up)
			if not self.is_grounded:
				height_change = old_height - self._current_height
				self._position[2] += height_change
				self.node.setPos(*self._position)

		# Move with collision
		self._slide_move(dt)

		# Ground check
		self._check_ground()

		# Smooth lean transition
		if self._current_lean != self._lean:
			diff = self._lean - self._current_lean
			self._current_lean += diff * self.lean_speed * dt

			if abs(self._current_lean - self._lean) < 0.01:
				self._current_lean = self._lean

		# Debug visualization
		self._update_debug_ray()

		# Update Camera
		self._update_camera()

	def destroy(self):
		if self._debug_ray_line:
			self._debug_ray_line.removeNode()
		if self._debug_ray_ball:
			self._debug_ray_ball.removeNode()
		if self.body:
			self.physics.removeRigidBody(self.body)
		if self.node:
			self.node.removeNode()
			self.node = None