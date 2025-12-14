from engine.actor_object import ActorObject

class CreatureEntity(ActorObject):
	"""
	Base class for animated creatures/enemies.

	Provides common creature functionality:
	- State machine (idle, walk, attack, etc.)
	- Animation state management
	- Basic AI hooks

	Override in subclasses for specific behavior.
	"""

	# Common states
	STATE_IDLE = 'idle'
	STATE_WALK = 'walk'
	STATE_RUN = 'run'
	STATE_ATTACK = 'attack'
	STATE_HURT = 'hurt'
	STATE_DEATH = 'death'

	def __init__(self, engine, model_path, position=None, rotation=None, scale=1.0,
							 collision_enabled=False, collision_size=None, mass=0.0):
		super().__init__(engine, model_path, position, rotation, scale,
										 collision_enabled, collision_size, mass)

		self.state = self.STATE_IDLE
		self.previous_state = None
		self.state_time = 0.0

		# Animation mapping - override in subclass
		# Maps states to animation names
		self.anim_map = {
			self.STATE_IDLE: 'idle',
			self.STATE_WALK: 'walk',
			self.STATE_RUN: 'run',
			self.STATE_ATTACK: 'attack',
			self.STATE_HURT: 'hurt',
			self.STATE_DEATH: 'death',
		}

		# Blend time for animation transitions (seconds)
		self.blend_time = 0.2

		# Stats - override in subclass
		self.health = 100
		self.max_health = 100
		self.speed = 1.0
		self.is_alive = True

	def set_state(self, new_state, force=False):
		"""Change creature state and play corresponding animation"""
		if new_state == self.state and not force:
			return

		self.previous_state = self.state
		self.state = new_state
		self.state_time = 0.0

		# Play animation for new state with blending
		anim_name = self.anim_map.get(new_state)
		if anim_name:
			if new_state in [self.STATE_IDLE, self.STATE_WALK, self.STATE_RUN]:
				self.loop(anim_name, blend_time=self.blend_time)
			else:
				self.play(anim_name, blend_time=self.blend_time)

		self.on_state_enter(new_state)

	def on_state_enter(self, state):
		"""Called when entering a new state - override in subclass"""
		pass

	def on_state_exit(self, state):
		"""Called when exiting a state - override in subclass"""
		pass

	def take_damage(self, amount):
		"""Apply damage to creature"""
		if not self.is_alive:
			return

		self.health -= amount

		if self.health <= 0:
			self.health = 0
			self.die()
		else:
			self.set_state(self.STATE_HURT)

	def heal(self, amount):
		"""Heal creature"""
		self.health = min(self.health + amount, self.max_health)

	def die(self):
		"""Handle creature death"""
		self.is_alive = False
		self.set_state(self.STATE_DEATH)

	def update(self, dt):
		"""Per-frame update - override in subclass"""
		self.state_time += dt
		self.update_ai(dt)

	def update_ai(self, dt):
		"""AI behavior - override in subclass"""
		pass