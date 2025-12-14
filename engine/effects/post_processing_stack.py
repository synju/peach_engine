from direct.showbase.ShowBase import ShowBase
from panda3d.core import (
	NodePath, Vec2, CardMaker, Shader,
	Texture, TransparencyAttrib,
	FrameBufferProperties, GraphicsPipe, GraphicsOutput,
	WindowProperties, Camera, OrthographicLens
)

base: ShowBase

PASSTHROUGH_VERT = """
#version 330
uniform mat4 p3d_ModelViewProjectionMatrix;
in vec4 p3d_Vertex;
in vec2 p3d_MultiTexCoord0;
out vec2 texcoord;
void main() {
	gl_Position = p3d_ModelViewProjectionMatrix * p3d_Vertex;
	texcoord = p3d_MultiTexCoord0;
}
"""

PASSTHROUGH_FRAG = """
#version 330
uniform sampler2D input_tex;
in vec2 texcoord;
out vec4 frag_color;
void main() {
	frag_color = texture(input_tex, texcoord);
}
"""

class StackEffect:
	"""
	Base class for stackable post-process effects.

	Effect types:
	- TRANSFORM: Reads input texture, outputs modified image (chains with previous)
	- OVERLAY: Blends on top with transparency (doesn't need chaining)
	"""

	TRANSFORM = "transform"
	OVERLAY = "overlay"

	def __init__(self, name, frag_shader, effect_type=None, vert_shader=None):
		self.name = name
		self.enabled = True
		self.effect_type = effect_type or self.TRANSFORM
		self._frag = frag_shader
		self._vert = vert_shader or PASSTHROUGH_VERT
		self._quad = None
		self._shader = None

	def _create_quad(self, render_parent):
		"""Create fullscreen quad"""
		cm = CardMaker(f'{self.name}_quad')
		cm.setFrameFullscreenQuad()
		self._quad = NodePath(cm.generate())
		self._quad.reparentTo(render_parent)
		self._shader = Shader.make(Shader.SL_GLSL, self._vert, self._frag)
		self._quad.setShader(self._shader)

		if self.effect_type == self.OVERLAY:
			self._quad.setTransparency(TransparencyAttrib.MAlpha)

		return self._quad

	def set_shader_input(self, name, value):
		"""Set a shader uniform"""
		if self._quad:
			self._quad.setShaderInput(name, value)

	def apply(self):
		"""Apply effect-specific uniforms - override in subclass"""
		pass

	def update(self, dt):
		"""Update per frame - override in subclass"""
		pass

	def show(self):
		if self._quad:
			self._quad.show()

	def hide(self):
		if self._quad:
			self._quad.hide()

	def destroy(self):
		if self._quad:
			self._quad.removeNode()
			self._quad = None

class PostProcessingStack:
	"""
	Manages post-processing effects with proper chaining via ping-pong buffers.

	TRANSFORM effects chain together (each reads previous output).
	OVERLAY effects render on top with transparency.

	Effects process in the order they are added.

	Usage:
		stack = PostProcessingStack(engine)
		stack.add_effect(HBAO(...))
		stack.add_effect(CRTNewPixie(...))
		stack.add_effect(CRTLottes(...))
		stack.add_effect(Vignette(...))

		# In update loop:
		stack.process(dt)
	"""

	def __init__(self, engine):
		self.engine = engine
		self.effects = []
		self.enabled = True
		self._width = 0
		self._height = 0

		# Ping-pong buffers for transform effect chaining
		self._buffers = [None, None]
		self._textures = [None, None]
		self._cameras = [None, None]
		self._scenes = [None, None]

		self._setup_buffers()

	def _setup_buffers(self):
		"""Create ping-pong render buffers"""
		self._width = base.win.getXSize()
		self._height = base.win.getYSize()

		for i in range(2):
			self._create_buffer(i)

	def _create_buffer(self, index):
		"""Create a render buffer with texture"""
		# Create texture
		self._textures[index] = Texture(f"pp_tex_{index}")
		self._textures[index].setup2dTexture(
			self._width, self._height,
			Texture.T_unsigned_byte, Texture.F_rgba8
		)
		self._textures[index].setWrapU(Texture.WM_clamp)
		self._textures[index].setWrapV(Texture.WM_clamp)

		# Buffer properties
		fb_props = FrameBufferProperties()
		fb_props.setRgbColor(True)
		fb_props.setRgbaBits(8, 8, 8, 8)
		fb_props.setDepthBits(0)

		win_props = WindowProperties.size(self._width, self._height)
		flags = GraphicsPipe.BF_refuse_window | GraphicsPipe.BF_resizeable

		# Create buffer
		self._buffers[index] = base.graphicsEngine.makeOutput(
			base.pipe, f"pp_buffer_{index}", -2,
			fb_props, win_props, flags,
			base.win.getGsg(), base.win
		)

		if self._buffers[index]:
			self._buffers[index].addRenderTexture(
				self._textures[index],
				GraphicsOutput.RTM_bind_or_copy
			)
			self._buffers[index].setSort(-100 + index)
			self._buffers[index].setClearColor((0, 0, 0, 1))
			self._buffers[index].setClearColorActive(True)

			# Create scene for this buffer
			self._scenes[index] = NodePath(f"pp_scene_{index}")

			# Create orthographic camera
			lens = OrthographicLens()
			lens.setFilmSize(2, 2)
			lens.setNearFar(-1000, 1000)

			cam_node = Camera(f"pp_cam_{index}")
			cam_node.setLens(lens)
			self._cameras[index] = self._scenes[index].attachNewNode(cam_node)

			# Create display region
			dr = self._buffers[index].makeDisplayRegion()
			dr.setCamera(self._cameras[index])

	def _check_resize(self):
		"""Check if window was resized and recreate buffers if needed"""
		new_width = base.win.getXSize()
		new_height = base.win.getYSize()

		if new_width != self._width or new_height != self._height:
			self._width = new_width
			self._height = new_height

			# Resize textures
			for i in range(2):
				if self._textures[i]:
					self._textures[i].setup2dTexture(
						self._width, self._height,
						Texture.T_unsigned_byte, Texture.F_rgba8
					)

	def add_effect(self, effect):
		"""Add an effect to the stack. Effects process in order added."""
		effect._create_quad(base.render2d)
		self.effects.append(effect)

		if not effect.enabled:
			effect.hide()

		return effect

	def insert_effect(self, index, effect):
		"""Insert an effect at a specific position in the stack."""
		effect._create_quad(base.render2d)
		self.effects.insert(index, effect)

		if not effect.enabled:
			effect.hide()

		return effect

	def remove_effect(self, effect):
		"""Remove an effect from the stack"""
		if effect in self.effects:
			self.effects.remove(effect)
			effect.destroy()

	def move_effect(self, effect, new_index):
		"""Move an effect to a new position in the stack."""
		if effect in self.effects:
			self.effects.remove(effect)
			self.effects.insert(new_index, effect)

	def get_effect(self, name):
		"""Get an effect by name"""
		for effect in self.effects:
			if effect.name == name:
				return effect
		return None

	def process(self, dt):
		"""
		Process all effects with proper chaining.
		TRANSFORM effects chain via ping-pong buffers.
		OVERLAY effects render directly to screen.
		"""
		if not self.enabled:
			for effect in self.effects:
				effect.hide()
			return

		self._check_resize()
		screen_size = Vec2(self._width, self._height)

		# Get textures from renderer
		scene_tex = self.engine.renderer.color_tex
		depth_tex = self.engine.renderer.depth_tex

		# Separate transform and overlay effects (maintaining order)
		active_transforms = [e for e in self.effects if e.enabled and e.effect_type == StackEffect.TRANSFORM]
		active_overlays = [e for e in self.effects if e.enabled and e.effect_type == StackEffect.OVERLAY]

		# Hide disabled effects
		for effect in self.effects:
			if not effect.enabled:
				effect.hide()

		# Current input starts as scene texture
		current_input = scene_tex
		current_buffer = 0

		# Process TRANSFORM effects with ping-pong chaining
		for i, effect in enumerate(active_transforms):
			is_last_transform = (i == len(active_transforms) - 1)

			if is_last_transform:
				# Last transform renders to screen
				effect._quad.reparentTo(base.render2d)
				effect._quad.setBin("fixed", 50 + i)
			else:
				# Intermediate transforms render to buffer
				effect._quad.reparentTo(self._scenes[current_buffer])

			effect.show()

			# Set uniforms - use current_input (which chains from previous effect)
			effect.set_shader_input("screen_size", screen_size)
			effect.set_shader_input("scene_tex", current_input)
			effect.set_shader_input("input_tex", current_input)
			effect.set_shader_input("depth_tex", depth_tex)

			lens = base.camLens
			effect.set_shader_input("near_plane", lens.getNear())
			effect.set_shader_input("far_plane", lens.getFar())

			effect.update(dt)
			effect.apply()

			if not is_last_transform:
				# Next effect reads from this buffer's output
				current_input = self._textures[current_buffer]
				# Ping-pong to other buffer
				current_buffer = 1 - current_buffer

		# Process OVERLAY effects (render on top of everything)
		for i, effect in enumerate(active_overlays):
			effect._quad.reparentTo(base.render2d)
			effect._quad.setBin("fixed", 70 + i)  # Overlays render after transforms
			effect.show()

			effect.set_shader_input("screen_size", screen_size)
			effect.set_shader_input("scene_tex", scene_tex)
			effect.set_shader_input("depth_tex", depth_tex)

			lens = base.camLens
			effect.set_shader_input("near_plane", lens.getNear())
			effect.set_shader_input("far_plane", lens.getFar())

			effect.update(dt)
			effect.apply()

	def turn_on(self):
		"""Enable the stack"""
		self.enabled = True

	def turn_off(self):
		"""Disable the stack"""
		self.enabled = False
		for effect in self.effects:
			effect.hide()

	def destroy(self):
		"""Clean up all resources"""
		for effect in self.effects:
			effect.destroy()
		self.effects.clear()

		# Clean up buffers
		for i in range(2):
			if self._buffers[i]:
				base.graphicsEngine.removeWindow(self._buffers[i])
			if self._scenes[i]:
				self._scenes[i].removeNode()