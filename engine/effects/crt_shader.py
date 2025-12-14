from engine.effects.post_processing_stack import StackEffect

CRT_FRAG = """
#version 330

uniform sampler2D scene_tex;
uniform vec2 screen_size;
uniform float curvature;
uniform float scanline_intensity;
uniform float scanline_count;
uniform float chromatic_aberration;
uniform float vignette;
uniform float gamma;
uniform int debug_mode;

in vec2 texcoord;
out vec4 frag_color;

vec2 curve(vec2 uv) {
	if (curvature < 0.0001) return uv;
	uv = uv * 2.0 - 1.0;
	vec2 offset = abs(uv.yx) / vec2(curvature);
	uv = uv + uv * offset * offset;
	uv = uv * 0.5 + 0.5;
	return uv;
}

void main() {
	vec2 uv = curve(texcoord);

	if (uv.x < 0.0 || uv.x > 1.0 || uv.y < 0.0 || uv.y > 1.0) {
		frag_color = vec4(0.0, 0.0, 0.0, 1.0);
		return;
	}

	float r = texture(scene_tex, uv + vec2(chromatic_aberration, 0.0)).r;
	float g = texture(scene_tex, uv).g;
	float b = texture(scene_tex, uv - vec2(chromatic_aberration, 0.0)).b;
	vec3 color = vec3(r, g, b);

	color = pow(color, vec3(1.0 / gamma));

	float scanline = sin(uv.y * scanline_count * 3.14159) * 0.5 + 0.5;
	scanline = pow(scanline, 1.5) * scanline_intensity + (1.0 - scanline_intensity);
	color *= scanline;

	vec2 vig_uv = uv * 2.0 - 1.0;
	float vig = 1.0 - dot(vig_uv, vig_uv) * vignette;
	color *= vig;

	if (debug_mode == 1) {
		frag_color = vec4(scanline, scanline, scanline, 1.0);
		return;
	}

	frag_color = vec4(color, 1.0);
}
"""

class CRTShader(StackEffect):
	"""Simple CRT with curvature, scanlines, chromatic aberration"""

	def __init__(self, curvature=4.0, scanline_intensity=0.3, scanline_count=240.0,
							 chromatic_aberration=0.002, vignette=0.2, gamma=1.0, enabled=True, debug=False):
		super().__init__("crt", CRT_FRAG, StackEffect.TRANSFORM)
		self.curvature = curvature
		self.scanline_intensity = scanline_intensity
		self.scanline_count = scanline_count
		self.chromatic_aberration = chromatic_aberration
		self.vignette = vignette
		self.gamma = gamma
		self.enabled = enabled
		self.debug = debug

	def apply(self):
		self.set_shader_input("curvature", self.curvature)
		self.set_shader_input("scanline_intensity", self.scanline_intensity)
		self.set_shader_input("scanline_count", self.scanline_count)
		self.set_shader_input("chromatic_aberration", self.chromatic_aberration)
		self.set_shader_input("vignette", self.vignette)
		self.set_shader_input("gamma", self.gamma)
		self.set_shader_input("debug_mode", 1 if self.debug else 0)
