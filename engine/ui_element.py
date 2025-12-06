from panda3d.core import TextNode, CardMaker
from direct.showbase.ShowBase import ShowBase

# Global created by ShowBase
base: ShowBase

class UIElement:
	"""Base UI element using pixel2d - true pixel coordinates"""

	def __init__(self, anchor='top-left', offset_x=0, offset_y=0):
		self.anchor = anchor
		self.offset_x = offset_x
		self.offset_y = offset_y
		self.node = None
		self.visible = True

	def get_pixel_position(self):
		"""Get pixel position based on anchor + offset"""
		w = base.win.getXSize()
		h = base.win.getYSize()

		anchors = {
			'top-left': (0, 0),
			'top-center': (w // 2, 0),
			'top-right': (w, 0),
			'middle-left': (0, h // 2),
			'center': (w // 2, h // 2),
			'middle-right': (w, h // 2),
			'bottom-left': (0, h),
			'bottom-center': (w // 2, h),
			'bottom-right': (w, h),
		}

		ax, ay = anchors.get(self.anchor, (0, 0))
		return (ax + self.offset_x, ay + self.offset_y)

	def update_position(self):
		"""Update position in pixel2d space"""
		if self.node:
			px, py = self.get_pixel_position()
			self.node.setPos(px, 0, -py)

	def set_visible(self, visible):
		self.visible = visible
		if self.node:
			if visible:
				self.node.show()
			else:
				self.node.hide()

	def destroy(self):
		if self.node:
			self.node.removeNode()
			self.node = None

class UIText(UIElement):
	"""Text element using TextNode"""

	def __init__(self, text='', anchor='top-left', offset_x=0, offset_y=0,
							 size=16, text_color=(1, 1, 1, 1)):
		super().__init__(anchor, offset_x, offset_y)

		self.size = size

		self._text_node = TextNode('text')
		self._text_node.setText(text)
		self._text_node.setTextColor(*text_color)
		self._text_node.setAlign(TextNode.ACenter)

		self.node = base.pixel2d.attachNewNode(self._text_node)
		self.node.setScale(size)
		self.update_position()

	@property
	def text(self):
		return self._text_node.getText()

	@text.setter
	def text(self, value):
		self._text_node.setText(value)

class UIBox(UIElement):
	"""Box outline using 4 CardMaker quads, optionally with filled background"""

	def __init__(self, anchor='top-left', offset_x=0, offset_y=0,
							 width=80, height=30, box_color=(1, 1, 1, 1), thickness=1,
							 fill_color=None):
		super().__init__(anchor, offset_x, offset_y)

		self.width = width
		self.height = height
		self.box_color = box_color
		self.thickness = thickness
		self.fill_color = fill_color

		self.node = base.pixel2d.attachNewNode('box')

		# Create background fill first (so it's behind border)
		if fill_color is not None:
			self._create_fill()

		self._create_border()
		self.update_position()

	def _create_fill(self):
		"""Create filled background"""
		hw = self.width // 2
		hh = self.height // 2
		cm = CardMaker('fill')
		cm.setFrame(-hw, hw, -hh, hh)
		cm.setColor(*self.fill_color)
		self.node.attachNewNode(cm.generate())

	def _create_border(self):
		"""Create 4 lines as thin quads"""
		hw = self.width // 2
		hh = self.height // 2
		t = self.thickness

		# Top
		self._make_quad(-hw, hh, self.width, t)
		# Bottom
		self._make_quad(-hw, -hh, self.width, t)
		# Left
		self._make_quad(-hw, -hh, t, self.height)
		# Right
		self._make_quad(hw - t, -hh, t, self.height)

	def _make_quad(self, x, z, w, h):
		cm = CardMaker('border')
		cm.setFrame(0, w, 0, h)
		cm.setColor(*self.box_color)
		quad = self.node.attachNewNode(cm.generate())
		quad.setPos(x, 0, z)