from engine.effects.post_processing_stack import StackEffect

SHADOWMASK_FRAG = """
#version 330

uniform sampler2D scene_tex;
uniform vec2 screen_size;

uniform int mask_type;
uniform float line_density;
uniform float intensity;
uniform float dot_width;
uniform float brightness;
uniform int debug_mode;

in vec2 texcoord;
out vec4 frag_color;

void main() {
	vec3 color = texture(scene_tex, texcoord).rgb;

	// line_density controls how many RGB triplets across screen
	// Higher = more lines = finer pattern
	vec2 pos = texcoord * line_density;

	vec3 mask = vec3(1.0);

	if (mask_type == 0) {
		// Aperture grille - thin vertical RGB stripes (Trinitron style)
		float col = mod(floor(pos.x), 3.0);

		// Distance from center of cell - controls line thickness
		float sub_pos = fract(pos.x);
		float dist = abs(sub_pos - 0.5) * 2.0;  // 0 at center, 1 at edges
		float phosphor = 1.0 - smoothstep(dot_width, dot_width + 0.2, dist);

		if (col == 0.0) mask = vec3(phosphor, 0.0, 0.0);
		else if (col == 1.0) mask = vec3(0.0, phosphor, 0.0);
		else mask = vec3(0.0, 0.0, phosphor);

		// Add base so gaps aren't pure black
		mask = mask * intensity + vec3(1.0 - intensity);
	}
	else if (mask_type == 1) {
		// Slot mask - staggered RGB pattern
		float row = mod(floor(pos.y * screen_size.y / screen_size.x), 2.0);
		float col = mod(floor(pos.x + row * 1.5), 3.0);

		float sub_pos = fract(pos.x);
		float dist = abs(sub_pos - 0.5) * 2.0;
		float phosphor = 1.0 - smoothstep(dot_width, dot_width + 0.2, dist);

		if (col == 0.0) mask = vec3(phosphor, 0.0, 0.0);
		else if (col == 1.0) mask = vec3(0.0, phosphor, 0.0);
		else mask = vec3(0.0, 0.0, phosphor);

		mask = mask * intensity + vec3(1.0 - intensity);
	}
	else if (mask_type == 2) {
		// Shadow mask - delta triad dots
		float pos_y = texcoord.y * line_density * screen_size.y / screen_size.x;
		float row = mod(floor(pos_y), 3.0);
		float col = mod(floor(pos.x + row), 3.0);

		float dist_x = abs(fract(pos.x) - 0.5) * 2.0;
		float dist_y = abs(fract(pos_y) - 0.5) * 2.0;
		float dist = max(dist_x, dist_y);
		float phosphor = 1.0 - smoothstep(dot_width, dot_width + 0.2, dist);

		if (col == 0.0) mask = vec3(phosphor, 0.0, 0.0);
		else if (col == 1.0) mask = vec3(0.0, phosphor, 0.0);
		else mask = vec3(0.0, 0.0, phosphor);

		mask = mask * intensity + vec3(1.0 - intensity);
	}
	else if (mask_type == 3) {
		// Simple vertical dark lines (no RGB)
		float sub_pos = fract(pos.x);
		float dist = abs(sub_pos - 0.5) * 2.0;
		float line = smoothstep(dot_width, dot_width + 0.2, dist);
		mask = vec3(1.0 - line * intensity);
	}

	color *= mask * brightness;

	if (debug_mode == 1) {
		frag_color = vec4(mask, 1.0);
		return;
	}

	frag_color = vec4(clamp(color, 0.0, 1.0), 1.0);
}
"""

class ShadowMask(StackEffect):
	"""
	Shadow mask / phosphor pattern effect.

	Creates the RGB phosphor patterns seen on CRT monitors.

	Parameters:
		mask_type: 0 = aperture grille (vertical RGB stripes, like Trinitron)
		           1 = slot mask (staggered RGB)
		           2 = shadow mask (delta triad dots)
		           3 = simple vertical bars (dark lines, no RGB)
		line_density: Number of RGB triplets across screen width
		              640 = 640 triplets (fine), 320 = coarser, 1280 = very fine
		intensity: Strength of the mask (0-1)
		dot_width: Width of each phosphor (0.1 = thin, 0.5 = medium, 0.9 = thick)
		brightness: Brightness compensation
	"""

	def __init__(self, mask_type=0, line_density=640.0, intensity=0.5,
							 dot_width=0.4, brightness=1.5,
							 enabled=True, debug=False):
		super().__init__("shadow_mask", SHADOWMASK_FRAG, StackEffect.TRANSFORM)
		self.mask_type = mask_type
		self.line_density = line_density
		self.intensity = intensity
		self.dot_width = dot_width
		self.brightness = brightness
		self.enabled = enabled
		self.debug = debug

	def apply(self):
		self.set_shader_input("mask_type", self.mask_type)
		self.set_shader_input("line_density", self.line_density)
		self.set_shader_input("intensity", self.intensity)
		self.set_shader_input("dot_width", self.dot_width)
		self.set_shader_input("brightness", self.brightness)
		self.set_shader_input("debug_mode", 1 if self.debug else 0)