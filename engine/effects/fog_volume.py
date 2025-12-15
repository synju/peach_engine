from engine.effects.post_processing_stack import StackEffect
from panda3d.core import Vec3, Vec4, Mat4
from direct.showbase.ShowBase import ShowBase

base: ShowBase

VOLUME_FOG_FRAG = """
#version 330

uniform sampler2D scene_tex;
uniform sampler2D depth_tex;
uniform vec2 screen_size;
uniform vec3 camera_pos;
uniform mat4 inv_view_proj;
uniform vec3 box_min;
uniform vec3 box_max;
uniform vec4 fog_color;
uniform float fog_density;
uniform float near_plane;
uniform float far_plane;

in vec2 texcoord;
out vec4 frag_color;

vec2 intersect_box(vec3 ray_origin, vec3 ray_dir) {
	vec3 t1 = (box_min - ray_origin) / ray_dir;
	vec3 t2 = (box_max - ray_origin) / ray_dir;

	vec3 t_min = min(t1, t2);
	vec3 t_max = max(t1, t2);

	float enter = max(max(t_min.x, t_min.y), t_min.z);
	float exit_val = min(min(t_max.x, t_max.y), t_max.z);

	return vec2(enter, exit_val);
}

bool point_in_box(vec3 p) {
	return all(greaterThanEqual(p, box_min - 0.01)) && all(lessThanEqual(p, box_max + 0.01));
}

void main() {
	vec3 scene_color = texture(scene_tex, texcoord).rgb;
	float depth_raw = texture(depth_tex, texcoord).r;

	// Reconstruct world position from depth
	vec2 ndc = texcoord * 2.0 - 1.0;
	vec4 clip_pos = vec4(ndc, depth_raw * 2.0 - 1.0, 1.0);
	vec4 world_pos = inv_view_proj * clip_pos;
	world_pos /= world_pos.w;

	// Ray from camera to this pixel
	vec3 ray_dir = normalize(world_pos.xyz - camera_pos);

	// Linearize depth for scene distance
	float linear_depth = near_plane * far_plane / (far_plane - depth_raw * (far_plane - near_plane));
	float scene_dist = length(world_pos.xyz - camera_pos);

	// Intersect ray with fog box
	vec2 t = intersect_box(camera_pos, ray_dir);

	// No intersection or behind camera
	if (t.x > t.y || t.y < 0.0) {
		frag_color = vec4(scene_color, 1.0);
		return;
	}

	// Handle camera inside box
	bool inside = point_in_box(camera_pos);
	float entry_dist = inside ? 0.0 : max(t.x, 0.0);
	float exit_dist = t.y;

	// Clamp exit to scene geometry
	exit_dist = min(exit_dist, scene_dist);

	// No fog if geometry is before fog volume
	if (exit_dist <= entry_dist) {
		frag_color = vec4(scene_color, 1.0);
		return;
	}

	// Calculate fog amount based on distance through volume
	float fog_dist = exit_dist - entry_dist;
	float fog_amount = 1.0 - exp(-fog_density * fog_dist);

	// Blend fog with scene
	vec3 final_color = mix(scene_color, fog_color.rgb, fog_amount);
	frag_color = vec4(final_color, 1.0);
}
"""

class VolumeFog(StackEffect):
	"""
	Localized fog volume (Q3 Arena style).

	Parameters:
		position: Center of the fog volume (x, y, z)
		size: Size of the volume (x, y, z) or single value for cube
		color: Fog color (r, g, b)
		density: Fog density
	"""

	def __init__(self, position=(0, 0, 0), size=(10, 10, 10), color=(0.5, 0.5, 0.5),
							 density=0.1, enabled=True):
		super().__init__("volume_fog", VOLUME_FOG_FRAG, StackEffect.TRANSFORM)
		self.position = list(position)
		self.size = list(size) if isinstance(size, (list, tuple)) else [size, size, size]
		self.color = list(color)
		self.density = density
		self.enabled = enabled

	def apply(self):
		# Calculate box bounds
		px, py, pz = self.position
		sx, sy, sz = self.size[0] / 2, self.size[1] / 2, self.size[2] / 2

		box_min = Vec3(px - sx, py - sy, pz - sz)
		box_max = Vec3(px + sx, py + sy, pz + sz)

		self.set_shader_input("box_min", box_min)
		self.set_shader_input("box_max", box_max)
		self.set_shader_input("fog_color", Vec4(*self.color, 1.0))
		self.set_shader_input("fog_density", self.density)

		# Camera info
		self.set_shader_input("camera_pos", base.camera.getPos(base.render))

		# Get inverse view-projection matrix
		view_mat = base.camera.getMat(base.render)
		proj_mat = base.camLens.getProjectionMat()
		view_proj = view_mat * proj_mat
		inv_view_proj = Mat4()
		inv_view_proj.invertFrom(view_proj)
		self.set_shader_input("inv_view_proj", inv_view_proj)