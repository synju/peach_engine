from engine.effects.post_processing_stack import StackEffect

FILM_GRAIN_FRAG = """
#version 330

uniform vec2 screen_size;
uniform float time;
uniform float intensity;
uniform float size;
uniform int debug_mode;

in vec2 texcoord;
out vec4 frag_color;

float hash(vec2 p) {
	vec3 p3 = fract(vec3(p.xyx) * 0.1031);
	p3 += dot(p3, p3.yzx + 33.33);
	return fract((p3.x + p3.y) * p3.z);
}

void main() {
	vec2 uv = texcoord * screen_size / size;
	float noise = hash(uv + time);
	noise = (noise - 0.5) * intensity + 0.5;

	if (debug_mode == 1) {
		frag_color = vec4(noise, noise, noise, 1.0);
		return;
	}

	float alpha = abs(noise - 0.5) * 2.0 * intensity;
	frag_color = vec4(noise, noise, noise, alpha);
}
"""

class FilmGrain(StackEffect):
	"""Animated film grain overlay"""

	def __init__(self, intensity=0.1, size=2.0, speed=1.0, enabled=True, debug=False):
		super().__init__("film_grain", FILM_GRAIN_FRAG, StackEffect.OVERLAY)
		self.intensity = intensity
		self.size = size
		self.speed = speed
		self.enabled = enabled
		self.debug = debug
		self._time = 0.0

	def apply(self):
		self.set_shader_input("intensity", self.intensity)
		self.set_shader_input("size", self.size)
		self.set_shader_input("time", self._time)
		self.set_shader_input("debug_mode", 1 if self.debug else 0)

	def update(self, dt):
		self._time += dt * self.speed
