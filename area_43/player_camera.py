from engine.camera import Camera


class PlayerCamera(Camera):
	"""Camera controlled by Player - no direct input"""

	def __init__(self, engine, near_clip=0.1, far_clip=10000):
		super().__init__(engine, (0, 0, 0), (0, 0, 0), near_clip, far_clip)

	def handle_input(self, input_handler):
		pass

	def update(self, dt):
		pass