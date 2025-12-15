import math
from area_43.entities.entity_creatures.creature_entity import CreatureEntity
from panda3d.core import Vec3
from direct.showbase.ShowBase import ShowBase

base: ShowBase

class SpikeMonster(CreatureEntity):
	"""
	Spike Monster enemy with idle and jab animations.
	"""

	def __init__(self, engine, position=None, rotation=None, scale=1.0,
							 collision_enabled=False):
		super().__init__(
			engine,
			model_path='entities/models/spike_monster.gltf',
			position=position,
			rotation=rotation,
			scale=scale,
			collision_enabled=collision_enabled,
			mass=0.0
		)

		# Map states to actual animation names in the GLTF
		self.anim_map = {
			self.STATE_IDLE: 'idle',
			'attack_idle': 'attack_idle',
			self.STATE_ATTACK: 'jab',
		}

		# Animation blend time (seconds)
		self.blend_time = 0.3

		# Stats
		self.health = 50
		self.max_health = 50
		self.attack_damage = 10

		# AI ranges
		self.orient_range = 4.5  # Start facing player at this distance
		self.attack_range = 1.8  # Attack when within this distance
		self.attack_cooldown = 0.2  # Seconds between attacks
		self._attack_timer = 0.0
		self.turn_speed = 5.0  # Rotation speed (higher = faster turn)

		# Target (usually the player)
		self.target = None

		# Start in idle
		self.set_state(self.STATE_IDLE, force=True)

	def set_target(self, target):
		"""Set the target to track (e.g., player)"""
		self.target = target

	def get_distance_to_target(self):
		"""Get distance to target"""
		if not self.target:
			return float('inf')

		my_pos = self.node.getPos()
		target_pos = self._get_target_position()

		if target_pos is None:
			return float('inf')

		return (my_pos - target_pos).length()

	def _get_target_position(self):
		"""Get the target's position as Vec3"""
		if not self.target:
			return None

		# Player class has _position list
		if hasattr(self.target, '_position'):
			return Vec3(*self.target._position)
		# Or a node
		if hasattr(self.target, 'node') and self.target.node:
			return self.target.node.getPos()
		# Or direct NodePath
		if hasattr(self.target, 'getPos'):
			return self.target.getPos()

		return None

	def face_target(self, dt):
		"""Orient to face the target smoothly"""
		target_pos = self._get_target_position()
		if target_pos is None:
			return

		# Get direction to target
		my_pos = self.node.getPos()
		direction = target_pos - my_pos
		direction.z = 0  # Keep level

		if direction.length() < 0.01:
			return

		# Calculate target heading (flipped for Blender model orientation)
		target_heading = math.degrees(math.atan2(direction.x, -direction.y))

		# Get current heading
		current_heading = self.node.getH()

		# Find shortest rotation direction
		diff = target_heading - current_heading
		while diff > 180:
			diff -= 360
		while diff < -180:
			diff += 360

		# Smooth rotation
		rotation_amount = self.turn_speed * dt * 60  # Scale by dt
		if abs(diff) < rotation_amount:
			self.node.setH(target_heading)
		else:
			self.node.setH(current_heading + rotation_amount * (1 if diff > 0 else -1))

	def set_state(self, new_state, force=False, blend_time=None):
		"""Change state and play animation"""
		if new_state == self.state and not force:
			return

		self.previous_state = self.state
		self.state = new_state
		self.state_time = 0.0

		anim_name = self.anim_map.get(new_state)
		if anim_name:
			blend = blend_time if blend_time is not None else self.blend_time

			# Loop idle states, play attack once
			if new_state in [self.STATE_IDLE, 'attack_idle']:
				self.loop(anim_name, blend_time=blend)
			else:
				self.play(anim_name, blend_time=blend)

		self.on_state_enter(new_state)

	def attack(self):
		"""Perform jab attack"""
		if self._attack_timer <= 0 and self.state != self.STATE_ATTACK:
			self.set_state(self.STATE_ATTACK, blend_time=0.1)
			self._attack_timer = self.attack_cooldown

	def _should_ignore_player(self):
		"""Check if player has creatures_ignore_player enabled"""
		try:
			player = self.engine.scene_handler.current_scene.player
			return getattr(player, 'creatures_ignore_player', False)
		except:
			return False

	def update_ai(self, dt):
		"""AI behavior based on distance to target"""
		# Check if player wants to be ignored
		if self._should_ignore_player():
			if self.state != self.STATE_IDLE:
				self.set_state(self.STATE_IDLE)
			return

		# Update cooldown
		if self._attack_timer > 0:
			self._attack_timer -= dt

		# Get distance to target
		distance = self.get_distance_to_target()

		# Outside tracking range - go to idle
		if distance > self.orient_range:
			if self.state != self.STATE_IDLE:
				self.set_state(self.STATE_IDLE)
			return

		# Inside tracking range - face target
		self.face_target(dt)

		# Inside attack range - try to attack
		if distance <= self.attack_range:
			if self._attack_timer <= 0 and self.state != self.STATE_ATTACK:
				self.attack()
		else:
			# Inside tracking but outside attack range - attack_idle
			if self.state not in [self.STATE_ATTACK, 'attack_idle']:
				self.set_state('attack_idle')

	def on_state_enter(self, state):
		"""Handle state-specific setup"""
		if state == self.STATE_ATTACK:
			# Could trigger damage/hitbox check here
			pass

	def update(self, dt):
		"""Per-frame update"""
		super().update(dt)

		# Return to attack_idle after jab finishes
		if self.state == self.STATE_ATTACK:
			duration = self.get_duration('jab')
			if duration > 0 and self.state_time >= duration:
				self.set_state('attack_idle')