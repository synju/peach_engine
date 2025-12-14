from engine.effects.post_processing_stack import StackEffect

CRT_LOTTES_FRAG = """
#version 330

uniform sampler2D scene_tex;
uniform vec2 screen_size;

uniform int mask_type;
uniform float mask_strength;
uniform float scanline_strength;
uniform float scanline_count;
uniform float scanline_hardness;
uniform float bloom_amount;
uniform float bloom_radius;
uniform float curvature;
uniform float corner_radius;
uniform float brightness;
uniform float saturation;
uniform float vignette;
uniform int debug_mode;

in vec2 texcoord;
out vec4 frag_color;

vec2 warp(vec2 uv, float amount) {
	if (amount < 0.0001) return uv;
	uv = uv * 2.0 - 1.0;
	vec2 offset = abs(uv.yx) / vec2(amount);
	uv = uv + uv * offset * offset;
	uv = uv * 0.5 + 0.5;
	return uv;
}

float corner_mask(vec2 uv, float radius) {
	if (radius < 0.001) return 1.0;
	uv = abs(uv * 2.0 - 1.0) - (1.0 - radius);
	uv = max(uv, 0.0) / radius;
	return 1.0 - smoothstep(0.8, 1.0, length(uv));
}

vec3 aperture_grille(vec2 pos) {
	float col = mod(pos.x, 3.0);
	if (col < 1.0) return vec3(1.0, 0.0, 0.0);
	if (col < 2.0) return vec3(0.0, 1.0, 0.0);
	return vec3(0.0, 0.0, 1.0);
}

vec3 slot_mask(vec2 pos) {
	float row = mod(floor(pos.y), 2.0);
	float col = mod(pos.x + row * 1.5, 3.0);
	if (col < 1.0) return vec3(1.0, 0.0, 0.0);
	if (col < 2.0) return vec3(0.0, 1.0, 0.0);
	return vec3(0.0, 0.0, 1.0);
}

vec3 shadow_mask(vec2 pos) {
	float row = mod(floor(pos.y), 3.0);
	float col = mod(pos.x + row, 3.0);
	if (col < 1.0) return vec3(1.0, 0.0, 0.0);
	if (col < 2.0) return vec3(0.0, 1.0, 0.0);
	return vec3(0.0, 0.0, 1.0);
}

vec3 get_mask(vec2 pos, int type) {
	if (type == 1) return aperture_grille(pos);
	if (type == 2) return slot_mask(pos);
	if (type == 3) return shadow_mask(pos);
	return vec3(1.0);
}

vec3 bloom_sample(vec2 uv, float radius) {
	vec2 pixel_size = 1.0 / screen_size;
	vec3 bloom = vec3(0.0);
	float total = 0.0;
	for (float x = -3.0; x <= 3.0; x += 1.0) {
		for (float y = -3.0; y <= 3.0; y += 1.0) {
			float weight = 1.0 - length(vec2(x, y)) / 5.0;
			weight = max(weight, 0.0);
			weight = weight * weight;
			bloom += texture(scene_tex, uv + vec2(x, y) * pixel_size * radius).rgb * weight;
			total += weight;
		}
	}
	return bloom / total;
}

void main() {
	vec2 uv = warp(texcoord, curvature);

	if (uv.x < 0.0 || uv.x > 1.0 || uv.y < 0.0 || uv.y > 1.0) {
		frag_color = vec4(0.0, 0.0, 0.0, 1.0);
		return;
	}

	float corners = corner_mask(uv, corner_radius);
	if (corners < 0.01) {
		frag_color = vec4(0.0, 0.0, 0.0, 1.0);
		return;
	}

	vec3 color = texture(scene_tex, uv).rgb;

	if (bloom_amount > 0.01) {
		vec3 bloom = bloom_sample(uv, bloom_radius);
		color += bloom * bloom_amount;
	}

	color *= brightness;

	float luma = dot(color, vec3(0.299, 0.587, 0.114));
	color = mix(vec3(luma), color, saturation);

	vec2 screen_pos = uv * screen_size;

	float scan_y = uv.y * scanline_count;
	float scanline = sin(scan_y * 3.14159);
	scanline = sign(scanline) * pow(abs(scanline), 1.0 / scanline_hardness);
	scanline = scanline * 0.5 + 0.5;
	scanline = scanline * scanline_strength + (1.0 - scanline_strength);
	color *= scanline;

	if (mask_type > 0 && mask_strength > 0.01) {
		vec3 mask = get_mask(screen_pos, mask_type);
		mask = mix(vec3(1.0), mask, mask_strength);
		color *= mask;
	}

	if (vignette > 0.001) {
		vec2 vig_uv = uv * 2.0 - 1.0;
		float vig = 1.0 - dot(vig_uv, vig_uv) * vignette;
		color *= max(vig, 0.0);
	}

	color *= corners;

	if (debug_mode == 1) {
		vec3 mask = get_mask(screen_pos, mask_type);
		frag_color = vec4(mask, 1.0);
		return;
	}
	if (debug_mode == 2) {
		frag_color = vec4(scanline, scanline, scanline, 1.0);
		return;
	}

	frag_color = vec4(clamp(color, 0.0, 1.0), 1.0);
}
"""

class CRTLottes(StackEffect):
	"""CRT Lottes: masks, scanlines, bloom, curvature"""

	def __init__(self, mask_type=1, mask_strength=0.3, scanline_strength=0.3,
							 scanline_count=240.0, scanline_hardness=2.0, bloom_amount=0.0,
							 bloom_radius=2.0, curvature=6.0, corner_radius=0.0,
							 brightness=1.0, saturation=1.0, vignette=0.0, enabled=True, debug=False):
		super().__init__("crt_lottes", CRT_LOTTES_FRAG, StackEffect.TRANSFORM)
		self.mask_type = mask_type
		self.mask_strength = mask_strength
		self.scanline_strength = scanline_strength
		self.scanline_count = scanline_count
		self.scanline_hardness = scanline_hardness
		self.bloom_amount = bloom_amount
		self.bloom_radius = bloom_radius
		self.curvature = curvature
		self.corner_radius = corner_radius
		self.brightness = brightness
		self.saturation = saturation
		self.vignette = vignette
		self.enabled = enabled
		self.debug = debug

	def apply(self):
		self.set_shader_input("mask_type", self.mask_type)
		self.set_shader_input("mask_strength", self.mask_strength)
		self.set_shader_input("scanline_strength", self.scanline_strength)
		self.set_shader_input("scanline_count", self.scanline_count)
		self.set_shader_input("scanline_hardness", self.scanline_hardness)
		self.set_shader_input("bloom_amount", self.bloom_amount)
		self.set_shader_input("bloom_radius", self.bloom_radius)
		self.set_shader_input("curvature", self.curvature)
		self.set_shader_input("corner_radius", self.corner_radius)
		self.set_shader_input("brightness", self.brightness)
		self.set_shader_input("saturation", self.saturation)
		self.set_shader_input("vignette", self.vignette)
		self.set_shader_input("debug_mode", 1 if self.debug == True else (2 if self.debug == 2 else 0))
