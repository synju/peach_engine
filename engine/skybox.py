from direct.showbase.ShowBase import ShowBase
from panda3d.core import Filename, CardMaker, NodePath
import os

# Global created by ShowBase
base: ShowBase

class Skybox:
	"""A skybox using 6 cubemap textures - no pole pinching"""

	def __init__(self, engine, folder_path=None, faces=None, scale=500, overlap=1.001):
		"""
		Option 1 - folder_path: path to folder containing px, nx, py, ny, pz, nz images
		Option 2 - faces: dict mapping face names to file paths
				{
						'right': 'path/to/right.png',
						'left': 'path/to/left.png',
						'top': 'path/to/top.png',
						'bottom': 'path/to/bottom.png',
						'front': 'path/to/front.png',
						'back': 'path/to/back.png',
				}
		overlap: card size multiplier to hide seams (1.001 = 0.1% overlap)
		"""
		self.engine = engine
		self._visible = True

		# Create parent node
		self.node = NodePath('skybox')

		# Create 6 faces
		if faces:
			self._create_faces_manual(faces, scale, overlap)
		elif folder_path:
			self._create_faces_auto(folder_path, scale, overlap)
		else:
			print("Skybox: provide either folder_path or faces dict")

		# Don't let lighting affect the skybox
		self.node.setLightOff()

		# Render behind everything
		self.node.setBin('background', 0)
		self.node.setDepthWrite(False)

		# Attach to render
		self.node.reparentTo(base.render)

	def _create_faces_manual(self, faces, scale, overlap):
		"""Create faces with manually specified textures

		faces dict can be:
				'right': 'path.png'  OR
				'right': ('path.png', rotation, flip_h, flip_v)

		Examples:
				'top': 'sky.png'                    # no transforms
				'top': ('sky.png', 90)              # rotate 90 degrees
				'top': ('sky.png', 0, True)         # flip horizontal
				'top': ('sky.png', 90, True, False) # rotate + flip h
		"""
		half = scale / 2

		# Face definitions: (position, rotation HPR)
		face_transforms = {
			'right': ((half, 0, 0), (90, 0, 0)),
			'left': ((-half, 0, 0), (-90, 0, 0)),
			'top': ((0, 0, half), (0, -90, 0)),
			'bottom': ((0, 0, -half), (0, 90, 0)),
			'front': ((0, half, 0), (0, 0, 0)),
			'back': ((0, -half, 0), (180, 0, 0)),
		}

		# Make cards slightly larger to overlap and hide seams
		card_half = half * overlap

		cm = CardMaker('skybox_face')
		cm.setFrame(-card_half, card_half, -card_half, card_half)

		for name, value in faces.items():
			if name not in face_transforms:
				print(f"Skybox: unknown face '{name}', use: right, left, top, bottom, front, back")
				continue

			# Parse value - can be string or tuple
			tex_rotation = 0
			flip_h = False
			flip_v = False

			if isinstance(value, tuple):
				tex_path = value[0]
				if len(value) > 1:
					tex_rotation = value[1]
				if len(value) > 2:
					flip_h = value[2]
				if len(value) > 3:
					flip_v = value[3]
			else:
				tex_path = value

			pos, rot = face_transforms[name]

			# Create card
			card = self.node.attachNewNode(cm.generate())
			card.setPos(*pos)
			card.setHpr(*rot)
			card.setTwoSided(True)

			# Apply texture rotation
			if tex_rotation:
				card.setR(tex_rotation)

			# Apply flips via scale
			sx = -1 if flip_h else 1
			sz = -1 if flip_v else 1
			card.setSx(sx)
			card.setSz(sz)

			# Load and apply texture
			try:
				tex = base.loader.loadTexture(tex_path)
				if tex:
					# Clamp texture to prevent edge bleeding
					from panda3d.core import SamplerState
					tex.setWrapU(SamplerState.WM_clamp)
					tex.setWrapV(SamplerState.WM_clamp)
					card.setTexture(tex)
			except Exception as e:
				print(f"Could not load skybox texture {tex_path}: {e}")

	def _create_faces_auto(self, folder_path, scale, overlap):
		"""Create faces from folder with px, nx, py, ny, pz, nz naming"""
		half = scale / 2

		# Map file names to face positions
		faces = {
			'px': ((half, 0, 0), (90, 0, 0)),
			'nx': ((-half, 0, 0), (-90, 0, 0)),
			'py': ((0, 0, half), (0, -90, 0)),
			'ny': ((0, 0, -half), (0, 90, 0)),
			'pz': ((0, half, 0), (0, 0, 0)),
			'nz': ((0, -half, 0), (180, 0, 0)),
		}

		# Make cards slightly larger to overlap and hide seams
		card_half = half * overlap

		cm = CardMaker('skybox_face')
		cm.setFrame(-card_half, card_half, -card_half, card_half)

		for name, (pos, rot) in faces.items():
			card = self.node.attachNewNode(cm.generate())
			card.setPos(*pos)
			card.setHpr(*rot)
			card.setTwoSided(True)

			# Try common extensions
			tex = None
			for ext in ['png', 'jpg', 'jpeg']:
				tex_path = f"{folder_path}/{name}.{ext}"
				try:
					tex = base.loader.loadTexture(tex_path)
					if tex:
						break
				except:
					pass

			if tex:
				card.setTexture(tex)
				# Clamp texture to prevent edge bleeding
				from panda3d.core import SamplerState
				tex.setWrapU(SamplerState.WM_clamp)
				tex.setWrapV(SamplerState.WM_clamp)

	@property
	def visible(self):
		return self._visible

	@visible.setter
	def visible(self, value):
		self._visible = value
		if value:
			self.node.show()
		else:
			self.node.hide()

	def show(self):
		self.visible = True

	def hide(self):
		self.visible = False

	def update(self, dt):
		"""Follow camera position so sky appears infinitely far"""
		if self.engine.renderer.camera:
			pos = self.engine.renderer.camera.position
			self.node.setPos(pos[0], pos[1], pos[2])

	def destroy(self):
		if self.node:
			self.node.removeNode()
			self.node = None
