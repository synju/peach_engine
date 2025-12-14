from direct.actor.Actor import Actor
from panda3d.core import Vec3, BitMask32
from panda3d.bullet import BulletBoxShape, BulletRigidBodyNode

from direct.showbase.ShowBase import ShowBase

base: ShowBase

class ActorObject:
	"""
	Base class for animated 3D models using Panda3D's Actor system.

	Handles:
	- Loading GLTF/GLB models with embedded animations
	- Animation playback (play, loop, stop, blend)
	- Optional physics collision

	Usage:
		actor = ActorObject(engine, 'path/to/model.gltf', position=[0,0,0])
		actor.loop('idle')
		actor.play('attack')
	"""

	def __init__(self, engine, model_path, position=None, rotation=None, scale=1.0,
							 collision_enabled=False, collision_size=None, mass=0.0):
		self.engine = engine
		self.model_path = model_path
		self.position = position or [0, 0, 0]
		self.rotation = rotation or [0, 0, 0]
		self.scale = scale if isinstance(scale, (list, tuple)) else [scale, scale, scale]

		self.actor = None
		self.node = None
		self.collision_node = None
		self.animations = {}
		self.current_anim = None
		self._blend_interval = None

		self._load_actor()

		if collision_enabled:
			self._setup_collision(collision_size, mass)

	def _load_actor(self):
		"""Load the animated model"""
		self.actor = Actor(self.model_path)
		self.actor.reparentTo(base.render)

		# Apply transform
		self.actor.setPos(Vec3(*self.position))
		self.actor.setHpr(Vec3(*self.rotation))
		self.actor.setScale(Vec3(*self.scale))

		self.node = self.actor

		# Get available animations
		self._discover_animations()

	def _discover_animations(self):
		"""Find all animations in the model"""
		try:
			# Get all animation names
			anims = self.actor.getAnimNames()
			for anim in anims:
				self.animations[anim] = True
		except Exception as e:
			print(f"Warning: Could not discover animations: {e}")

	def get_animations(self):
		"""Return list of available animation names"""
		return list(self.animations.keys())

	def print_animations(self):
		"""Print all available animations for debugging"""
		print(f"Animations in {self.model_path}:")
		try:
			anims = self.actor.getAnimNames()
			if anims:
				for anim in anims:
					try:
						duration = self.actor.getDuration(anim)
						frames = self.actor.getNumFrames(anim)
						print(f"  - {anim} ({frames} frames, {duration:.2f}s)")
					except:
						print(f"  - {anim}")
			else:
				print("  No animations found!")
				# Debug: check if there's animation data at all
				print("  Debug info:")
				print(f"    Part names: {self.actor.getPartNames()}")
				bundle = self.actor.getPartBundle('modelRoot')
				if bundle:
					print(f"    Bundle: {bundle}")
					print(f"    Num children: {bundle.getNumChildren()}")
		except Exception as e:
			print(f"  Error listing animations: {e}")

	def play(self, anim_name, blend_time=0.0, from_frame=None, to_frame=None):
		"""Play animation once, optionally blending from current"""
		if blend_time > 0 and self.current_anim:
			self._blend_to(anim_name, blend_time, loop=False)
		else:
			self.actor.play(anim_name, fromFrame=from_frame, toFrame=to_frame)
		self.current_anim = anim_name

	def loop(self, anim_name, blend_time=0.0, restart=True, from_frame=None, to_frame=None):
		"""Loop animation continuously, optionally blending from current"""
		if blend_time > 0 and self.current_anim:
			self._blend_to(anim_name, blend_time, loop=True)
		else:
			self.actor.loop(anim_name, restart=restart, fromFrame=from_frame, toFrame=to_frame)
		self.current_anim = anim_name

	def _blend_to(self, anim_name, blend_time, loop=True):
		"""Smoothly blend from current animation to new one"""
		old_anim = self.current_anim

		# Cancel any existing blend and finalize it
		if hasattr(self, '_blend_interval') and self._blend_interval:
			self._blend_interval.finish()  # Complete it instantly
			self._blend_interval = None

		if not old_anim or old_anim == anim_name:
			# No old animation or same animation, just play directly
			self.actor.disableBlend()
			if loop:
				self.actor.loop(anim_name)
			else:
				self.actor.play(anim_name)
			return

		# Enable blend mode
		self.actor.enableBlend()

		# Old anim keeps playing at full weight
		self.actor.setControlEffect(old_anim, 1.0)

		# Start new animation with 0 weight
		self.actor.setControlEffect(anim_name, 0.0)
		if loop:
			self.actor.loop(anim_name)
		else:
			self.actor.play(anim_name)

		# Store for the lerp
		self._blend_old = old_anim
		self._blend_new = anim_name

		# Create blend interval
		from direct.interval.LerpInterval import LerpFunc

		def update_blend(t):
			if self.actor:
				try:
					self.actor.setControlEffect(self._blend_old, 1.0 - t)
					self.actor.setControlEffect(self._blend_new, t)
					if t >= 1.0:
						self.actor.disableBlend()
						self.actor.stop(self._blend_old)
						self._blend_interval = None
				except:
					pass

		self._blend_interval = LerpFunc(update_blend, fromData=0.0, toData=1.0, duration=blend_time)
		self._blend_interval.start()

	def stop(self, anim_name=None):
		"""Stop animation"""
		if anim_name:
			self.actor.stop(anim_name)
		else:
			self.actor.stop()
		self.current_anim = None

	def pose(self, anim_name, frame):
		"""Set to specific frame of animation"""
		self.actor.pose(anim_name, frame)

	def blend(self, anim_name1, anim_name2, blend_factor):
		"""Blend between two animations (0.0 = anim1, 1.0 = anim2)"""
		# Enable blending
		self.actor.enableBlend()
		self.actor.setControlEffect(anim_name1, 1.0 - blend_factor)
		self.actor.setControlEffect(anim_name2, blend_factor)

	def get_duration(self, anim_name):
		"""Get animation duration in seconds"""
		try:
			return self.actor.getDuration(anim_name)
		except:
			return 0.0

	def get_num_frames(self, anim_name):
		"""Get number of frames in animation"""
		try:
			return self.actor.getNumFrames(anim_name)
		except:
			return 0

	def get_current_frame(self, anim_name=None):
		"""Get current frame number"""
		anim = anim_name or self.current_anim
		if anim:
			try:
				return self.actor.getCurrentFrame(anim)
			except:
				return 0
		return 0

	def is_playing(self, anim_name=None):
		"""Check if animation is currently playing (not finished)"""
		anim = anim_name or self.current_anim
		if not anim:
			return False

		try:
			ctrl = self.actor.getAnimControl(anim)
			if ctrl:
				return ctrl.isPlaying()
		except:
			pass

		# Fallback
		return self.actor.getCurrentAnim() == anim

	def _setup_collision(self, size, mass):
		"""Setup bullet physics collision"""
		if size is None:
			# Auto-calculate from bounds
			bounds = self.actor.getTightBounds()
			if bounds:
				min_pt, max_pt = bounds
				size = (max_pt - min_pt) * 0.5
			else:
				size = Vec3(0.5, 0.5, 0.5)
		else:
			size = Vec3(*size) if isinstance(size, (list, tuple)) else Vec3(size, size, size)

		shape = BulletBoxShape(size)

		self.collision_node = BulletRigidBodyNode(f'actor_collision')
		self.collision_node.addShape(shape)
		self.collision_node.setMass(mass)

		np = base.render.attachNewNode(self.collision_node)
		np.setPos(Vec3(*self.position))
		np.setHpr(Vec3(*self.rotation))

		self.engine.physics.attachRigidBody(self.collision_node)

		# Reparent actor to physics node
		self.actor.reparentTo(np)
		self.actor.setPos(0, 0, 0)
		self.actor.setHpr(0, 0, 0)
		self.node = np

	def set_position(self, x, y, z):
		"""Set position"""
		self.position = [x, y, z]
		self.node.setPos(Vec3(x, y, z))

	def set_rotation(self, h, p, r):
		"""Set rotation (heading, pitch, roll)"""
		self.rotation = [h, p, r]
		self.node.setHpr(Vec3(h, p, r))

	def get_position(self):
		"""Get current position"""
		pos = self.node.getPos()
		return [pos.x, pos.y, pos.z]

	def look_at(self, target):
		"""Face toward a target position or NodePath"""
		if isinstance(target, (list, tuple)):
			self.node.lookAt(Vec3(*target))
		else:
			self.node.lookAt(target)

	def update(self, dt):
		"""Override in subclass for per-frame logic"""
		pass

	def destroy(self):
		"""Clean up resources"""
		# Cancel any blend in progress
		if hasattr(self, '_blend_interval') and self._blend_interval:
			self._blend_interval.pause()
			self._blend_interval = None

		if self.collision_node:
			self.engine.physics.removeRigidBody(self.collision_node)

		if self.actor:
			self.actor.cleanup()
			self.actor.removeNode()
			self.actor = None