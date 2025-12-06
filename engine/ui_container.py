from direct.showbase.ShowBase import ShowBase

# Global created by ShowBase
base: ShowBase

class UIContainer:
	"""Container for UI elements - repositions on window resize"""

	def __init__(self):
		self.elements = []
		self.visible = True
		self._last_window_size = (0, 0)

	def add(self, element):
		"""Add an element to the container"""
		self.elements.append(element)
		return element

	def set_visible(self, visible):
		"""Show/hide all elements"""
		self.visible = visible
		for element in self.elements:
			element.set_visible(visible)

	def update(self):
		"""Check for window resize and reposition elements"""
		current_size = (base.win.getXSize(), base.win.getYSize())

		if current_size != self._last_window_size:
			self._last_window_size = current_size
			for element in self.elements:
				element.update_position()

	def destroy(self):
		"""Clean up all elements"""
		for element in self.elements:
			element.destroy()
		self.elements.clear()