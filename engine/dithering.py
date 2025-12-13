from direct.showbase.ShowBase import ShowBase
from panda3d.core import (
	NodePath, Vec2, CardMaker,
	Shader, TransparencyAttrib,
	Texture, PNMImage
)

base: ShowBase

DITHER_VERT = """
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

DITHER_FRAG = """
#version 330

uniform sampler2D scene_tex;
uniform sampler2D dither_tex;

uniform vec2 screen_size;
uniform float color_levels;
uniform float dither_strength;
uniform float opacity;
uniform float gamma;
uniform float contrast;
uniform int debug_mode;

in vec2 texcoord;
out vec4 frag_color;

void main() {
	vec4 color = texture(scene_tex, texcoord);

	// Apply gamma correction (linear to sRGB)
	vec3 corrected = pow(color.rgb, vec3(1.0/gamma));

	// Apply contrast
	corrected = (corrected - 0.5) * contrast + 0.5;

	// Get dither value from Bayer matrix texture (tiled)
	vec2 dither_uv = texcoord * screen_size / 8.0;  // 8x8 Bayer matrix
	float dither = texture(dither_tex, dither_uv).r;

	// Remap dither from 0-1 to -0.5 to 0.5
	dither = (dither - 0.5) * dither_strength;

	if (debug_mode == 1) {
		// Debug: show dither pattern
		frag_color = vec4(dither + 0.5, dither + 0.5, dither + 0.5, 1.0);
		return;
	}

	// Apply dithering and quantize to color levels
	vec3 dithered = corrected + dither;

	// Quantize to specified number of levels
	vec3 quantized = floor(dithered * color_levels + 0.5) / color_levels;

	// Blend between original and dithered based on opacity
	vec3 final_color = mix(corrected, quantized, opacity);

	frag_color = vec4(final_color, color.a);
}
"""

class Dithering:
	"""Ordered dithering post-process effect using Bayer matrix"""

	def __init__(self, engine, color_levels=32.0, strength=0.05, opacity=0.5, gamma=2.2, contrast=1.0, dithering_enabled=True, debug_mode=False):
		self.engine = engine
		self._color_levels = color_levels
		self._strength = strength
		self._opacity = opacity
		self._gamma = gamma
		self._contrast = contrast
		self._enabled = dithering_enabled
		self._debug = debug_mode

		self._scene_tex = None
		self._dither_tex = None
		self._quad = None

		self._setup()

		if not self._enabled:
			self._quad.hide()

	def _setup(self):
		"""Setup dithering resources"""
		self._get_scene_texture()
		self._create_bayer_texture()
		self._create_quad()

	def _get_scene_texture(self):
		"""Get the rendered scene texture from renderer"""
		self._scene_tex = self.engine.renderer.color_tex

	def _create_bayer_texture(self):
		"""Create 8x8 Bayer matrix texture for ordered dithering"""
		# 8x8 Bayer matrix values (normalized 0-1)
		bayer_8x8 = [
			0, 32, 8, 40, 2, 34, 10, 42,
			48, 16, 56, 24, 50, 18, 58, 26,
			12, 44, 4, 36, 14, 46, 6, 38,
			60, 28, 52, 20, 62, 30, 54, 22,
			3, 35, 11, 43, 1, 33, 9, 41,
			51, 19, 59, 27, 49, 17, 57, 25,
			15, 47, 7, 39, 13, 45, 5, 37,
			63, 31, 55, 23, 61, 29, 53, 21
		]

		size = 8
		img = PNMImage(size, size)

		for y in range(size):
			for x in range(size):
				val = bayer_8x8[y * size + x] / 64.0
				img.setXel(x, y, val, val, val)

		self._dither_tex = Texture("bayer_dither")
		self._dither_tex.load(img)
		self._dither_tex.setWrapU(Texture.WM_repeat)
		self._dither_tex.setWrapV(Texture.WM_repeat)
		self._dither_tex.setMinfilter(Texture.FT_nearest)
		self._dither_tex.setMagfilter(Texture.FT_nearest)

	def _create_quad(self):
		"""Create fullscreen quad for dithering"""
		cm = CardMaker('dither_quad')
		cm.setFrameFullscreenQuad()

		self._quad = NodePath(cm.generate())
		self._quad.reparentTo(base.render2d)

		shader = Shader.make(Shader.SL_GLSL, DITHER_VERT, DITHER_FRAG)
		self._quad.setShader(shader)
		self._quad.setBin("fixed", 45)  # After HBAO

		self._update_shader_inputs()

	def _update_shader_inputs(self):
		"""Update all shader uniforms"""
		if not self._quad:
			return

		self._quad.setShaderInput("scene_tex", self._scene_tex)
		self._quad.setShaderInput("dither_tex", self._dither_tex)
		self._quad.setShaderInput("screen_size", Vec2(base.win.getXSize(), base.win.getYSize()))
		self._quad.setShaderInput("color_levels", self._color_levels)
		self._quad.setShaderInput("dither_strength", self._strength)
		self._quad.setShaderInput("opacity", self._opacity)
		self._quad.setShaderInput("gamma", self._gamma)
		self._quad.setShaderInput("contrast", self._contrast)
		self._quad.setShaderInput("debug_mode", 1 if self._debug else 0)

	def update(self):
		"""Update per frame"""
		if not self._enabled:
			return
		self._update_shader_inputs()

	@property
	def color_levels(self):
		return self._color_levels

	@color_levels.setter
	def color_levels(self, value):
		self._color_levels = value
		if self._quad:
			self._quad.setShaderInput("color_levels", value)

	@property
	def strength(self):
		return self._strength

	@strength.setter
	def strength(self, value):
		self._strength = value
		if self._quad:
			self._quad.setShaderInput("dither_strength", value)

	@property
	def opacity(self):
		return self._opacity

	@opacity.setter
	def opacity(self, value):
		self._opacity = value
		if self._quad:
			self._quad.setShaderInput("opacity", value)

	@property
	def gamma(self):
		return self._gamma

	@gamma.setter
	def gamma(self, value):
		self._gamma = value
		if self._quad:
			self._quad.setShaderInput("gamma", value)

	@property
	def contrast(self):
		return self._contrast

	@contrast.setter
	def contrast(self, value):
		self._contrast = value
		if self._quad:
			self._quad.setShaderInput("contrast", value)

	@property
	def enabled(self):
		return self._enabled

	@enabled.setter
	def enabled(self, value):
		self._enabled = value
		if self._quad:
			if value:
				self._quad.show()
			else:
				self._quad.hide()

	@property
	def debug(self):
		return self._debug

	@debug.setter
	def debug(self, value):
		self._debug = value
		if self._quad:
			self._quad.setShaderInput("debug_mode", 1 if value else 0)

	def turn_on(self):
		self.enabled = True

	def turn_off(self):
		self.enabled = False

	def destroy(self):
		"""Clean up resources"""
		if self._quad:
			self._quad.removeNode()
			self._quad = None