class CreatureHandler:
	"""
	Manages creature entities in a scene.

	Usage:
		self.creatures = CreatureHandler()
		self.creatures.add(spider)  # id 0
		self.creatures.add(monster) # id 1

		# Update all
		self.creatures.update(dt)

		# Access
		spider = self.creatures.get(0)
		monster = self.creatures.get(1)

		# Cleanup
		self.creatures.destroy()
	"""

	def __init__(self):
		self._creatures = []

	def add(self, creature):
		"""Add a creature. Returns its ID (index)."""
		creature_id = len(self._creatures)
		self._creatures.append(creature)
		return creature_id

	def remove(self, creature_id):
		"""Remove and destroy a creature by ID. Sets slot to None."""
		if 0 <= creature_id < len(self._creatures):
			creature = self._creatures[creature_id]
			if creature:
				creature.destroy()
				self._creatures[creature_id] = None

	def get(self, creature_id):
		"""Get creature by ID."""
		if 0 <= creature_id < len(self._creatures):
			return self._creatures[creature_id]
		return None

	def get_all(self):
		"""Get all creatures (excludes removed)."""
		return [c for c in self._creatures if c is not None]

	def set_target_all(self, target):
		"""Set target for all creatures."""
		for creature in self._creatures:
			if creature and hasattr(creature, 'set_target'):
				creature.set_target(target)

	def update(self, dt):
		"""Update all creatures."""
		for creature in self._creatures:
			if creature:
				creature.update(dt)

	def destroy(self):
		"""Destroy all creatures."""
		for creature in self._creatures:
			if creature:
				creature.destroy()
		self._creatures.clear()

	def __len__(self):
		return len([c for c in self._creatures if c is not None])

	def __iter__(self):
		return iter(c for c in self._creatures if c is not None)

	def __getitem__(self, creature_id):
		return self.get(creature_id)