import math
from area_43.entities.entity_creatures.creature_entity import CreatureEntity
from panda3d.core import Vec3, BitMask32
from direct.showbase.ShowBase import ShowBase

base: ShowBase

class FaceSpider(CreatureEntity):
	"""
	Face Spider enemy that chases and pounces on the player.

	Behaviors:
	- Idle when player is far away
	- Walk/chase when player enters detection radius
	- Pounce attack when close enough (leaps toward player)
	"""

	def __init__(self, engine, position=None, rotation=None, scale=1.0,
							 collision_enabled=False):
		super().__init__(
			engine,
			model_path='entities/models/face_spider.gltf',
			position=position,
			rotation=rotation,
			scale=scale,
			collision_enabled=collision_enabled,
			mass=0.0
		)

		# Animation map
		self.anim_map = {
			self.STATE_IDLE: 'idle',
			self.STATE_WALK: 'walk',
			self.STATE_ATTACK: 'pounce',
		}

		# Animation blend time
		self.blend_time = 0.2
		self.walk_anim_speed = 1.5  # Speed multiplier for walk animation

		# AI ranges
		self.idle_radius = 10.0  # Start chasing at this distance
		self.pounce_radius = 4.0  # Pounce when this close
		self.pounce_distance = 4.0  # How far the pounce travels
		self.pounce_cooldown = 2.0  # Time between pounces
		self._pounce_timer = 0.0
		self.can_pounce = True  # Set False to disable pouncing

		# Wander behavior
		self._wander_target = None
		self._wander_idle_timer = 0.0
		self._wander_radius_min = 3.0  # Min distance to wander
		self._wander_radius_max = 10.0  # Max distance to wander
		self._is_wandering = False

		# Movement
		self.walk_speed = 5.0
		self.turn_speed = 10.0

		# Pounce state
		self._is_pouncing = False
		self._pounce_start_pos = None
		self._pounce_target_pos = None
		self._pounce_direction = None
		self._pounce_progress = 0.0
		self._pounce_duration = 0.4  # How long the pounce movement takes
		self._pounce_arc_height = 1.5  # How high the jump goes
		self._pounce_airborne = False  # True when in the air
		self._pounce_falling = False  # True when hit wall and falling
		self._pounce_velocity_z = 0.0  # Vertical velocity when falling
		self._pounce_frame = 15  # Frame to hold while airborne

		# Physics
		self._gravity = 20.0
		self._ground_offset = 0.01  # Height above ground
		self._velocity_z = 0.0  # Vertical velocity for gravity

		# Target
		self.target = None

		# Start idle
		self.set_state(self.STATE_IDLE, force=True)

	def set_target(self, target):
		"""Set the target to chase"""
		self.target = target

	def _get_target_position(self):
		"""Get target position as Vec3"""
		if not self.target:
			return None
		if hasattr(self.target, '_position'):
			return Vec3(*self.target._position)
		if hasattr(self.target, 'node') and self.target.node:
			return self.target.node.getPos()
		if hasattr(self.target, 'getPos'):
			return self.target.getPos()
		return None

	def get_distance_to_target(self):
		"""Get horizontal distance to target"""
		if not self.target:
			return float('inf')

		my_pos = self.node.getPos()
		target_pos = self._get_target_position()

		if target_pos is None:
			return float('inf')

		# Horizontal distance only
		diff = target_pos - my_pos
		diff.z = 0
		return diff.length()

	def _raycast_down(self, pos, max_dist=100.0):
		"""Raycast down from position, return hit point or None"""
		from_pos = Vec3(pos.x, pos.y, pos.z + 1.0)
		to_pos = Vec3(pos.x, pos.y, pos.z - max_dist)

		result = self.engine.physics.rayTestClosest(from_pos, to_pos)
		if result.hasHit():
			return result.getHitPos()
		return None

	def _raycast_forward(self, from_pos, direction, dist):
		"""Raycast forward, return True if hit wall"""
		to_pos = from_pos + direction * dist
		to_pos.z = from_pos.z + 0.5  # Check at body height
		from_check = Vec3(from_pos.x, from_pos.y, from_pos.z + 0.5)

		result = self.engine.physics.rayTestClosest(from_check, to_pos)
		if result.hasHit():
			hit_pos = result.getHitPos()
			hit_normal = result.getHitNormal()
			# Wall = mostly vertical normal
			if abs(hit_normal.z) < 0.5:
				return True, hit_pos
		return False, None

	def _pick_wander_spot(self):
		"""Pick a random spot within wander radius that has ground"""
		import random
		my_pos = self.node.getPos()

		for _ in range(10):  # Try up to 10 times
			angle = random.uniform(0, math.pi * 2)
			dist = random.uniform(self._wander_radius_min, self._wander_radius_max)

			new_x = my_pos.x + math.cos(angle) * dist
			new_y = my_pos.y + math.sin(angle) * dist

			test_pos = Vec3(new_x, new_y, my_pos.z)

			# Check ground exists
			ground = self._raycast_down(test_pos)
			if not ground:
				continue

			# Check no wall in the way
			direction = test_pos - my_pos
			direction.z = 0
			direction.normalize()
			hit_wall, _ = self._raycast_forward(my_pos, direction, dist)
			if hit_wall:
				continue

			return Vec3(new_x, new_y, ground.z + self._ground_offset)

		return None

	def _face_position(self, target_pos, dt):
		"""Smoothly rotate to face a position"""
		my_pos = self.node.getPos()
		direction = target_pos - my_pos
		direction.z = 0

		if direction.length() < 0.01:
			return

		target_heading = math.degrees(math.atan2(direction.x, -direction.y))
		current_heading = self.node.getH()

		diff = target_heading - current_heading
		while diff > 180:
			diff -= 360
		while diff < -180:
			diff += 360

		rotation_amount = self.turn_speed * dt * 60
		if abs(diff) < rotation_amount:
			self.node.setH(target_heading)
		else:
			self.node.setH(current_heading + rotation_amount * (1 if diff > 0 else -1))

	def _move_toward_position(self, target_pos, dt):
		"""Move toward a specific position"""
		my_pos = self.node.getPos()
		direction = target_pos - my_pos
		direction.z = 0

		dist = direction.length()
		if dist < 0.2:
			return True  # Reached

		direction.normalize()

		# Check for wall ahead
		hit_wall, _ = self._raycast_forward(my_pos, direction, self.walk_speed * dt + 0.3)
		if hit_wall:
			return True  # Blocked, stop

		move = direction * self.walk_speed * dt
		new_pos = my_pos + move

		# Check for ground
		ground = self._raycast_down(new_pos)
		if not ground:
			return True  # No ground, stop

		new_pos.z = ground.z + self._ground_offset
		self.node.setPos(new_pos)
		return False  # Still moving

	def face_target(self, dt):
		"""Smoothly rotate to face target"""
		target_pos = self._get_target_position()
		if target_pos is None:
			return

		my_pos = self.node.getPos()
		direction = target_pos - my_pos
		direction.z = 0

		if direction.length() < 0.01:
			return

		target_heading = math.degrees(math.atan2(direction.x, -direction.y))
		current_heading = self.node.getH()

		diff = target_heading - current_heading
		while diff > 180:
			diff -= 360
		while diff < -180:
			diff += 360

		rotation_amount = self.turn_speed * dt * 60
		if abs(diff) < rotation_amount:
			self.node.setH(target_heading)
		else:
			self.node.setH(current_heading + rotation_amount * (1 if diff > 0 else -1))

	def move_toward_target(self, dt, min_distance=None):
		"""Move toward the target while walking"""
		target_pos = self._get_target_position()
		if target_pos is None:
			return

		my_pos = self.node.getPos()
		direction = target_pos - my_pos
		direction.z = 0

		dist = direction.length()
		if dist < 0.1:
			return

		# Use min_distance if provided, otherwise pounce_radius
		stop_distance = min_distance if min_distance is not None else self.pounce_radius
		if dist <= stop_distance:
			return

		direction.normalize()

		# Check for wall ahead
		hit_wall, _ = self._raycast_forward(my_pos, direction, self.walk_speed * dt + 0.3)
		if hit_wall:
			return

		move = direction * self.walk_speed * dt
		new_pos = my_pos + move

		# Check for ground at new position
		ground = self._raycast_down(new_pos)
		if not ground:
			# No ground ahead - try to jump across
			if self.can_pounce and self._pounce_timer <= 0:
				self.start_pounce()
			return

		new_pos.z = ground.z + self._ground_offset
		self.node.setPos(new_pos)

	def start_pounce(self):
		"""Begin a pounce attack toward the player"""
		if self._pounce_timer > 0 or self._is_pouncing:
			return

		target_pos = self._get_target_position()
		if target_pos is None:
			return

		self._is_pouncing = True
		self._pounce_airborne = False
		self._pounce_falling = False
		self._pounce_start_pos = Vec3(self.node.getPos())

		# Calculate pounce direction
		direction = target_pos - self._pounce_start_pos
		direction.z = 0
		dist = direction.length()

		if dist > 0.01:
			direction.normalize()
			self._pounce_direction = direction
			travel = min(self.pounce_distance, dist)
			self._pounce_target_pos = self._pounce_start_pos + direction * travel
			self._pounce_target_pos.z = self._pounce_start_pos.z
		else:
			self._pounce_direction = Vec3(0, 1, 0)
			self._pounce_target_pos = Vec3(self._pounce_start_pos)

		self._pounce_progress = 0.0
		self._pounce_velocity_z = 0.0
		self._velocity_z = 0.0  # Reset gravity velocity
		self.set_state(self.STATE_ATTACK, blend_time=0.05)
		self._pounce_timer = self.pounce_cooldown

	def update_pounce(self, dt):
		"""Update pounce movement - arc through the air with collision"""
		if not self._is_pouncing:
			return

		my_pos = self.node.getPos()

		# If falling after hitting wall or no ground
		if self._pounce_falling:
			self._pounce_velocity_z -= self._gravity * dt
			new_z = my_pos.z + self._pounce_velocity_z * dt

			# Check ground
			ground = self._raycast_down(my_pos)
			if ground and new_z <= ground.z + self._ground_offset:
				# Landed
				my_pos.z = ground.z + self._ground_offset
				self.node.setPos(my_pos)
				self._land()
				return

			my_pos.z = new_z
			self.node.setPos(my_pos)
			return

		# Normal pounce arc
		self._pounce_progress += dt / self._pounce_duration
		t = min(self._pounce_progress, 1.0)

		# Check if we're in the airborne phase (after frame 15 equivalent)
		# Roughly, airborne starts around 30% into the pounce
		if t > 0.3 and not self._pounce_airborne:
			self._pounce_airborne = True
			# Pose at frame 15 and hold
			self.actor.pose('pounce', self._pounce_frame)

		# Horizontal position
		new_pos = self._pounce_start_pos + (self._pounce_target_pos - self._pounce_start_pos) * t

		# Vertical arc
		arc_height = self._pounce_arc_height * math.sin(t * math.pi)
		base_z = self._pounce_start_pos.z

		# Check for ground at target position (for landing on different heights)
		if t > 0.5:
			ground = self._raycast_down(new_pos)
			if ground:
				# Interpolate toward ground level as we descend
				landing_z = ground.z + self._ground_offset
				descent_t = (t - 0.5) / 0.5  # 0 to 1 in second half
				base_z = self._pounce_start_pos.z + (landing_z - self._pounce_start_pos.z) * descent_t

		new_pos.z = base_z + arc_height

		# Check wall collision
		travel_this_frame = (self._pounce_target_pos - self._pounce_start_pos).length() * (dt / self._pounce_duration)
		hit_wall, hit_pos = self._raycast_forward(my_pos, self._pounce_direction, travel_this_frame + 0.3)

		if hit_wall:
			# Stop horizontal movement, start falling
			self._pounce_falling = True
			self._pounce_velocity_z = 0.0 # (default 2.0) Small upward bump like its bouncing off the wall slightly
			return

		self.node.setPos(new_pos)

		# Check if landed (pounce complete)
		if t >= 1.0:
			# Check for ground
			ground = self._raycast_down(new_pos)
			if ground and new_pos.z <= ground.z + self._ground_offset + 0.1:
				# Has ground - land
				new_pos.z = ground.z + self._ground_offset
				self.node.setPos(new_pos)
				self._land()
			else:
				# No ground - start falling
				self._pounce_falling = True
				self._pounce_velocity_z = 0.0

	def _land(self):
		"""Called when pounce lands (normal or after falling)"""
		self._is_pouncing = False
		self._pounce_airborne = False
		self._pounce_falling = False
		self._velocity_z = 0.0  # Reset gravity velocity

		# Resume animation from frame 15 to finish
		if self.actor:
			self.actor.play('pounce', fromFrame=self._pounce_frame)

	def set_state(self, new_state, force=False, blend_time=None):
		"""Change state and play animation"""
		# Skip if already in this state
		if new_state == self.state and not force:
			return

		self.previous_state = self.state
		self.state = new_state
		self.state_time = 0.0

		anim_name = self.anim_map.get(new_state)
		if anim_name and self.actor:
			if new_state in [self.STATE_IDLE, self.STATE_WALK]:
				self.actor.loop(anim_name)
				if new_state == self.STATE_WALK:
					self.actor.setPlayRate(self.walk_anim_speed, anim_name)
			else:
				self.actor.play(anim_name)

		self.on_state_enter(new_state)

	def on_state_enter(self, state):
		"""Called when entering a state"""
		if state == self.STATE_ATTACK:
			pass

	def _should_ignore_player(self):
		"""Check if player has creatures_ignore_player enabled"""
		try:
			player = self.engine.scene_handler.current_scene.player
			return getattr(player, 'creatures_ignore_player', False)
		except:
			return False

	def update_ai(self, dt):
		"""AI behavior - chase and pounce"""
		import random

		# Update pounce cooldown
		if self._pounce_timer > 0:
			self._pounce_timer -= dt

		# If mid-pounce, just update the jump
		if self._is_pouncing:
			self.update_pounce(dt)
			return

		# Apply gravity when not pouncing
		my_pos = self.node.getPos()
		ground = self._raycast_down(my_pos)
		if ground:
			ground_z = ground.z + self._ground_offset
			if my_pos.z > ground_z + 0.01:
				# Above ground - fall
				self._velocity_z -= self._gravity * dt
				my_pos.z += self._velocity_z * dt
				if my_pos.z <= ground_z:
					my_pos.z = ground_z
					self._velocity_z = 0.0
				self.node.setPos(my_pos)
			else:
				# On ground
				my_pos.z = ground_z
				self.node.setPos(my_pos)
				self._velocity_z = 0.0
		else:
			# No ground - fall into void
			self._velocity_z -= self._gravity * dt
			my_pos.z += self._velocity_z * dt
			self.node.setPos(my_pos)

		# Get distance to target
		distance = self.get_distance_to_target()

		# Inside range - chase/attack (unless ignoring player)
		if not self._should_ignore_player() and distance <= self.idle_radius:
			self._is_wandering = False
			self._wander_target = None

			# Face target
			self.face_target(dt)

			# Pouncing enabled
			if self.can_pounce:
				if distance <= self.pounce_radius:
					if self._pounce_timer <= 0 and self.state != self.STATE_ATTACK:
						self.start_pounce()
					elif self.state != self.STATE_IDLE and self.state != self.STATE_ATTACK:
						self.set_state(self.STATE_IDLE)
				else:
					if self.state != self.STATE_WALK:
						self.set_state(self.STATE_WALK)
					self.move_toward_target(dt)
			else:
				# Pouncing disabled - walk until 1 block away
				if distance > 1.0:
					if self.state != self.STATE_WALK:
						self.set_state(self.STATE_WALK)
					self.move_toward_target(dt, min_distance=1.0)
				else:
					if self.state != self.STATE_IDLE:
						self.set_state(self.STATE_IDLE)
			return

		# Outside range or ignoring player - wander behavior
		if self._is_wandering and self._wander_target:
			# Walking to wander spot
			self._face_position(self._wander_target, dt)
			reached = self._move_toward_position(self._wander_target, dt)

			if reached:
				# Arrived - start idle timer
				self._is_wandering = False
				self._wander_target = None
				self._wander_idle_timer = random.uniform(0.0, 2.0)
				if self.state != self.STATE_IDLE:
					self.set_state(self.STATE_IDLE)
		else:
			# Idling
			if self._wander_idle_timer > 0:
				self._wander_idle_timer -= dt
				if self.state != self.STATE_IDLE:
					self.set_state(self.STATE_IDLE)
			else:
				# Pick new wander spot
				spot = self._pick_wander_spot()
				if spot:
					self._wander_target = spot
					self._is_wandering = True
					if self.state != self.STATE_WALK:
						self.set_state(self.STATE_WALK)
				else:
					# Couldn't find spot, idle more
					self._wander_idle_timer = random.uniform(1.0, 4.0)
					if self.state != self.STATE_IDLE:
						self.set_state(self.STATE_IDLE)

	def update(self, dt):
		"""Per-frame update"""
		super().update(dt)

		# After pounce finishes, decide next state
		if self.state == self.STATE_ATTACK and not self._is_pouncing:
			duration = self.get_duration('pounce')
			if duration > 0 and self.state_time >= duration:
				distance = self.get_distance_to_target()
				if distance <= self.pounce_radius:
					# Close enough - idle while waiting for cooldown
					self.set_state(self.STATE_IDLE)
				elif distance <= self.idle_radius:
					# In chase range - walk toward target
					self.set_state(self.STATE_WALK)
				else:
					# Out of range - idle
					self.set_state(self.STATE_IDLE)