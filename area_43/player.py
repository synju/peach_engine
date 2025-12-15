import math

from direct.showbase.ShowBase import ShowBase
from panda3d.bullet import BulletCapsuleShape, BulletGhostNode, BulletRigidBodyNode, ZUp
from panda3d.core import NodePath, Point3, Vec3

from area_43.player_camera import PlayerCamera

base: ShowBase

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

		# Noclip mode
		self.noclip_mode = False
		self.noclip_speed = 5.0
		self.noclip_fast_speed = 15.0

		# Creature Interaction
		self.creatures_ignore_player = False

		# Built-in camera
		self.camera = PlayerCamera(engine, near_clip, far_clip)

		# Setup physics collider
		self._setup_collider()

		# Apply initial position
		self.position = position

		# Register console commands
		self.engine.scene_handler.console.register_command('noclip', self.toggle_noclip, "Toggle noclip mode")

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

	def _test_position(self, x, y, z):
		"""Test if capsule at position overlaps any walls. Returns (blocked, normal)"""

		# Create temp ghost at test position (raised slightly to avoid floor)
		shape = BulletCapsuleShape(self.radius, self._current_height - (self.radius * 2), ZUp)
		ghost = BulletGhostNode('test')
		ghost.addShape(shape)
		ghost_np = NodePath(ghost)
		ghost_np.setPos(x, y, z + self._current_height / 2 + 0.05)

		self.physics.attachGhost(ghost)

		# Check overlaps
		result = self.physics.contactTest(ghost)

		wall_normal = None
		blocked = False

		for contact in result.getContacts():
			other = contact.getNode0() if contact.getNode1() == ghost else contact.getNode1()
			if other == self.body:
				continue

			manifold = contact.getManifoldPoint()
			normal = manifold.getNormalWorldOnB()

			# Flip normal if needed (should point away from wall, toward player)
			if contact.getNode0() == ghost:
				normal = Vec3(-normal.x, -normal.y, -normal.z)

			# Only care about walls
			if abs(normal.z) < self.max_slope:
				blocked = True
				wall_normal = normal
				break

		self.physics.removeGhost(ghost)
		ghost_np.removeNode()

		return blocked, wall_normal

	def _test_ceiling(self, x, y, z):
		"""Test if capsule at position overlaps a ceiling. Returns True if blocked."""

		# Create temp ghost at test position
		shape = BulletCapsuleShape(self.radius, self._current_height - (self.radius * 2), ZUp)
		ghost = BulletGhostNode('test_ceiling')
		ghost.addShape(shape)
		ghost_np = NodePath(ghost)
		ghost_np.setPos(x, y, z + self._current_height / 2 + 0.05)

		self.physics.attachGhost(ghost)

		# Check overlaps
		result = self.physics.contactTest(ghost)

		blocked = False

		for contact in result.getContacts():
			other = contact.getNode0() if contact.getNode1() == ghost else contact.getNode1()
			if other == self.body:
				continue

			manifold = contact.getManifoldPoint()
			normal = manifold.getNormalWorldOnB()

			# Flip normal if needed
			if contact.getNode0() == ghost:
				normal = Vec3(-normal.x, -normal.y, -normal.z)

			# Ceiling has downward-facing normal (negative Z)
			if normal.z < -self.max_slope:
				blocked = True
				break

		self.physics.removeGhost(ghost)
		ghost_np.removeNode()

		return blocked

	def _slide_move(self, dt):
		"""Wall sliding with overlap testing - finds slide direction iteratively"""

		# Desired movement
		move_x = self.velocity.x * dt
		move_y = self.velocity.y * dt
		move_len = math.sqrt(move_x * move_x + move_y * move_y)

		# Horizontal movement (only if moving)
		if move_len >= 0.0001:
			# Test destination
			new_x = self._position[0] + move_x
			new_y = self._position[1] + move_y

			blocked, _ = self._test_position(new_x, new_y, self._position[2])

			if not blocked:
				# Clear path - move there
				self._position[0] = new_x
				self._position[1] = new_y
			else:
				# Blocked - find slide direction by testing angles
				# Start from movement direction, test outward in both directions
				move_angle = math.atan2(move_y, move_x)

				found_slide = False

				# Test angles from 10 to 90 degrees in both directions
				for offset_deg in range(10, 91, 10):
					offset_rad = math.radians(offset_deg)

					# Try positive angle (left)
					test_angle = move_angle + offset_rad
					test_x = self._position[0] + math.cos(test_angle) * move_len
					test_y = self._position[1] + math.sin(test_angle) * move_len

					blocked_left, _ = self._test_position(test_x, test_y, self._position[2])

					if not blocked_left:
						# Scale speed by how much we're deflecting (cos of offset)
						speed_scale = math.cos(offset_rad)
						self._position[0] += math.cos(test_angle) * move_len * speed_scale
						self._position[1] += math.sin(test_angle) * move_len * speed_scale
						found_slide = True
						break

					# Try negative angle (right)
					test_angle = move_angle - offset_rad
					test_x = self._position[0] + math.cos(test_angle) * move_len
					test_y = self._position[1] + math.sin(test_angle) * move_len

					blocked_right, _ = self._test_position(test_x, test_y, self._position[2])

					if not blocked_right:
						speed_scale = math.cos(offset_rad)
						self._position[0] += math.cos(test_angle) * move_len * speed_scale
						self._position[1] += math.sin(test_angle) * move_len * speed_scale
						found_slide = True
						break

				# If no slide found at 90 degrees, we're in a corner or facing wall directly
				if not found_slide:
					self.velocity.x = 0
					self.velocity.y = 0

		# Vertical movement - check ceiling BEFORE moving up
		if self.velocity.z > 0:
			# Moving up - check for ceiling using ghost test
			move_z = self.velocity.z * dt
			new_z = self._position[2] + move_z

			# Test if new position would overlap ceiling
			if self._test_ceiling(self._position[0], self._position[1], new_z):
				# Binary search to find max height we can reach
				low_z = self._position[2]
				high_z = new_z
				for _ in range(5):  # 5 iterations gives ~3% precision
					mid_z = (low_z + high_z) / 2
					if self._test_ceiling(self._position[0], self._position[1], mid_z):
						high_z = mid_z
					else:
						low_z = mid_z

				self._position[2] = low_z
				self.velocity.z = 0
			else:
				self._position[2] = new_z
		else:
			# Moving down or stationary
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

	def _check_ceiling(self):
		"""Raycast up to check for ceiling collision when jumping"""
		if self.velocity.z <= 0:
			return

		# Check center + 8 points around the capsule edge
		offsets = [(0, 0)]
		for i in range(8):
			angle = math.radians(i * 45)
			offsets.append((
				math.cos(angle) * self.radius * 0.8,
				math.sin(angle) * self.radius * 0.8
			))

		for ox, oy in offsets:
			start = Point3(
				self._position[0] + ox,
				self._position[1] + oy,
				self._position[2] + self._current_height
			)
			end = Point3(
				self._position[0] + ox,
				self._position[1] + oy,
				self._position[2] + self._current_height + 0.2
			)

			result = self.physics.rayTestClosest(start, end)

			if result.hasHit():
				# Hit ceiling - stop upward velocity
				ceiling_z = result.getHitPos().z
				self._position[2] = ceiling_z - self._current_height - 0.01
				self.velocity.z = 0
				self.node.setPos(*self._position)
				return

	def _can_uncrouch(self):
		"""Check if there's enough headroom to stand up"""
		# Create a standing-height capsule and check for any overlap
		shape = BulletCapsuleShape(self.radius, self.height - (self.radius * 2), ZUp)
		ghost = BulletGhostNode('uncrouch_test')
		ghost.addShape(shape)
		ghost_np = NodePath(ghost)
		ghost_np.setPos(self._position[0], self._position[1], self._position[2] + self.height / 2 + 0.05)

		self.physics.attachGhost(ghost)
		result = self.physics.contactTest(ghost)

		blocked = False
		for contact in result.getContacts():
			other = contact.getNode0() if contact.getNode1() == ghost else contact.getNode1()
			if other == self.body:
				continue
			blocked = True
			break

		self.physics.removeGhost(ghost)
		ghost_np.removeNode()

		return not blocked

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

		# Get actual hit position
		result = self.physics.rayTestClosest(start, end)
		if result.hasHit():
			hit_pos = result.getHitPos()
			end = hit_pos

		# Draw line
		lines = LineSegs()
		lines.setColor(0, 1, 0, 1)
		lines.setThickness(2)
		lines.moveTo(start)
		lines.drawTo(end)
		self._debug_ray_line = base.render.attachNewNode(lines.create())
		self._debug_ray_line.setBin('fixed', 100)
		self._debug_ray_line.setDepthTest(False)
		self._debug_ray_line.setDepthWrite(False)
		self._debug_ray_line.setLightOff()

		# Draw ball at end
		if result.hasHit():
			from panda3d.core import GeomVertexFormat, GeomVertexData, GeomVertexWriter
			from panda3d.core import Geom, GeomPoints, GeomNode

			fmt = GeomVertexFormat.get_v3c4()
			vdata = GeomVertexData('ball', fmt, Geom.UHStatic)
			vdata.setNumRows(1)

			vertex = GeomVertexWriter(vdata, 'vertex')
			color = GeomVertexWriter(vdata, 'color')

			vertex.addData3(end.x, end.y, end.z)
			color.addData4(1, 0, 0, 1)

			points = GeomPoints(Geom.UHStatic)
			points.addVertex(0)
			points.closePrimitive()

			geom = Geom(vdata)
			geom.addPrimitive(points)

			node = GeomNode('debug_ball')
			node.addGeom(geom)

			self._debug_ray_ball = base.render.attachNewNode(node)
			self._debug_ray_ball.setRenderModeThickness(10)
			self._debug_ray_ball.setBin('fixed', 100)
			self._debug_ray_ball.setDepthTest(False)
			self._debug_ray_ball.setDepthWrite(False)
			self._debug_ray_ball.setLightOff()

	def get_look_hit(self, distance=5.0):
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

		# Disable noclip on reset
		if self.noclip_mode:
			self.noclip_mode = False
			self.physics.attachRigidBody(self.body)

		self.node.setPos(*self._position)
		self._update_camera()

	def toggle_noclip(self, args):
		"""Toggle noclip mode on/off"""
		self.noclip_mode = not self.noclip_mode

		if self.noclip_mode:
			# Disable collision
			self.physics.removeRigidBody(self.body)
			self.velocity = Vec3(0, 0, 0)
		else:
			# Re-enable collision
			self.physics.attachRigidBody(self.body)
			self.is_grounded = False

		return f"Noclip: {'ON' if self.noclip_mode else 'OFF'}"

	def handle_input(self, input_handler):
		# Always looking - lock mouse on first input
		if not self.looking:
			input_handler.set_mouse_locked(True)
			self.looking = True

		# Mouse look
		dx, dy = input_handler.mouse_delta
		self.heading -= dx * self.sensitivity
		self.pitch += dy * self.sensitivity

		# Crouch - check headroom before uncrouching
		wants_crouch = input_handler.is_key_pressed('control')
		if wants_crouch:
			self.is_crouching = True
		elif self.is_crouching and self._can_uncrouch():
			self.is_crouching = False
		# else: stay crouched until there's headroom

		self.is_sprinting = (
			input_handler.is_key_pressed('shift') and
			not self.is_crouching
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

		if input_handler.is_key_down('v'):
			self.toggle_noclip(args=None)
			self.engine.scene_handler.console.print(f"Noclip: {'ON' if self.noclip_mode else 'OFF'}")

		if input_handler.is_key_down('c'):
			self.creatures_ignore_player = not self.creatures_ignore_player
			self.engine.scene_handler.console.print(f"Creatures ignore player: {'ON' if self.creatures_ignore_player else 'OFF'}")

	def update(self, dt):
		if not self.looking:
			# Still apply gravity and ground check even before mouse input
			if not self.noclip_mode:
				if not self.is_grounded:
					self.velocity.z += self.gravity * dt
				self._slide_move(dt)
				self._check_ground()
			self._update_camera()
			return

		input_handler = self.engine.input_handler

		# Get input direction
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

		# Noclip mode - fly freely
		if self.noclip_mode:
			if input_handler.is_key_pressed('space'):
				move_z += 1
			if input_handler.is_key_pressed('control'):
				move_z -= 1

			# Calculate 3D movement direction based on camera orientation
			heading_rad = math.radians(self._heading)
			pitch_rad = math.radians(self._pitch)

			# Forward vector (includes pitch)
			forward = Vec3(
				-math.sin(heading_rad) * math.cos(pitch_rad),
				math.cos(heading_rad) * math.cos(pitch_rad),
				math.sin(pitch_rad)
			)
			# Right vector (horizontal only)
			right = Vec3(math.cos(heading_rad), math.sin(heading_rad), 0)
			# Up vector (world up)
			up = Vec3(0, 0, 1)

			# Build movement vector
			move_dir = forward * move_y + right * move_x + up * move_z

			# Normalize if moving
			if move_dir.length() > 0:
				move_dir.normalize()

			# Speed (shift for fast)
			speed = self.noclip_fast_speed if input_handler.is_key_pressed('shift') else self.noclip_speed

			# Apply movement directly (no collision)
			self._position[0] += move_dir.x * speed * dt
			self._position[1] += move_dir.y * speed * dt
			self._position[2] += move_dir.z * speed * dt

			self.node.setPos(*self._position)
			self._update_camera()
			return

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
			# Only remove if attached (not in noclip mode)
			if not self.noclip_mode:
				self.physics.removeRigidBody(self.body)
		if self.node:
			self.node.removeNode()
			self.node = None