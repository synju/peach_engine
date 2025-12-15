from engine.effects.post_processing_stack import StackEffect
from panda3d.core import Vec4

LINEAR_FOG_FRAG = """
#version 330

uniform sampler2D scene_tex;
uniform sampler2D depth_tex;
uniform vec2 screen_size;
uniform vec4 fog_color;
uniform float fog_start;
uniform float fog_end;
uniform float fog_density;
uniform float near_plane;
uniform float far_plane;
uniform int debug_mode;

in vec2 texcoord;
out vec4 frag_color;

void main() {
	// Debug: just show fog color
	if (debug_mode == 1) {
		frag_color = vec4(fog_color.rgb, 1.0);
		return;
	}

	// Debug: show scene texture
	if (debug_mode == 2) {
		frag_color = texture(scene_tex, texcoord);
		return;
	}

	vec3 scene_color = texture(scene_tex, texcoord).rgb;
	float depth_raw = texture(depth_tex, texcoord).r;

	// Linearize depth
	float linear_depth = near_plane * far_plane / (far_plane - depth_raw * (far_plane - near_plane));

	// Linear fog factor (0 at start, 1 at end and beyond)
	float fog_factor = clamp((linear_depth - fog_start) / (fog_end - fog_start), 0.0, 1.0);

	// Apply density curve (density=1.0 means linear, higher = fog builds faster)
	float fog_amount = pow(fog_factor, 1.0 / fog_density);

	// Blend fog with scene
	vec3 final_color = mix(scene_color, fog_color.rgb, fog_amount);
	frag_color = vec4(final_color, 1.0);
}
"""

class LinearFog(StackEffect):
	"""
	Linear distance fog as a post-processing effect.

	Parameters:
		color: Fog color (r, g, b)
		start: Distance where fog starts
		end: Distance where fog is fully opaque
		density: Fog density multiplier
		debug: 0=off, 1=show fog color only, 2=show scene only
	"""

	def __init__(self, color=(1.0, 1.0, 1.0), start=0.0, end=100.0, density=1.0,
							 enabled=True, debug=0):
		super().__init__("linear_fog", LINEAR_FOG_FRAG, StackEffect.TRANSFORM)
		self.color = list(color)
		self.start = start
		self.end = end
		self.density = density
		self.enabled = enabled
		self.debug = debug

	def apply(self):
		self.set_shader_input("fog_color", Vec4(*self.color, 1.0))
		self.set_shader_input("fog_start", self.start)
		self.set_shader_input("fog_end", self.end)
		self.set_shader_input("fog_density", self.density)
		self.set_shader_input("debug_mode", self.debug)