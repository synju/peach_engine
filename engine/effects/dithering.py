from panda3d.core import Texture, PNMImage

from engine.effects.post_processing_stack import StackEffect

DITHERING_FRAG = """
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
	vec3 corrected = pow(color.rgb, vec3(1.0/gamma));
	corrected = (corrected - 0.5) * contrast + 0.5;

	vec2 dither_uv = texcoord * screen_size / 8.0;
	float dither = texture(dither_tex, dither_uv).r;
	dither = (dither - 0.5) * dither_strength;

	if (debug_mode == 1) {
		frag_color = vec4(dither + 0.5, dither + 0.5, dither + 0.5, 1.0);
		return;
	}

	vec3 dithered = corrected + dither;
	vec3 quantized = floor(dithered * color_levels + 0.5) / color_levels;
	vec3 final_color = mix(corrected, quantized, opacity);

	frag_color = vec4(final_color, color.a);
}
"""

class Dithering(StackEffect):
	"""Ordered dithering with Bayer matrix"""

	def __init__(self, color_levels=32.0, strength=0.05, opacity=0.5, gamma=2.2, contrast=1.0, enabled=True, debug=False):
		super().__init__("dithering", DITHERING_FRAG, StackEffect.TRANSFORM)
		self.color_levels = color_levels
		self.strength = strength
		self.opacity = opacity
		self.gamma = gamma
		self.contrast = contrast
		self.enabled = enabled
		self.debug = debug
		self._dither_tex = None
		self._create_bayer_texture()

	def _create_bayer_texture(self):
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

	def apply(self):
		self.set_shader_input("dither_tex", self._dither_tex)
		self.set_shader_input("color_levels", self.color_levels)
		self.set_shader_input("dither_strength", self.strength)
		self.set_shader_input("opacity", self.opacity)
		self.set_shader_input("gamma", self.gamma)
		self.set_shader_input("contrast", self.contrast)
		self.set_shader_input("debug_mode", 1 if self.debug else 0)
