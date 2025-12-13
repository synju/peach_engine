import random
from direct.showbase.ShowBase import ShowBase
from panda3d.core import (
	NodePath, Vec2, Vec4, CardMaker,
	Shader, TransparencyAttrib,
	Texture, PNMImage
)

base: ShowBase

# Simple SSAO shader - single pass like fog
SSAO_VERT = """
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

SSAO_FRAG = """
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

	// Skip skybox
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

	// Random offset from noise
	vec2 noise = texture(noise_tex, texcoord * screen_size / 4.0).rg;

	float occlusion = 0.0;
	float total_samples = 0.0;

	// Max depth difference to consider (rejects silhouette edges)
	float max_depth_diff = center_depth * 0.2;  // 20% of current depth

	// Sample in a small radius around the pixel
	for (int i = 0; i < 8; i++) {
		float angle = (float(i) + noise.x) * 0.785398; // pi/4 * i
		vec2 dir = vec2(cos(angle), sin(angle));

		// Sample at multiple distances
		for (int j = 1; j <= ao_samples; j++) {
			float scale = float(j) * ao_radius * 20.0;
			vec2 sample_uv = texcoord + dir * scale * texel;

			if (sample_uv.x < 0.0 || sample_uv.x > 1.0 || 
				sample_uv.y < 0.0 || sample_uv.y > 1.0) continue;

			float sample_raw = texture(depth_tex, sample_uv).r;

			// Skip if sample hit skybox
			if (sample_raw >= 0.9999) {
				total_samples += 1.0;
				continue;
			}

			float sample_depth = linearize_depth(sample_raw);

			// Depth difference (positive = sample is closer to camera)
			float diff = center_depth - sample_depth;

			// Reject silhouette edges - if depth difference is too large in either direction,
			// it's an edge discontinuity, not a corner
			if (abs(diff) > max_depth_diff) {
				total_samples += 1.0;
				continue;
			}

			// Only count as occlusion if sample is slightly in front (closer)
			if (diff > ao_bias * 0.001 && diff < max_depth_diff) {
				occlusion += 1.0 - (diff / max_depth_diff);
			}
			total_samples += 1.0;
		}
	}

	// Calculate final AO
	float ao = 1.0;
	if (total_samples > 0.0) {
		ao = 1.0 - (occlusion / total_samples) * ao_intensity;
	}
	ao = clamp(ao, 0.0, 1.0);

	if (debug_mode == 1) {
		// Debug: show raw AO
		frag_color = vec4(ao, ao, ao, 1.0);
	} else {
		// Normal: darken where occluded
		float darkness = (1.0 - ao) * ao_intensity;
		frag_color = vec4(0.0, 0.0, 0.0, darkness);
	}
}
"""

class HBAO:
	"""Screen-Space Ambient Occlusion post-process effect"""

	def __init__(self, engine, radius=0.5, intensity=0.5, samples=4, bias=0.1, hbao_enabled=True, debug=False):
		self.engine = engine
		self._radius = radius
		self._intensity = intensity
		self._samples = samples
		self._bias = bias
		self._enabled = hbao_enabled
		self._debug = debug

		self._depth_tex = None
		self._noise_tex = None
		self._quad = None

		self._setup()

		if not self._enabled:
			self._quad.hide()

	def _setup(self):
		"""Setup SSAO resources"""
		self._depth_tex = self.engine.renderer.depth_tex
		self._create_noise_texture()
		self._create_quad()

	def _create_noise_texture(self):
		"""Create 4x4 noise texture for randomizing samples"""
		size = 4
		img = PNMImage(size, size)

		for y in range(size):
			for x in range(size):
				r = random.random()
				g = random.random()
				img.setXel(x, y, r, g, 0)

		self._noise_tex = Texture("ssao_noise")
		self._noise_tex.load(img)
		self._noise_tex.setWrapU(Texture.WM_repeat)
		self._noise_tex.setWrapV(Texture.WM_repeat)
		self._noise_tex.setMinfilter(Texture.FT_nearest)
		self._noise_tex.setMagfilter(Texture.FT_nearest)

	def _create_quad(self):
		"""Create fullscreen quad for SSAO"""
		cm = CardMaker('ssao_quad')
		cm.setFrameFullscreenQuad()

		self._quad = NodePath(cm.generate())
		self._quad.reparentTo(base.render2d)

		shader = Shader.make(Shader.SL_GLSL, SSAO_VERT, SSAO_FRAG)
		self._quad.setShader(shader)
		self._quad.setTransparency(TransparencyAttrib.MAlpha)
		self._quad.setBin("fixed", 40)

		self._update_shader_inputs()

	def _update_shader_inputs(self):
		"""Update all shader uniforms"""
		if not self._quad:
			return

		self._quad.setShaderInput("depth_tex", self._depth_tex)
		self._quad.setShaderInput("noise_tex", self._noise_tex)
		self._quad.setShaderInput("screen_size", Vec2(base.win.getXSize(), base.win.getYSize()))

		lens = base.camLens
		self._quad.setShaderInput("near_plane", lens.getNear())
		self._quad.setShaderInput("far_plane", lens.getFar())

		self._quad.setShaderInput("ao_radius", self._radius)
		self._quad.setShaderInput("ao_intensity", self._intensity)
		self._quad.setShaderInput("ao_bias", self._bias)
		self._quad.setShaderInput("ao_samples", self._samples)
		self._quad.setShaderInput("debug_mode", 1 if self._debug else 0)

	def update(self):
		"""Update per frame"""
		if not self._enabled:
			return
		self._update_shader_inputs()

	@property
	def radius(self):
		return self._radius

	@radius.setter
	def radius(self, value):
		self._radius = value
		if self._quad:
			self._quad.setShaderInput("ao_radius", value)

	@property
	def intensity(self):
		return self._intensity

	@intensity.setter
	def intensity(self, value):
		self._intensity = value
		if self._quad:
			self._quad.setShaderInput("ao_intensity", value)

	@property
	def samples(self):
		return self._samples

	@samples.setter
	def samples(self, value):
		self._samples = value
		if self._quad:
			self._quad.setShaderInput("ao_samples", value)

	@property
	def bias(self):
		return self._bias

	@bias.setter
	def bias(self, value):
		self._bias = value
		if self._quad:
			self._quad.setShaderInput("ao_bias", value)

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