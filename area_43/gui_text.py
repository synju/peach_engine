import json
from direct.showbase.ShowBase import ShowBase
from direct.gui.OnscreenImage import OnscreenImage
from panda3d.core import TransparencyAttrib, NodePath, CardMaker, Texture, Filename

base: ShowBase

class GUIText:
	"""
	Renders text using a font grid sprite sheet.

	Usage:
		text = GUIText('assets/fonts/quantico.png', 'assets/fonts/font_grid.json')
		text.set_text('100')
		text.reparentTo(some_node)
		text.setPos(0.1, 0, 0)
	"""

	def __init__(self, image_path, json_path, scale=0.05, spacing=0.8):
		"""
		image_path: Path to font grid image
		json_path: Path to font grid JSON
		scale: Size of each character
		spacing: Space between characters (multiplier of scale)
		"""
		self.scale = scale
		self.spacing = spacing
		self.characters = []

		# Load font data
		with open(json_path, 'r') as f:
			self.font_data = json.load(f)

		# Convert path for Panda3D (needs forward slashes)
		panda_path = Filename.fromOsSpecific(image_path).getFullpath()

		# Load texture
		self.texture = base.loader.loadTexture(panda_path)
		self.texture.setMagfilter(Texture.FTNearest)
		self.texture.setMinfilter(Texture.FTNearest)

		# Calculate grid info
		self.cell_width = self.font_data['cell_width']
		self.cell_height = self.font_data['cell_height']
		self.columns = self.font_data['columns']
		self.rows = self.font_data['rows']

		# Image dimensions
		self.img_width = self.cell_width * self.columns
		self.img_height = self.cell_height * self.rows

		# Build character to grid position map
		self.char_map = {}
		for row_idx, row in enumerate(self.font_data['characters_per_row']):
			for col_idx, char in enumerate(row):
				self.char_map[char] = (col_idx, row_idx)

		# Root node
		self.root = NodePath('gui_text')
		self._char_nodes = []

	def _get_uv(self, char):
		"""Get UV coordinates for a character"""
		if char not in self.char_map:
			char = ' '

		col, row = self.char_map[char]

		u_left = col * self.cell_width / self.img_width
		u_right = (col + 1) * self.cell_width / self.img_width
		v_top = 1.0 - (row * self.cell_height / self.img_height)
		v_bottom = 1.0 - ((row + 1) * self.cell_height / self.img_height)

		return u_left, u_right, v_bottom, v_top

	def set_text(self, text):
		"""Update displayed text"""
		# Clear existing
		for node in self._char_nodes:
			node.removeNode()
		self._char_nodes.clear()

		# Create new characters
		x_offset = 0
		for char in text:
			u_left, u_right, v_bottom, v_top = self._get_uv(char)

			cm = CardMaker(f'char_{char}')
			cm.setFrame(-0.5, 0.5, -0.5, 0.5)
			cm.setUvRange((u_left, v_bottom), (u_right, v_top))

			card = self.root.attachNewNode(cm.generate())
			card.setTexture(self.texture)
			card.setTransparency(TransparencyAttrib.MAlpha)
			card.setScale(self.scale)
			card.setPos(x_offset, 0, 0)

			self._char_nodes.append(card)
			x_offset += self.scale * self.spacing

	def reparentTo(self, parent):
		self.root.reparentTo(parent)

	def setPos(self, x, y, z):
		self.root.setPos(x, y, z)

	def show(self):
		self.root.show()

	def hide(self):
		self.root.hide()

	def destroy(self):
		for node in self._char_nodes:
			node.removeNode()
		self._char_nodes.clear()
		self.root.removeNode()