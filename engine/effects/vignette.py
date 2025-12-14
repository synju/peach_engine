from engine.effects.post_processing_stack import StackEffect

VIGNETTE_FRAG = """
#version 330

uniform float intensity;
uniform float radius;
uniform float softness;
uniform int debug_mode;

in vec2 texcoord;
out vec4 frag_color;

void main() {
	vec2 uv = texcoord * 2.0 - 1.0;
	float dist = length(uv);
	float vignette = smoothstep(radius, radius - softness, dist);

	if (debug_mode == 1) {
		frag_color = vec4(vignette, vignette, vignette, 1.0);
		return;
	}

	float darkness = (1.0 - vignette) * intensity;
	frag_color = vec4(0.0, 0.0, 0.0, darkness);
}
"""

class Vignette(StackEffect):
	"""Vignette - darkens screen edges"""

	def __init__(self, intensity=0.5, radius=0.8, softness=0.5, enabled=True, debug=False):
		super().__init__("vignette", VIGNETTE_FRAG, StackEffect.OVERLAY)
		self.intensity = intensity
		self.radius = radius
		self.softness = softness
		self.enabled = enabled
		self.debug = debug

	def apply(self):
		self.set_shader_input("intensity", self.intensity)
		self.set_shader_input("radius", self.radius)
		self.set_shader_input("softness", self.softness)
		self.set_shader_input("debug_mode", 1 if self.debug else 0)
