from direct.showbase.ShowBase import ShowBase
from direct.gui.OnscreenImage import OnscreenImage
from panda3d.core import TransparencyAttrib

base: ShowBase

class GUIContainer:
	"""
	Container for grouping GUI elements.

	Usage:
		container = GUIContainer(gui_handler.bottom_left, align='bottom_left')
		container.add_image('shield', 'shield.png', x=0, y=0, scale=0.05)
		container.add_image('health', '100.png', x=0.1, y=0, scale=0.03)
	"""

	def __init__(self, anchor, align='bottom_left', offset=(0, 0)):
		"""
		anchor: NodePath to parent to (e.g., gui_handler.bottom_left)
		align: Which corner of container aligns to anchor
		       'bottom_left', 'bottom_right', 'top_left', 'top_right',
		       'center', 'bottom_center', 'top_center', 'middle_left', 'middle_right'
		offset: (x, z) offset from anchor point
		"""
		self.anchor = anchor
		self.align = align
		self.elements = {}

		self.root = anchor.attachNewNode('gui_container')
		self.root.setPos(offset[0], 0, offset[1])

	def add_image(self, name, filepath, x=0, y=0, scale=0.1):
		"""
		Add an image to the container.
		x, y: Position relative to container origin (y is vertical in screen space)
		"""
		img = OnscreenImage(image=filepath, scale=scale)
		img.setTransparency(TransparencyAttrib.MAlpha)
		img.reparentTo(self.root)

		px, pz = self._align_offset(x, y)
		img.setPos(px, 0, pz)

		self.elements[name] = img
		return img

	def _align_offset(self, x, y):
		"""Convert x,y to proper position based on alignment"""
		if self.align == 'bottom_left':
			return (x, y)
		elif self.align == 'bottom_right':
			return (-x, y)
		elif self.align == 'top_left':
			return (x, -y)
		elif self.align == 'top_right':
			return (-x, -y)
		elif self.align == 'bottom_center':
			return (x, y)
		elif self.align == 'top_center':
			return (x, -y)
		elif self.align == 'middle_left':
			return (x, y)
		elif self.align == 'middle_right':
			return (-x, y)
		else:  # center
			return (x, y)

	def get(self, name):
		"""Get element by name"""
		return self.elements.get(name)

	def remove(self, name):
		"""Remove an element"""
		if name in self.elements:
			self.elements[name].destroy()
			del self.elements[name]

	def show(self):
		self.root.show()

	def hide(self):
		self.root.hide()

	def destroy(self):
		for elem in self.elements.values():
			elem.destroy()
		self.elements.clear()
		self.root.removeNode()