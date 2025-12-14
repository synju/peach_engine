from engine.effects.post_processing_stack import StackEffect

SCANLINES_FRAG = """
#version 330

uniform vec2 screen_size;
uniform float time;
uniform float line_count;
uniform float thickness;
uniform float opacity;
uniform float scroll_speed;
uniform float softness;
uniform int direction;  // 0 = horizontal, 1 = vertical
uniform int debug_mode;

in vec2 texcoord;
out vec4 frag_color;

void main() {
	float coord;

	if (direction == 0) {
		coord = texcoord.y;
	} else {
		coord = texcoord.x;
	}

	// Scroll in terms of lines per second
	float scroll = time * scroll_speed / line_count;
	float line_pos = fract((coord + scroll) * line_count);

	// Smooth the edges to prevent aliasing/flickering
	// softness controls the edge blur
	float edge = softness * 0.5;
	float scanline = smoothstep(thickness - edge, thickness + edge, line_pos);

	if (debug_mode == 1) {
		frag_color = vec4(scanline, scanline, scanline, 1.0);
		return;
	}

	// Output as overlay - dark lines with opacity
	float darkness = (1.0 - scanline) * opacity;
	frag_color = vec4(0.0, 0.0, 0.0, darkness);
}
"""

class Scanlines(StackEffect):
	"""
	Scanlines effect with scrolling animation.

	Parameters:
		line_count: Number of scanlines (default 240 for NTSC)
		thickness: Line thickness 0-1 (0.5 = half dark, half light)
		opacity: How dark the lines are 0-1
		scroll_speed: Lines per second (0 = static, 10 = 10 lines/sec, negative = reverse)
		softness: Edge softness to prevent flickering (0.1-0.5 recommended)
		direction: 0 = horizontal, 1 = vertical
	"""

	def __init__(self, line_count=240.0, thickness=0.5, opacity=0.3,
							 scroll_speed=0.0, softness=0.3, direction=0, enabled=True, debug=False):
		super().__init__("scanlines", SCANLINES_FRAG, StackEffect.OVERLAY)
		self.line_count = line_count
		self.thickness = thickness
		self.opacity = opacity
		self.scroll_speed = scroll_speed
		self.softness = softness
		self.direction = direction
		self.enabled = enabled
		self.debug = debug
		self._time = 0.0

	def apply(self):
		self.set_shader_input("line_count", self.line_count)
		self.set_shader_input("thickness", self.thickness)
		self.set_shader_input("opacity", self.opacity)
		self.set_shader_input("scroll_speed", self.scroll_speed)
		self.set_shader_input("softness", self.softness)
		self.set_shader_input("direction", self.direction)
		self.set_shader_input("time", self._time)
		self.set_shader_input("debug_mode", 1 if self.debug else 0)

	def update(self, dt):
		self._time += dt