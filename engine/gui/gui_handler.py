from direct.showbase.ShowBase import ShowBase
from panda3d.core import NodePath

base: ShowBase

class GUIHandler:
	"""
	GUI handler with 9 anchor points using aspect2d.

	Anchor points:
		top_left      top_center      top_right
		middle_left   middle_center   middle_right
		bottom_left   bottom_center   bottom_right

	Usage:
		engine.gui_handler.top_left      # Parent elements here
		engine.gui_handler.show()
		engine.gui_handler.hide()
	"""

	def __init__(self, engine):
		self.engine = engine
		self._visible = True

		# Root node for all GUI
		self.root = base.aspect2d.attachNewNode('gui_root')

		# Create 9 anchor points
		self.top_left = self.root.attachNewNode('top_left')
		self.top_center = self.root.attachNewNode('top_center')
		self.top_right = self.root.attachNewNode('top_right')

		self.middle_left = self.root.attachNewNode('middle_left')
		self.middle_center = self.root.attachNewNode('middle_center')
		self.middle_right = self.root.attachNewNode('middle_right')

		self.bottom_left = self.root.attachNewNode('bottom_left')
		self.bottom_center = self.root.attachNewNode('bottom_center')
		self.bottom_right = self.root.attachNewNode('bottom_right')

		# Position anchors
		self._update_anchors()

		# Listen for window resize
		base.accept('aspectRatioChanged', self._update_anchors)

	def _update_anchors(self):
		"""Update anchor positions based on aspect ratio"""
		ratio = base.getAspectRatio()

		# Top row
		self.top_left.setPos(-ratio, 0, 1)
		self.top_center.setPos(0, 0, 1)
		self.top_right.setPos(ratio, 0, 1)

		# Middle row
		self.middle_left.setPos(-ratio, 0, 0)
		self.middle_center.setPos(0, 0, 0)
		self.middle_right.setPos(ratio, 0, 0)

		# Bottom row
		self.bottom_left.setPos(-ratio, 0, -1)
		self.bottom_center.setPos(0, 0, -1)
		self.bottom_right.setPos(ratio, 0, -1)

	def get_anchor(self, name):
		"""Get anchor by name"""
		anchors = {
			'top_left': self.top_left,
			'top_center': self.top_center,
			'top_right': self.top_right,
			'middle_left': self.middle_left,
			'middle_center': self.middle_center,
			'middle_right': self.middle_right,
			'bottom_left': self.bottom_left,
			'bottom_center': self.bottom_center,
			'bottom_right': self.bottom_right,
		}
		return anchors.get(name)

	def show(self):
		"""Show all GUI elements"""
		self.root.show()
		self._visible = True

	def hide(self):
		"""Hide all GUI elements"""
		self.root.hide()
		self._visible = False

	def toggle(self):
		"""Toggle GUI visibility"""
		if self._visible:
			self.hide()
		else:
			self.show()

	@property
	def visible(self):
		return self._visible

	def destroy(self):
		"""Clean up"""
		base.ignore('aspectRatioChanged')
		self.root.removeNode()