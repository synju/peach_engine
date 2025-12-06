class Scene:
	"""Base scene class - extend this for your game scenes"""

	def __init__(self, engine, name='scene'):
		self.engine = engine
		self.name = name
		self.scene_handler = None

	# Lifecycle
	def on_enter(self):
		"""Called when scene becomes active"""
		pass

	def on_exit(self):
		"""Called when leaving the scene"""
		pass

	# Event handling
	def handle_input(self, input_handler):
		"""Override in subclass"""
		pass

	def update(self, dt):
		"""Override in subclass"""
		pass

	def render(self, renderer):
		"""Override in subclass"""
		pass

	def destroy(self):
		"""Clean up scene"""
		pass