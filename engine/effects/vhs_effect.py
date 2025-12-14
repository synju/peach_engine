import random
from panda3d.core import Texture, PNMImage

from engine.effects.post_processing_stack import StackEffect

VHS_FRAG = """
#version 330

uniform sampler2D overlay_tex;
uniform float scroll_offset;
uniform float opacity;
uniform float scale_x;
uniform float scale_y;
uniform int debug_mode;

in vec2 texcoord;
out vec4 frag_color;

void main() {
	vec2 uv = vec2(texcoord.x * scale_x, texcoord.y * scale_y);
	uv.y += scroll_offset;

	float noise = texture(overlay_tex, uv).r;

	if (debug_mode == 1) {
		frag_color = vec4(noise, noise, noise, 1.0);
		return;
	}

	frag_color = vec4(noise, noise, noise, noise * opacity);
}
"""

class VHSEffect(StackEffect):
	"""Scrolling VHS noise overlay"""

	def __init__(self, scroll_speed=0.5, opacity=0.15, scale_x=2.0, scale_y=2.0, enabled=True, debug=False):
		super().__init__("vhs", VHS_FRAG, StackEffect.OVERLAY)
		self.scroll_speed = scroll_speed
		self.opacity = opacity
		self.scale_x = scale_x
		self.scale_y = scale_y
		self.enabled = enabled
		self.debug = debug
		self._scroll_offset = 0.0
		self._overlay_tex = None
		self._create_noise_texture()

	def _create_noise_texture(self):
		width, height = 64, 256
		img = PNMImage(width, height)
		for y in range(height):
			scanline = 0.95 if y % 2 == 0 else 1.0
			band_noise = random.uniform(0.1, 0.3) if random.random() < 0.03 else 0
			for x in range(width):
				pixel_noise = random.uniform(-0.05, 0.05)
				val = max(0, min(1, scanline + band_noise + pixel_noise))
				img.setXel(x, y, val, val, val)
		self._overlay_tex = Texture("vhs_noise")
		self._overlay_tex.load(img)
		self._overlay_tex.setWrapU(Texture.WM_repeat)
		self._overlay_tex.setWrapV(Texture.WM_repeat)
		self._overlay_tex.setMinfilter(Texture.FT_nearest)
		self._overlay_tex.setMagfilter(Texture.FT_nearest)

	def apply(self):
		self.set_shader_input("overlay_tex", self._overlay_tex)
		self.set_shader_input("scroll_offset", self._scroll_offset)
		self.set_shader_input("opacity", self.opacity)
		self.set_shader_input("scale_x", self.scale_x)
		self.set_shader_input("scale_y", self.scale_y)
		self.set_shader_input("debug_mode", 1 if self.debug else 0)

	def update(self, dt):
		self._scroll_offset += self.scroll_speed * dt
		if self._scroll_offset > 1.0:
			self._scroll_offset -= 1.0
