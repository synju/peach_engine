import random
from panda3d.core import Texture, PNMImage

from engine.effects.post_processing_stack import StackEffect

HBAO_FRAG = """
#version 330

uniform sampler2D depth_tex;
uniform sampler2D noise_tex;

uniform vec2 screen_size;
uniform float near_plane;
uniform float far_plane;
uniform float ao_radius;
uniform float ao_intensity;
uniform float ao_bias;
uniform int ao_samples;
uniform int debug_mode;

in vec2 texcoord;
out vec4 frag_color;

float linearize_depth(float d) {
	return (2.0 * near_plane) / (far_plane + near_plane - d * (far_plane - near_plane));
}

void main() {
	float depth = texture(depth_tex, texcoord).r;

	if (depth >= 0.9999) {
		if (debug_mode == 1) {
			frag_color = vec4(1.0, 1.0, 1.0, 1.0);
		} else {
			frag_color = vec4(0.0, 0.0, 0.0, 0.0);
		}
		return;
	}

	float center_depth = linearize_depth(depth);
	vec2 texel = 1.0 / screen_size;
	vec2 noise = texture(noise_tex, texcoord * screen_size / 4.0).rg;

	float occlusion = 0.0;
	float total_samples = 0.0;
	float max_depth_diff = center_depth * 0.2;

	for (int i = 0; i < 8; i++) {
		float angle = (float(i) + noise.x) * 0.785398;
		vec2 dir = vec2(cos(angle), sin(angle));

		for (int j = 1; j <= ao_samples; j++) {
			float scale = float(j) * ao_radius * 20.0;
			vec2 sample_uv = texcoord + dir * scale * texel;

			if (sample_uv.x < 0.0 || sample_uv.x > 1.0 || 
				sample_uv.y < 0.0 || sample_uv.y > 1.0) continue;

			float sample_raw = texture(depth_tex, sample_uv).r;

			if (sample_raw >= 0.9999) {
				total_samples += 1.0;
				continue;
			}

			float sample_depth = linearize_depth(sample_raw);
			float diff = center_depth - sample_depth;

			if (abs(diff) > max_depth_diff) {
				total_samples += 1.0;
				continue;
			}

			if (diff > ao_bias * 0.001 && diff < max_depth_diff) {
				occlusion += 1.0 - (diff / max_depth_diff);
			}
			total_samples += 1.0;
		}
	}

	float ao = 1.0;
	if (total_samples > 0.0) {
		ao = 1.0 - (occlusion / total_samples) * ao_intensity;
	}
	ao = clamp(ao, 0.0, 1.0);

	if (debug_mode == 1) {
		frag_color = vec4(ao, ao, ao, 1.0);
	} else {
		float darkness = (1.0 - ao) * ao_intensity;
		frag_color = vec4(0.0, 0.0, 0.0, darkness);
	}
}
"""

class HBAO(StackEffect):
	"""Screen-Space Ambient Occlusion"""

	def __init__(self, radius=0.5, intensity=0.5, samples=4, bias=0.1, enabled=True, debug=False):
		super().__init__("hbao", HBAO_FRAG, StackEffect.OVERLAY)
		self.radius = radius
		self.intensity = intensity
		self.samples = samples
		self.bias = bias
		self.enabled = enabled
		self.debug = debug
		self._noise_tex = None
		self._create_noise_texture()

	def _create_noise_texture(self):
		size = 4
		img = PNMImage(size, size)
		for y in range(size):
			for x in range(size):
				img.setXel(x, y, random.random(), random.random(), 0)
		self._noise_tex = Texture("hbao_noise")
		self._noise_tex.load(img)
		self._noise_tex.setWrapU(Texture.WM_repeat)
		self._noise_tex.setWrapV(Texture.WM_repeat)
		self._noise_tex.setMinfilter(Texture.FT_nearest)
		self._noise_tex.setMagfilter(Texture.FT_nearest)

	def apply(self):
		self.set_shader_input("noise_tex", self._noise_tex)
		self.set_shader_input("ao_radius", self.radius)
		self.set_shader_input("ao_intensity", self.intensity)
		self.set_shader_input("ao_bias", self.bias)
		self.set_shader_input("ao_samples", self.samples)
		self.set_shader_input("debug_mode", 1 if self.debug else 0)
