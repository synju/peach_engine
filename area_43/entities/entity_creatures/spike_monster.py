import math
from area_43.entities.entity_creatures.creature_entity import CreatureEntity
from engine.mesh_object import MeshObject
from panda3d.core import Vec3
from direct.showbase.ShowBase import ShowBase

base: ShowBase

class SpikeMonster(CreatureEntity):
	"""
	Spike Monster enemy with idle and jab animations.
	"""

	def __init__(self, engine, position=None, rotation=None, scale=1.0, collision_enabled=False, debug_mode=False):
		super().__init__(
			engine,
			model_path='entities/models/spike_monster.gltf',
			position=position,
			rotation=rotation,
			scale=scale,
			collision_enabled=collision_enabled,
			mass=0.0
		)

		# Load stationary base mesh (not parented to node, syncs position only)
		self.base_mesh = MeshObject(
			engine,
			name='spike_monster_base',
			model_path='entities/models/spike_monster_base.gltf',
			position=position
		)
		self.base_mesh.scale = 0.2

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
		self.attack_cooldown = 3.0  # Seconds between attacks
		self._attack_timer = 0.0
		self.turn_speed = 5.0  # Rotation speed (higher = faster turn)
		self.attack_alignment = 20  # Must be within this many degrees to attack

		# Target (usually the player)
		self.target = None

		# Debug
		self.debug_mode = debug_mode
		self.creature_radius = 0.5
		self._debug_circle = None

		# Expose damage bone for tracking spike tip
		self._damage_joint = self.actor.exposeJoint(None, "modelRoot", "Spike_Damage_Point")
		self.damage_radius = 0.01
		self.damage_sphere_offset = Vec3(0.0, 0.0, -0.05)  # Offset from bone position
		self._has_hit_player = False  # Prevent multiple hits per attack
		self._debug_damage_sphere = None

		# Hitboxes
		self.setup_hitboxes()

		# Start in idle
		self.set_state(self.STATE_IDLE, force=True)

	def setup_hitboxes(self):
		# Find and store hitbox meshes from model
		self.hitboxes = []
		hitbox_nodes = self.actor.findAllMatches("**/hitbox_*")

		for i in range(hitbox_nodes.getNumPaths()):
			hb = hitbox_nodes.getPath(i)
			name = hb.getName()

			# Damage multiplier based on name
			if "tip" in name:
				multiplier = 2.0
			elif "head" in name:
				multiplier = 1.5
			else:
				multiplier = 1.0

			self.hitboxes.append({
				"name": name,
				"node": hb,
				"multiplier": multiplier
			})

			# Hide the hitbox mesh (invisible but still trackable)
			hb.hide()

		self._debug_hitbox_visuals = []

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
		"""Orient to face the target smoothly (rotates actor only, not base)"""
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

		# Get current heading (from actor, not node)
		current_heading = self.actor.getH()

		# Find shortest rotation direction
		diff = target_heading - current_heading
		while diff > 180:
			diff -= 360
		while diff < -180:
			diff += 360

		# Smooth rotation (rotate actor only)
		rotation_amount = self.turn_speed * dt * 60  # Scale by dt
		if abs(diff) < rotation_amount:
			self.actor.setH(target_heading)
		else:
			self.actor.setH(current_heading + rotation_amount * (1 if diff > 0 else -1))

	def is_facing_target(self):
		"""Check if facing target within attack_alignment degrees"""
		target_pos = self._get_target_position()
		if target_pos is None:
			return False

		my_pos = self.node.getPos()
		direction = target_pos - my_pos
		direction.z = 0

		if direction.length() < 0.01:
			return True

		target_heading = math.degrees(math.atan2(direction.x, -direction.y))
		current_heading = self.actor.getH()

		diff = target_heading - current_heading
		while diff > 180:
			diff -= 360
		while diff < -180:
			diff += 360

		return abs(diff) <= self.attack_alignment

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
			self._has_hit_player = False  # Reset hit flag for new attack
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

		# Inside attack range - try to attack if facing target
		if distance <= self.attack_range:
			if self._attack_timer <= 0 and self.state != self.STATE_ATTACK and self.is_facing_target():
				self.attack()
		else:
			# Inside tracking but outside attack range - attack_idle
			if self.state not in [self.STATE_ATTACK, 'attack_idle']:
				self.set_state('attack_idle')

	def on_state_enter(self, state):
		"""Handle state-specific setup"""
		if state == self.STATE_ATTACK:
			self._has_hit_player = False

	def get_damage_sphere_pos(self):
		"""Get world position of damage sphere (spike tip + offset)"""
		if self._damage_joint:
			# Get bone position and apply local offset
			joint_pos = self._damage_joint.getPos(base.render)
			# Transform offset by bone's rotation
			offset_world = base.render.getRelativeVector(self._damage_joint, self.damage_sphere_offset)
			return joint_pos + offset_world
		return self.node.getPos()

	def check_hit(self, attack_pos, attack_radius=0.1):
		"""Check if an attack hits any hitbox mesh"""
		for hb in self.hitboxes:
			node = hb["node"]

			# Get tight bounds in world space
			bounds = node.getTightBounds(base.render)
			if not bounds:
				continue

			min_pt, max_pt = bounds
			center = (min_pt + max_pt) / 2

			# Approximate as sphere using half the diagonal
			size = max_pt - min_pt
			approx_radius = size.length() / 2

			# Check sphere intersection
			dist = (attack_pos - center).length()
			if dist < (approx_radius + attack_radius):
				return {"name": hb["name"], "multiplier": hb["multiplier"], "pos": center}

		return None

	def take_damage(self, amount, multiplier=1.0):
		"""Take damage with optional multiplier"""
		damage = amount * multiplier
		self.health -= damage
		if self.health <= 0:
			self.health = 0
			self.on_death()
		return damage

	def on_death(self):
		"""Called when health reaches 0"""
		pass

	def _intersects_player(self):
		"""Check if damage sphere intersects player's capsule"""
		if not self.target:
			return False

		target_pos = self._get_target_position()
		if target_pos is None:
			return False

		sphere_pos = self.get_damage_sphere_pos()

		# Player capsule dimensions
		player_radius = getattr(self.target, 'radius', 0.3)
		player_height = getattr(self.target, '_current_height', 1.8)

		# Capsule axis from bottom to top
		capsule_bottom = Vec3(target_pos.x, target_pos.y, target_pos.z + player_radius)
		capsule_top = Vec3(target_pos.x, target_pos.y, target_pos.z + player_height - player_radius)

		# Find closest point on capsule axis to sphere center
		axis = capsule_top - capsule_bottom
		axis_len = axis.length()
		if axis_len < 0.01:
			closest = capsule_bottom
		else:
			axis_norm = axis / axis_len
			t = (sphere_pos - capsule_bottom).dot(axis_norm)
			t = max(0, min(axis_len, t))
			closest = capsule_bottom + axis_norm * t

		# Check distance
		dist = (sphere_pos - closest).length()
		return dist < (player_radius + self.damage_radius)

	def update(self, dt):
		"""Per-frame update"""
		super().update(dt)

		# Sync base mesh position (not rotation)
		if self.base_mesh:
			pos = self.node.getPos()
			self.base_mesh.position = [pos.x, pos.y, pos.z]

		# Check for damage during attack
		if self.state == self.STATE_ATTACK and not self._has_hit_player:
			if self._intersects_player():
				self._has_hit_player = True
				if hasattr(self.target, 'take_damage'):
					self.target.take_damage(self.attack_damage)

		self._update_debug()

		# Return to attack_idle after jab finishes
		if self.state == self.STATE_ATTACK:
			duration = self.get_duration('jab')
			if duration > 0 and self.state_time >= duration:
				self.set_state('attack_idle')

	def _create_debug_circle(self):
		from panda3d.core import GeomVertexFormat, GeomVertexData, GeomVertexWriter
		from panda3d.core import Geom, GeomLines, GeomNode, NodePath

		segments = 32
		vdata = GeomVertexData('circle', GeomVertexFormat.get_v3c4(), Geom.UHStatic)
		vdata.setNumRows(segments)
		vertex = GeomVertexWriter(vdata, 'vertex')
		color = GeomVertexWriter(vdata, 'color')

		for i in range(segments):
			angle = (i / segments) * math.pi * 2
			vertex.addData3(math.cos(angle) * self.creature_radius, math.sin(angle) * self.creature_radius, 0)
			color.addData4(1, 1, 0, 1)

		lines = GeomLines(Geom.UHStatic)
		for i in range(segments):
			lines.addVertices(i, (i + 1) % segments)
			lines.closePrimitive()

		geom = Geom(vdata)
		geom.addPrimitive(lines)
		node = GeomNode('radius')
		node.addGeom(geom)
		np = NodePath(node)
		np.setLightOff()
		np.setRenderModeThickness(2)
		np.setBin('fixed', 100)
		np.reparentTo(base.render)
		return np

	def _create_debug_damage_sphere(self):
		"""Create wireframe sphere for damage detection visualization"""
		from panda3d.core import GeomVertexFormat, GeomVertexData, GeomVertexWriter
		from panda3d.core import Geom, GeomLines, GeomNode, NodePath

		segments = 16
		radius = self.damage_radius

		vdata = GeomVertexData('sphere', GeomVertexFormat.get_v3c4(), Geom.UHStatic)
		vdata.setNumRows(segments * 3)
		vertex = GeomVertexWriter(vdata, 'vertex')
		color = GeomVertexWriter(vdata, 'color')

		# XY circle (horizontal)
		for i in range(segments):
			angle = (i / segments) * math.pi * 2
			vertex.addData3(math.cos(angle) * radius, math.sin(angle) * radius, 0)
			color.addData4(1, 0, 0, 1)  # Red

		# XZ circle (vertical, front)
		for i in range(segments):
			angle = (i / segments) * math.pi * 2
			vertex.addData3(math.cos(angle) * radius, 0, math.sin(angle) * radius)
			color.addData4(1, 0, 0, 1)

		# YZ circle (vertical, side)
		for i in range(segments):
			angle = (i / segments) * math.pi * 2
			vertex.addData3(0, math.cos(angle) * radius, math.sin(angle) * radius)
			color.addData4(1, 0, 0, 1)

		lines = GeomLines(Geom.UHStatic)
		for circle in range(3):
			offset = circle * segments
			for i in range(segments):
				lines.addVertices(offset + i, offset + (i + 1) % segments)
				lines.closePrimitive()

		geom = Geom(vdata)
		geom.addPrimitive(lines)
		node = GeomNode('damage_sphere')
		node.addGeom(geom)
		np = NodePath(node)
		np.setLightOff()
		np.setRenderModeThickness(2)
		np.setBin('fixed', 100)
		np.setDepthTest(False)
		np.setDepthWrite(False)
		np.reparentTo(base.render)
		return np

	def _update_debug(self):
		if self.debug_mode:
			if not self._debug_circle:
				self._debug_circle = self._create_debug_circle()
			pos = self.node.getPos()
			self._debug_circle.setPos(pos.x, pos.y, pos.z)

			# Damage sphere follows spike tip
			if not self._debug_damage_sphere:
				self._debug_damage_sphere = self._create_debug_damage_sphere()
			sphere_pos = self.get_damage_sphere_pos()
			self._debug_damage_sphere.setPos(sphere_pos)

			# Show hitbox meshes in debug mode
			for hb in self.hitboxes:
				hb["node"].show()
		else:
			if self._debug_circle:
				self._debug_circle.removeNode()
				self._debug_circle = None
			if self._debug_damage_sphere:
				self._debug_damage_sphere.removeNode()
				self._debug_damage_sphere = None
			# Hide hitbox meshes
			for hb in self.hitboxes:
				hb["node"].hide()

	def destroy(self):
		if self._debug_circle:
			self._debug_circle.removeNode()
		if self._debug_damage_sphere:
			self._debug_damage_sphere.removeNode()
		if self.base_mesh:
			self.base_mesh.destroy()
		super().destroy()