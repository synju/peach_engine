from engine.effects.post_processing_stack import StackEffect

CRT_NEWPIXIE_FRAG = """
#version 330

uniform sampler2D scene_tex;
uniform vec2 screen_size;
uniform float time;

uniform float accumulate;
uniform float blur_x;
uniform float blur_y;
uniform float curvature;
uniform float interference;
uniform float rolling_scanlines;
uniform float brightness;

in vec2 texcoord;
out vec4 frag_color;

float hash(vec2 p) {
	vec3 p3 = fract(vec3(p.xyx) * 0.1031);
	p3 += dot(p3, p3.yzx + 33.33);
	return fract((p3.x + p3.y) * p3.z);
}

vec2 curve(vec2 uv, float amount) {
	if (amount < 0.0001) return uv;
	uv = uv * 2.0 - 1.0;
	vec2 offset = abs(uv.yx) / vec2(amount);
	uv = uv + uv * offset * offset;
	uv = uv * 0.5 + 0.5;
	return uv;
}

vec3 blur_sample(vec2 uv, vec2 blur_size) {
	vec3 col = vec3(0.0);
	float total = 0.0;
	for (float x = -2.0; x <= 2.0; x += 1.0) {
		for (float y = -2.0; y <= 2.0; y += 1.0) {
			float weight = 1.0 - length(vec2(x, y)) * 0.15;
			weight = max(weight, 0.0);
			col += texture(scene_tex, uv + vec2(x * blur_size.x, y * blur_size.y)).rgb * weight;
			total += weight;
		}
	}
	return col / total;
}

void main() {
	vec2 uv = curve(texcoord, curvature);

	if (uv.x < 0.0 || uv.x > 1.0 || uv.y < 0.0 || uv.y > 1.0) {
		frag_color = vec4(0.0, 0.0, 0.0, 1.0);
		return;
	}

	vec2 pixel_size = 1.0 / screen_size;
	vec2 blur_amount = vec2(blur_x, blur_y) * pixel_size;

	vec3 color;
	if (blur_x > 0.01 || blur_y > 0.01) {
		color = blur_sample(uv, blur_amount);
	} else {
		color = texture(scene_tex, uv).rgb;
	}

	if (accumulate > 0.01) {
		vec3 prev = texture(scene_tex, uv + vec2(pixel_size.x * 0.5, 0.0)).rgb;
		color = mix(color, (color + prev) * 0.5, accumulate);
	}

	if (interference > 0.001) {
		float noise = hash(uv * screen_size + time * 1000.0);
		noise = (noise - 0.5) * interference;
		color += noise;
	}

	if (rolling_scanlines > 0.01) {
		float roll = sin(uv.y * 50.0 + time * 10.0 * rolling_scanlines) * 0.01 * rolling_scanlines;
		color.r = texture(scene_tex, uv + vec2(roll, 0.0)).r;
	}

	color *= brightness;
	frag_color = vec4(clamp(color, 0.0, 1.0), 1.0);
}
"""

class CRTNewPixie(StackEffect):
	"""CRT NewPixie: blur, phosphor persistence, interference"""

	def __init__(self, accumulate=0.5, blur_x=2.0, blur_y=0.0, curvature=0.0,
							 interference=0.0, rolling_scanlines=0.0, brightness=1.0, enabled=True):
		super().__init__("crt_newpixie", CRT_NEWPIXIE_FRAG, StackEffect.TRANSFORM)
		self.accumulate = accumulate
		self.blur_x = blur_x
		self.blur_y = blur_y
		self.curvature = curvature
		self.interference = interference
		self.rolling_scanlines = rolling_scanlines
		self.brightness = brightness
		self.enabled = enabled
		self._time = 0.0

	def apply(self):
		self.set_shader_input("accumulate", self.accumulate)
		self.set_shader_input("blur_x", self.blur_x)
		self.set_shader_input("blur_y", self.blur_y)
		self.set_shader_input("curvature", self.curvature)
		self.set_shader_input("interference", self.interference)
		self.set_shader_input("rolling_scanlines", self.rolling_scanlines)
		self.set_shader_input("brightness", self.brightness)
		self.set_shader_input("time", self._time)

	def update(self, dt):
		self._time += dt
