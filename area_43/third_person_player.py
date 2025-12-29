import math
from direct.showbase.ShowBase import ShowBase
from panda3d.core import Vec3, NodePath
from panda3d.bullet import BulletCapsuleShape, BulletRigidBodyNode, BulletGhostNode, ZUp

from area_43.orbital_camera import OrbitalCamera
from engine.actor_object import ActorObject

base: ShowBase

class ThirdPersonPlayer:
	"""Third-person player controller using face_spider model"""

	def __init__(self, engine, physics_world, position=(0, 0, 0), rotation=(0, 0), near_clip=0.1, far_clip=10000, debug_mode=False):
		self.engine = engine
		self.physics = physics_world

		# Debug
		self.debug_mode = debug_mode
		self._debug_hitbox = None

		# Position & rotation
		self.position = list(position)
		self._heading = rotation[1]
		self.initial_position = list(position)
		self.initial_heading = rotation[1]

		# Physical properties
		self.height = 0.3
		self.radius = 0.3

		# Velocity
		self.velocity = Vec3(0, 0, 0)

		# Physics tuning
		self.gravity = -20.0
		self.jump_force = 6.0
		self.ground_accel = 5.0
		self.friction = 10.0
		self.max_slope = 0.7

		# Movement speed
		self.walk_speed = 3.0
		self.run_speed = 3.0

		# State
		self.is_grounded = False
		self.is_moving = False
		self.is_running = False

		# Mouse look
		self.looking = False

		# Load actor (face_spider model)
		self.actor = ActorObject(
			engine,
			model_path='entities/models/face_spider.gltf',
			position=position,
			scale=0.1
		)

		# Store node reference
		self.node = self.actor.node

		# Animation state
		self._current_anim = None

		# Setup physics collider
		self._setup_collider()

		# Create orbital camera
		self.camera = OrbitalCamera(engine, target=self, distance=4.0, height_offset=self.height - 0.1, near_clip=near_clip, far_clip=far_clip)

		# Start idle animation
		self._play_anim('idle', loop=True)

	def _setup_collider(self):
		"""Create capsule collider"""
		shape = BulletCapsuleShape(self.radius, self.height - (self.radius * 2), ZUp)

		self.body = BulletRigidBodyNode('third_person_body')
		self.body.addShape(shape)
		self.body.setKinematic(True)

		self.body_np = base.render.attachNewNode(self.body)
		self.body_np.setPos(self.position[0], self.position[1], self.position[2] + self.height / 2)

		self.physics.attachRigidBody(self.body)

	def _play_anim(self, anim_name, loop=False, blend_time=0.2):
		"""Play animation with optional blending"""
		if self._current_anim == anim_name:
			return

		self._current_anim = anim_name

		if loop:
			self.actor.loop(anim_name, blend_time=blend_time)
		else:
			self.actor.play(anim_name, blend_time=blend_time)

	def _test_position(self, x, y, z):
		"""Test if capsule at position overlaps walls"""
		shape = BulletCapsuleShape(self.radius, self.height - (self.radius * 2), ZUp)
		ghost = BulletGhostNode('test')
		ghost.addShape(shape)
		ghost_np = NodePath(ghost)
		ghost_np.setPos(x, y, z + self.height / 2 + 0.05)

		self.physics.attachGhost(ghost)
		result = self.physics.contactTest(ghost)

		blocked = False
		for contact in result.getContacts():
			other = contact.getNode0() if contact.getNode1() == ghost else contact.getNode1()
			if other == self.body:
				continue

			manifold = contact.getManifoldPoint()
			normal = manifold.getNormalWorldOnB()

			if contact.getNode0() == ghost:
				normal = Vec3(-normal.x, -normal.y, -normal.z)

			if abs(normal.z) < self.max_slope:
				blocked = True
				break

		self.physics.removeGhost(ghost)
		ghost_np.removeNode()

		return blocked

	def _slide_move(self, dt):
		"""Move with wall sliding"""
		move_x = self.velocity.x * dt
		move_y = self.velocity.y * dt
		move_len = math.sqrt(move_x * move_x + move_y * move_y)

		if move_len >= 0.0001:
			new_x = self.position[0] + move_x
			new_y = self.position[1] + move_y

			if not self._test_position(new_x, new_y, self.position[2]):
				self.position[0] = new_x
				self.position[1] = new_y
			else:
				# Try sliding
				move_angle = math.atan2(move_y, move_x)

				for offset_deg in range(10, 91, 10):
					offset_rad = math.radians(offset_deg)

					# Try left
					test_angle = move_angle + offset_rad
					test_x = self.position[0] + math.cos(test_angle) * move_len
					test_y = self.position[1] + math.sin(test_angle) * move_len

					if not self._test_position(test_x, test_y, self.position[2]):
						speed_scale = math.cos(offset_rad)
						self.position[0] += math.cos(test_angle) * move_len * speed_scale
						self.position[1] += math.sin(test_angle) * move_len * speed_scale
						break

					# Try right
					test_angle = move_angle - offset_rad
					test_x = self.position[0] + math.cos(test_angle) * move_len
					test_y = self.position[1] + math.sin(test_angle) * move_len

					if not self._test_position(test_x, test_y, self.position[2]):
						speed_scale = math.cos(offset_rad)
						self.position[0] += math.cos(test_angle) * move_len * speed_scale
						self.position[1] += math.sin(test_angle) * move_len * speed_scale
						break
				else:
					self.velocity.x = 0
					self.velocity.y = 0

		# Vertical movement
		self.position[2] += self.velocity.z * dt

		# Update node positions
		self.node.setPos(*self.position)
		self.body_np.setPos(self.position[0], self.position[1], self.position[2] + self.height / 2)

	def _check_ground(self):
		"""Raycast down to check ground"""
		from panda3d.core import Point3

		start = Point3(self.position[0], self.position[1], self.position[2] + 0.05)
		end = Point3(self.position[0], self.position[1], self.position[2] - 0.1)

		# Draw debug raycast
		if self.debug_mode:
			self._draw_debug_raycast(start, end)

		result = self.physics.rayTestClosest(start, end)

		if result.hasHit():
			normal = result.getHitNormal()
			if normal.z >= self.max_slope:
				self.is_grounded = True
				ground_z = result.getHitPos().z
				if self.position[2] < ground_z:
					self.position[2] = ground_z
					self.velocity.z = 0
					self.node.setPos(*self.position)
					self.body_np.setPos(self.position[0], self.position[1], self.position[2] + self.height / 2)
				return

		self.is_grounded = False

	def _draw_debug_raycast(self, start, end):
		"""Draw the ground check raycast"""
		from panda3d.core import LineSegs

		# Remove old line
		if hasattr(self, '_debug_raycast') and self._debug_raycast:
			self._debug_raycast.removeNode()

		lines = LineSegs()
		lines.setColor(1, 0, 1, 1)  # Magenta
		lines.setThickness(2)
		lines.moveTo(start)
		lines.drawTo(end)

		self._debug_raycast = base.render.attachNewNode(lines.create())
		self._debug_raycast.setLightOff()
		self._debug_raycast.setBin('fixed', 100)
		self._debug_raycast.setDepthTest(False)
		self._debug_raycast.setDepthWrite(False)

	def _create_debug_hitbox(self):
		"""Create capsule outline for visualization"""
		from panda3d.core import LineSegs

		lines = LineSegs()
		lines.setColor(0, 1, 1, 1)
		lines.setThickness(2)

		radius = self.radius
		height = self.height
		segments = 16

		# Bottom circle
		for i in range(segments + 1):
			angle = (i / segments) * math.pi * 2
			x = math.cos(angle) * radius
			y = math.sin(angle) * radius
			if i == 0:
				lines.moveTo(x, y, 0)
			else:
				lines.drawTo(x, y, 0)

		# Top circle
		for i in range(segments + 1):
			angle = (i / segments) * math.pi * 2
			x = math.cos(angle) * radius
			y = math.sin(angle) * radius
			if i == 0:
				lines.moveTo(x, y, height)
			else:
				lines.drawTo(x, y, height)

		# Vertical lines
		for i in range(4):
			angle = (i / 4) * math.pi * 2
			x = math.cos(angle) * radius
			y = math.sin(angle) * radius
			lines.moveTo(x, y, 0)
			lines.drawTo(x, y, height)

		node = lines.create()
		np = base.render.attachNewNode(node)
		np.setBin('fixed', 100)
		np.setDepthTest(False)
		np.setDepthWrite(False)
		np.setLightOff()
		return np

	def _update_debug_hitbox(self):
		"""Update debug hitbox"""
		if self.debug_mode:
			if not self._debug_hitbox:
				self._debug_hitbox = self._create_debug_hitbox()
			self._debug_hitbox.setPos(self.position[0], self.position[1], self.position[2])

			# Draw position sphere
			self._draw_debug_position_sphere()
		elif self._debug_hitbox:
			self._debug_hitbox.removeNode()
			self._debug_hitbox = None
			if hasattr(self, '_debug_pos_sphere') and self._debug_pos_sphere:
				self._debug_pos_sphere.removeNode()
				self._debug_pos_sphere = None

	def _draw_debug_position_sphere(self):
		"""Draw a red sphere at the spider's position"""
		from panda3d.core import LineSegs

		# Remove old sphere
		if hasattr(self, '_debug_pos_sphere') and self._debug_pos_sphere:
			self._debug_pos_sphere.removeNode()

		lines = LineSegs()
		lines.setColor(1, 0, 0, 1)  # Red
		lines.setThickness(2)

		radius = 0.05
		segments = 12

		# Draw 3 circles for a sphere wireframe
		# XY circle
		for i in range(segments + 1):
			angle = (i / segments) * math.pi * 2
			x = math.cos(angle) * radius
			y = math.sin(angle) * radius
			if i == 0:
				lines.moveTo(self.position[0] + x, self.position[1] + y, self.position[2])
			else:
				lines.drawTo(self.position[0] + x, self.position[1] + y, self.position[2])

		# XZ circle
		for i in range(segments + 1):
			angle = (i / segments) * math.pi * 2
			x = math.cos(angle) * radius
			z = math.sin(angle) * radius
			if i == 0:
				lines.moveTo(self.position[0] + x, self.position[1], self.position[2] + z)
			else:
				lines.drawTo(self.position[0] + x, self.position[1], self.position[2] + z)

		# YZ circle
		for i in range(segments + 1):
			angle = (i / segments) * math.pi * 2
			y = math.cos(angle) * radius
			z = math.sin(angle) * radius
			if i == 0:
				lines.moveTo(self.position[0], self.position[1] + y, self.position[2] + z)
			else:
				lines.drawTo(self.position[0], self.position[1] + y, self.position[2] + z)

		self._debug_pos_sphere = base.render.attachNewNode(lines.create())
		self._debug_pos_sphere.setLightOff()
		self._debug_pos_sphere.setBin('fixed', 100)
		self._debug_pos_sphere.setDepthTest(False)
		self._debug_pos_sphere.setDepthWrite(False)

	def handle_input(self, input_handler):
		"""Handle input from keyboard and gamepad"""
		# Lock mouse on first input
		if not self.looking:
			input_handler.set_mouse_locked(True)
			self.looking = True

		# Camera orbiting (handles both mouse and gamepad right stick)
		self.camera.handle_input(input_handler)

		# Running (keyboard)
		self.is_running = input_handler.is_key_pressed('shift')

		# Jump - keyboard or gamepad A button
		jump_pressed = input_handler.is_key_down('space')
		if input_handler.is_gamepad_available():
			jump_pressed = jump_pressed or input_handler.is_gamepad_button_pressed('a')

		if jump_pressed and self.is_grounded:
			self.velocity.z = self.jump_force
			self.is_grounded = False

	def update(self, dt):
		"""Update player"""
		if not self.looking:
			if not self.is_grounded:
				self.velocity.z += self.gravity * dt
			self._slide_move(dt)
			self._check_ground()
			self.camera.update(dt)
			return

		input_handler = self.engine.input_handler

		# Get input direction from keyboard
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

		# Add gamepad left stick input
		if input_handler.is_gamepad_available():
			stick_x, stick_y = input_handler.get_left_stick()
			move_x += stick_x
			move_y += stick_y  # Stick up = negative Y = forward

		# Clamp combined input
		move_len = math.sqrt(move_x * move_x + move_y * move_y)
		if move_len > 1.0:
			move_x /= move_len
			move_y /= move_len

		self.is_moving = abs(move_x) > 0.01 or abs(move_y) > 0.01

		# Convert to world direction based on CAMERA heading
		heading_rad = math.radians(self.camera.heading)
		forward = Vec3(-math.sin(heading_rad), math.cos(heading_rad), 0)
		right = Vec3(math.cos(heading_rad), math.sin(heading_rad), 0)

		wish_dir = forward * move_y + right * move_x
		wish_speed = self.run_speed if self.is_running else self.walk_speed

		if self.is_grounded:
			# Friction
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

				# Rotate actor to face movement direction (flipped for model orientation)
				target_heading = math.degrees(math.atan2(wish_dir.x, -wish_dir.y))
				current_h = self.actor.actor.getH()

				# Smooth rotation
				diff = target_heading - current_h
				while diff > 180:
					diff -= 360
				while diff < -180:
					diff += 360

				rotation_speed = 10.0
				new_h = current_h + diff * rotation_speed * dt
				self.actor.actor.setH(new_h)
		else:
			# Gravity
			self.velocity.z += self.gravity * dt

		# Animation
		if not self.is_grounded:
			self._play_anim('pounce', loop=False)
		elif self.is_moving:
			self._play_anim('walk', loop=True)
		else:
			self._play_anim('idle', loop=True)

		# Move with collision
		self._slide_move(dt)

		# Ground check
		self._check_ground()

		# Debug
		self._update_debug_hitbox()

		# Update camera
		self.camera.update(dt)

	def reset(self):
		"""Reset to initial position"""
		self.position = list(self.initial_position)
		self._heading = self.initial_heading
		self.velocity = Vec3(0, 0, 0)
		self.is_grounded = False

		self.node.setPos(*self.position)
		self.body_np.setPos(self.position[0], self.position[1], self.position[2] + self.height / 2)

	def destroy(self):
		"""Clean up"""
		if self._debug_hitbox:
			self._debug_hitbox.removeNode()

		if hasattr(self, '_debug_raycast') and self._debug_raycast:
			self._debug_raycast.removeNode()

		if self.body:
			self.physics.removeRigidBody(self.body)

		if self.body_np:
			self.body_np.removeNode()

		if self.actor:
			self.actor.destroy()