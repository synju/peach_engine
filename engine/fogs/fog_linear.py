from direct.showbase.ShowBase import ShowBase
from panda3d.core import (
	NodePath, Vec4, CardMaker,
	Shader, TransparencyAttrib
)

base: ShowBase

LINEAR_FOG_VERT = """
#version 330

uniform mat4 p3d_ModelViewProjectionMatrix;

in vec4 p3d_Vertex;
in vec2 p3d_MultiTexCoord0;

out vec2 texcoord;

void main() {
	gl_Position = p3d_ModelViewProjectionMatrix * p3d_Vertex;
	texcoord = p3d_MultiTexCoord0;
}
"""

LINEAR_FOG_FRAG = """
#version 330

uniform sampler2D depth_tex;
uniform vec4 fog_color;
uniform float fog_start;
uniform float fog_end;
uniform float fog_density;
uniform float near_plane;
uniform float far_plane;

in vec2 texcoord;

out vec4 frag_color;

void main() {
	float depth_raw = texture(depth_tex, texcoord).r;

	// Linearize depth
	float linear_depth = near_plane * far_plane / (far_plane - depth_raw * (far_plane - near_plane));

	// Linear fog with density curve
	float fog_factor = clamp((linear_depth - fog_start) / (fog_end - fog_start), 0.0, 1.0);
	float fog_amount = 1.0 - exp(-fog_density * fog_factor * 3.0);

	frag_color = vec4(fog_color.rgb, fog_amount);
}
"""


class LinearDistanceFog:
	"""Linear distance fog using depth buffer - works with simplepbr"""

	def __init__(self, engine, name='linear_fog', color=(0.5, 0.5, 0.5),
				 start=10.0, end=100.0, density=1.0, fog_enabled=True):
		self.engine = engine
		self.name = name
		self._color = list(color)
		self._start = start
		self._end = end
		self._density = density
		self._enabled = fog_enabled

		self._quad = None
		self._shader = None
		self._depth_tex = None

		self._setup_depth_texture()
		self._create_quad()

		if not self._enabled:
			self._quad.hide()

	def _setup_depth_texture(self):
		"""Get depth texture from renderer (simplepbr's buffer)"""
		self._depth_tex = self.engine.renderer.depth_tex

	def _create_quad(self):
		"""Create fullscreen quad for fog rendering"""
		cm = CardMaker('linear_fog_quad')
		cm.setFrameFullscreenQuad()

		self._quad = NodePath(cm.generate())
		self._quad.reparentTo(base.render2d)

		self._shader = Shader.make(Shader.SL_GLSL, LINEAR_FOG_VERT, LINEAR_FOG_FRAG)
		self._quad.setShader(self._shader)
		self._quad.setTransparency(TransparencyAttrib.MAlpha)
		self._quad.setBin("fixed", 50)

		self._update_shader_inputs()

	def _update_shader_inputs(self):
		"""Update shader uniforms"""
		if not self._quad:
			return

		self._quad.setShaderInput("depth_tex", self._depth_tex)
		self._quad.setShaderInput("fog_color", Vec4(*self._color, 1.0))
		self._quad.setShaderInput("fog_start", self._start)
		self._quad.setShaderInput("fog_end", self._end)
		self._quad.setShaderInput("fog_density", self._density)

		lens = base.camLens
		self._quad.setShaderInput("near_plane", lens.getNear())
		self._quad.setShaderInput("far_plane", lens.getFar())

	def update(self):
		"""Update per-frame (call if near/far planes change)"""
		if not self._quad or not self._enabled:
			return

		lens = base.camLens
		self._quad.setShaderInput("near_plane", lens.getNear())
		self._quad.setShaderInput("far_plane", lens.getFar())

	@property
	def color(self):
		return self._color

	@color.setter
	def color(self, value):
		self._color = list(value)
		if self._quad:
			self._quad.setShaderInput("fog_color", Vec4(*self._color, 1.0))

	@property
	def start(self):
		return self._start

	@start.setter
	def start(self, value):
		self._start = value
		if self._quad:
			self._quad.setShaderInput("fog_start", self._start)

	@property
	def end(self):
		return self._end

	@end.setter
	def end(self, value):
		self._end = value
		if self._quad:
			self._quad.setShaderInput("fog_end", self._end)

	@property
	def density(self):
		return self._density

	@density.setter
	def density(self, value):
		self._density = value
		if self._quad:
			self._quad.setShaderInput("fog_density", self._density)

	@property
	def enabled(self):
		return self._enabled

	@enabled.setter
	def enabled(self, value):
		self._enabled = value
		if self._quad:
			if value:
				self._quad.show()
			else:
				self._quad.hide()

	def set_range(self, start, end):
		"""Set fog start and end distance"""
		self._start = start
		self._end = end
		if self._quad:
			self._quad.setShaderInput("fog_start", self._start)
			self._quad.setShaderInput("fog_end", self._end)

	def turn_on(self):
		self.enabled = True

	def turn_off(self):
		self.enabled = False

	def destroy(self):
		if self._quad:
			self._quad.removeNode()
			self._quad = None