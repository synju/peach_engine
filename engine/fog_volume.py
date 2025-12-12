from direct.showbase.ShowBase import ShowBase
from panda3d.core import (
	NodePath, Vec4, Vec3, Vec2,
	GeomVertexFormat, GeomVertexData, GeomVertexWriter,
	Geom, GeomTriangles, GeomLines, GeomNode,
	Shader, Texture, TransparencyAttrib,
	CullFaceAttrib, GraphicsOutput
)

base: ShowBase

# Vertex shader for fog volume
FOG_VOLUME_VERT = """
#version 330

uniform mat4 p3d_ModelViewProjectionMatrix;
uniform mat4 p3d_ModelMatrix;

in vec4 p3d_Vertex;

out vec3 world_pos;

void main() {
	world_pos = (p3d_ModelMatrix * p3d_Vertex).xyz;
	gl_Position = p3d_ModelViewProjectionMatrix * p3d_Vertex;
}
"""

# Fragment shader for fog volume - calculates depth through volume
FOG_VOLUME_FRAG = """
#version 330

uniform vec3 camera_pos;
uniform vec3 camera_forward;
uniform vec3 box_min;
uniform vec3 box_max;
uniform vec4 fog_color;
uniform float fog_density;
uniform sampler2D depth_tex;
uniform vec2 screen_size;
uniform float near_plane;
uniform float far_plane;

in vec3 world_pos;

out vec4 frag_color;

vec2 intersect_box(vec3 ray_origin, vec3 ray_dir) {
	vec3 t1 = (box_min - ray_origin) / ray_dir;
	vec3 t2 = (box_max - ray_origin) / ray_dir;

	vec3 t_min = min(t1, t2);
	vec3 t_max = max(t1, t2);

	float enter = max(max(t_min.x, t_min.y), t_min.z);
	float exit = min(min(t_max.x, t_max.y), t_max.z);

	return vec2(enter, exit);
}

bool point_in_box(vec3 p) {
	return all(greaterThan(p, box_min - 0.01)) && all(lessThan(p, box_max + 0.01));
}

void main() {
	vec3 ray_dir = normalize(world_pos - camera_pos);
	vec2 t = intersect_box(camera_pos, ray_dir);

	if (t.x > t.y || t.y < 0.0) {
		discard;
	}

	// Get scene depth
	vec2 screen_uv = gl_FragCoord.xy / screen_size;
	float depth_raw = texture(depth_tex, screen_uv).r;

	// Linearize depth to get view-space Z
	float scene_z = near_plane * far_plane / (far_plane - depth_raw * (far_plane - near_plane));

	// Convert view-space Z to world distance along ray
	float cos_angle = abs(dot(ray_dir, camera_forward));
	float scene_dist = scene_z / max(cos_angle, 0.0001);

	// Entry/exit distances along ray
	bool inside = point_in_box(camera_pos);
	float entry_dist = inside ? 0.0 : max(t.x, 0.0);
	float exit_dist = t.y;

	// Clamp to scene geometry
	exit_dist = min(exit_dist, scene_dist);

	// No fog if scene is in front of fog entry
	if (exit_dist <= entry_dist) {
		discard;
	}

	float fog_dist = exit_dist - entry_dist;
	float fog_amount = 1.0 - exp(-fog_density * fog_dist);

	frag_color = vec4(fog_color.rgb, fog_amount);
}
"""


class FogVolume:
	"""Q3-style fog volume - depth-aware fog within a defined box region"""

	def __init__(self, engine, name='fog_volume', position=(0, 0, 0), size=(10, 10, 10),
				 color=(0.5, 0.5, 0.5), density=0.1, fog_enabled=True, debug_mode=False):
		self.engine = engine
		self.name = name
		self._position = list(position)
		self._size = list(size) if isinstance(size, (list, tuple)) else [size, size, size]
		self._color = list(color)
		self._density = density
		self._enabled = fog_enabled
		self.debug_mode = debug_mode

		self.node = None
		self._debug_node = None
		self._fog_node = None
		self._shader = None
		self._depth_tex = None

		self._setup_depth_texture()
		self._create_volume()

		if self.debug_mode:
			self._create_debug_wireframe()

	def _setup_depth_texture(self):
		"""Setup access to the depth buffer"""
		self._depth_tex = Texture("depth")
		base.win.addRenderTexture(
			self._depth_tex,
			GraphicsOutput.RTMBindOrCopy,
			GraphicsOutput.RTPDepth
		)

	def _create_volume(self):
		"""Create the fog volume geometry with shader"""
		self.node = NodePath(self.name)
		self.node.reparentTo(base.render)
		self.node.setPos(*self._position)

		self._fog_node = self._create_box_geom()
		self._fog_node.reparentTo(self.node)

		self._shader = Shader.make(Shader.SL_GLSL, FOG_VOLUME_VERT, FOG_VOLUME_FRAG)
		self._fog_node.setShader(self._shader)

		self._fog_node.setTransparency(TransparencyAttrib.MAlpha)
		self._fog_node.setDepthWrite(False)
		self._fog_node.setDepthTest(False)
		self._fog_node.setAttrib(CullFaceAttrib.make(CullFaceAttrib.MCullClockwise))
		self._fog_node.setBin("transparent", 10)

		self._update_shader_inputs()

		if not self._enabled:
			self._fog_node.hide()

	def _update_shader_inputs(self):
		"""Update all shader uniforms"""
		if not self._fog_node:
			return

		px, py, pz = self._position
		sx, sy, sz = self._size[0] / 2, self._size[1] / 2, self._size[2] / 2

		box_min = Vec3(px - sx, py - sy, pz - sz)
		box_max = Vec3(px + sx, py + sy, pz + sz)

		self._fog_node.setShaderInput("box_min", box_min)
		self._fog_node.setShaderInput("box_max", box_max)
		self._fog_node.setShaderInput("fog_color", Vec4(*self._color, 1.0))
		self._fog_node.setShaderInput("fog_density", self._density)
		self._fog_node.setShaderInput("depth_tex", self._depth_tex)
		self._fog_node.setShaderInput("screen_size", Vec2(base.win.getXSize(), base.win.getYSize()))
		self._fog_node.setShaderInput("camera_pos", base.camera.getPos(base.render))
		self._fog_node.setShaderInput("camera_forward", base.camera.getQuat(base.render).getForward())

		lens = base.camLens
		self._fog_node.setShaderInput("near_plane", lens.getNear())
		self._fog_node.setShaderInput("far_plane", lens.getFar())

	def _create_box_geom(self):
		"""Create a box mesh for the fog volume"""
		format = GeomVertexFormat.get_v3()
		vdata = GeomVertexData('fog_box', format, Geom.UHStatic)
		vdata.setNumRows(8)

		vertex = GeomVertexWriter(vdata, 'vertex')

		sx, sy, sz = self._size[0] / 2, self._size[1] / 2, self._size[2] / 2

		corners = [
			(-sx, -sy, -sz),
			(sx, -sy, -sz),
			(sx, sy, -sz),
			(-sx, sy, -sz),
			(-sx, -sy, sz),
			(sx, -sy, sz),
			(sx, sy, sz),
			(-sx, sy, sz),
		]

		for corner in corners:
			vertex.addData3(*corner)

		tris = GeomTriangles(Geom.UHStatic)

		faces = [
			(0, 1, 2, 2, 3, 0),
			(4, 7, 6, 6, 5, 4),
			(0, 4, 5, 5, 1, 0),
			(2, 6, 7, 7, 3, 2),
			(0, 3, 7, 7, 4, 0),
			(1, 5, 6, 6, 2, 1),
		]

		for face in faces:
			for idx in face:
				tris.addVertex(idx)
			tris.closePrimitive()

		geom = Geom(vdata)
		geom.addPrimitive(tris)

		node = GeomNode('fog_geom')
		node.addGeom(geom)

		return NodePath(node)

	def _create_debug_wireframe(self):
		"""Create wireframe box for debug visualization"""
		if self._debug_node:
			self._debug_node.removeNode()

		format = GeomVertexFormat.get_v3c4()
		vdata = GeomVertexData('debug_wire', format, Geom.UHStatic)
		vdata.setNumRows(8)

		vertex = GeomVertexWriter(vdata, 'vertex')
		color = GeomVertexWriter(vdata, 'color')

		sx, sy, sz = self._size[0] / 2, self._size[1] / 2, self._size[2] / 2

		corners = [
			(-sx, -sy, -sz),
			(sx, -sy, -sz),
			(sx, sy, -sz),
			(-sx, sy, -sz),
			(-sx, -sy, sz),
			(sx, -sy, sz),
			(sx, sy, sz),
			(-sx, sy, sz),
		]

		for corner in corners:
			vertex.addData3(*corner)
			color.addData4(1, 0.5, 0, 1)

		lines = GeomLines(Geom.UHStatic)

		edges = [
			(0, 1), (1, 2), (2, 3), (3, 0),
			(4, 5), (5, 6), (6, 7), (7, 4),
			(0, 4), (1, 5), (2, 6), (3, 7),
		]

		for a, b in edges:
			lines.addVertices(a, b)
			lines.closePrimitive()

		geom = Geom(vdata)
		geom.addPrimitive(lines)

		node = GeomNode('debug_wireframe')
		node.addGeom(geom)

		self._debug_node = self.node.attachNewNode(node)
		self._debug_node.setRenderModeThickness(2)
		self._debug_node.setLightOff()
		self._debug_node.setBin('fixed', 100)

	@property
	def position(self):
		return self._position

	@position.setter
	def position(self, value):
		self._position = list(value)
		if self.node:
			self.node.setPos(*self._position)
		self._update_shader_inputs()

	@property
	def size(self):
		return self._size

	@size.setter
	def size(self, value):
		self._size = list(value) if isinstance(value, (list, tuple)) else [value, value, value]
		self._rebuild()

	@property
	def color(self):
		return self._color

	@color.setter
	def color(self, value):
		self._color = list(value)
		self._update_shader_inputs()

	@property
	def density(self):
		return self._density

	@density.setter
	def density(self, value):
		self._density = value
		self._update_shader_inputs()

	@property
	def enabled(self):
		return self._enabled

	@enabled.setter
	def enabled(self, value):
		self._enabled = value
		if self._fog_node:
			if value:
				self._fog_node.show()
			else:
				self._fog_node.hide()

	def _rebuild(self):
		if self._fog_node:
			self._fog_node.removeNode()
		if self._debug_node:
			self._debug_node.removeNode()

		self._fog_node = self._create_box_geom()
		self._fog_node.reparentTo(self.node)

		self._fog_node.setShader(self._shader)
		self._fog_node.setTransparency(TransparencyAttrib.MAlpha)
		self._fog_node.setDepthWrite(False)
		self._fog_node.setDepthTest(False)
		self._fog_node.setAttrib(CullFaceAttrib.make(CullFaceAttrib.MCullClockwise))
		self._fog_node.setBin("transparent", 10)

		self._update_shader_inputs()

		if not self._enabled:
			self._fog_node.hide()

		if self.debug_mode:
			self._create_debug_wireframe()

	def update(self):
		if self._fog_node:
			cam_pos = base.camera.getPos(base.render)
			cam_fwd = base.camera.getQuat(base.render).getForward()
			self._fog_node.setShaderInput("camera_pos", cam_pos)
			self._fog_node.setShaderInput("camera_forward", cam_fwd)
			self._fog_node.setShaderInput("screen_size", Vec2(base.win.getXSize(), base.win.getYSize()))

		if self.debug_mode:
			if not self._debug_node:
				self._create_debug_wireframe()
			self._debug_node.show()
		else:
			if self._debug_node:
				self._debug_node.hide()

	def turn_on(self):
		self.enabled = True

	def turn_off(self):
		self.enabled = False

	def destroy(self):
		if self._debug_node:
			self._debug_node.removeNode()
			self._debug_node = None
		if self._fog_node:
			self._fog_node.removeNode()
			self._fog_node = None
		if self.node:
			self.node.removeNode()
			self.node = None