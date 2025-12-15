from engine.effects.post_processing_stack import StackEffect
from panda3d.core import Vec4

DISTANCE_FOG_FRAG = """
#version 330

uniform sampler2D scene_tex;
uniform sampler2D depth_tex;
uniform vec2 screen_size;
uniform vec4 fog_color;
uniform float fog_density;
uniform float near_plane;
uniform float far_plane;

in vec2 texcoord;
out vec4 frag_color;

void main() {
	vec3 scene_color = texture(scene_tex, texcoord).rgb;
	float depth_raw = texture(depth_tex, texcoord).r;

	// Linearize depth
	float linear_depth = near_plane * far_plane / (far_plane - depth_raw * (far_plane - near_plane));

	// Exponential fog
	float fog_amount = 1.0 - exp(-fog_density * linear_depth);

	// Blend fog with scene
	vec3 final_color = mix(scene_color, fog_color.rgb, fog_amount);
	frag_color = vec4(final_color, 1.0);
}
"""

class DistanceFog(StackEffect):
	"""
	Exponential distance fog (Silent Hill style).

	Parameters:
		color: Fog color (r, g, b)
		density: Fog density (higher = thicker fog closer)
	"""

	def __init__(self, color=(0.5, 0.5, 0.5), density=0.03, enabled=True):
		super().__init__("distance_fog", DISTANCE_FOG_FRAG, StackEffect.TRANSFORM)
		self.color = list(color)
		self.density = density
		self.enabled = enabled

	def apply(self):
		self.set_shader_input("fog_color", Vec4(*self.color, 1.0))
		self.set_shader_input("fog_density", self.density)