from direct.showbase.ShowBase import ShowBase
from panda3d.core import (
	CardMaker, TransparencyAttrib, Texture, TextureStage, Shader, Vec2
)
import math

base: ShowBase


BLUR_SHADER_VERT = """
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

BLUR_SHADER_FRAG = """
#version 330
uniform sampler2D p3d_Texture0;
uniform float blur_amount;
uniform float opacity;
uniform vec2 tex_offset;
uniform vec2 tex_scale;
in vec2 texcoord;
out vec4 fragColor;

void main() {
	vec2 uv = texcoord * tex_scale + tex_offset;
	float b = blur_amount * 0.001;

	vec4 color = vec4(0.0);

	// 9-sample box blur
	color += texture(p3d_Texture0, uv + vec2(-b, -b));
	color += texture(p3d_Texture0, uv + vec2(0, -b));
	color += texture(p3d_Texture0, uv + vec2(b, -b));
	color += texture(p3d_Texture0, uv + vec2(-b, 0));
	color += texture(p3d_Texture0, uv);
	color += texture(p3d_Texture0, uv + vec2(b, 0));
	color += texture(p3d_Texture0, uv + vec2(-b, b));
	color += texture(p3d_Texture0, uv + vec2(0, b));
	color += texture(p3d_Texture0, uv + vec2(b, b));

	color = color / 9.0;
	color.a *= opacity;
	fragColor = color;
}
"""


class ConsoleBackground:
	"""Console background layers"""

	def __init__(self, parent, height):
		self._parent = parent
		self._height = height

		# Layer references
		self._bg_color = None
		self._mini_circuit = None
		self._big_circuit = None
		self._text_layer = None
		self._vignette = None

		# Animation state
		self._time = 0
		self._mini_scroll_x = 0
		self._mini_scroll_y = 0
		self._big_scroll_x = 0
		self._big_scroll_y = 0
		self._text_scroll_x = 0
		self._text_scroll_y = 0

		# Layer 2 settings (mini circuitry)
		self._mini_circuit_settings = {
			'scroll_speed': 0.015,
			'breath_speed': 0.4,
			'breath_amount': 0.6,
			'blur': 0.5,
			'opacity': 0.2,
			'max_speed': 0.04,
			'scale_x': 8.0,
			'scale_y': 5.5,
		}

		# Layer 3 settings (big circuitry)
		self._big_circuit_settings = {
			'scroll_speed': 0.02,
			'breath_speed': 0.3,
			'breath_amount': 0.8,
			'blur': 1.0,
			'opacity': 0.3,
			'max_speed': 0.05,
			'scale_x': 2.0,
			'scale_y': 1.5
		}

		# Layer 4 settings (text)
		self._text_layer_settings = {
			'scroll_speed': 0.01,
			'breath_speed': 0.25,
			'breath_amount': 0.5,
			'blur': 0.0,
			'opacity': 0.3,
			'max_speed': 0.03,
			'scale_x': 0.5,
			'scale_y': 0.2
		}

		# Shared shader
		self._blur_shader = Shader.make(Shader.SL_GLSL, BLUR_SHADER_VERT, BLUR_SHADER_FRAG)

		self._create_layers()

	def _create_layers(self):
		"""Create background layers"""
		aspect = base.getAspectRatio()

		# Layer 1: Background color (static)
		cm = CardMaker('bg_color')
		cm.setFrame(-aspect, aspect, -self._height * 2, 0)

		self._bg_color = self._parent.attachNewNode(cm.generate())
		self._bg_color.setPos(0, 0, 0)

		tex = loader.loadTexture("assets/console/bg-color.png")
		self._bg_color.setTexture(tex)
		self._bg_color.setTransparency(TransparencyAttrib.MAlpha)

		# Layer 2: Mini circuitry
		cm = CardMaker('mini_circuit')
		cm.setFrame(-aspect, aspect, -self._height * 2, 0)

		self._mini_circuit = self._parent.attachNewNode(cm.generate())
		self._mini_circuit.setPos(0, 0, 0)

		tex = loader.loadTexture("assets/console/mini-circuitry.png")
		tex.setWrapU(Texture.WMRepeat)
		tex.setWrapV(Texture.WMRepeat)
		self._mini_circuit.setTexture(tex)
		self._mini_circuit.setTransparency(TransparencyAttrib.MAlpha)

		self._mini_circuit.setShader(self._blur_shader)
		self._mini_circuit.setShaderInput("blur_amount", self._mini_circuit_settings['blur'])
		self._mini_circuit.setShaderInput("opacity", self._mini_circuit_settings['opacity'])
		self._mini_circuit.setShaderInput("tex_offset", Vec2(0.0, 0.0))
		self._mini_circuit.setShaderInput("tex_scale", Vec2(
			self._mini_circuit_settings['scale_x'],
			self._mini_circuit_settings['scale_y']))

		# Layer 3: Big circuitry
		cm = CardMaker('big_circuit')
		cm.setFrame(-aspect, aspect, -self._height * 2, 0)

		self._big_circuit = self._parent.attachNewNode(cm.generate())
		self._big_circuit.setPos(0, 0, 0)

		tex = loader.loadTexture("assets/console/big-circuitry.png")
		tex.setWrapU(Texture.WMRepeat)
		tex.setWrapV(Texture.WMRepeat)
		self._big_circuit.setTexture(tex)
		self._big_circuit.setTransparency(TransparencyAttrib.MAlpha)

		self._big_circuit.setShader(self._blur_shader)
		self._big_circuit.setShaderInput("blur_amount", self._big_circuit_settings['blur'])
		self._big_circuit.setShaderInput("opacity", self._big_circuit_settings['opacity'])
		self._big_circuit.setShaderInput("tex_offset", Vec2(0.0, 0.0))
		self._big_circuit.setShaderInput("tex_scale", Vec2(
			self._big_circuit_settings['scale_x'],
			self._big_circuit_settings['scale_y']))

		# Layer 4: Text
		cm = CardMaker('text_layer')
		cm.setFrame(-aspect, aspect, -self._height * 2, 0)

		self._text_layer = self._parent.attachNewNode(cm.generate())
		self._text_layer.setPos(0, 0, 0)

		tex = loader.loadTexture("assets/console/c1.png")
		tex.setWrapU(Texture.WMRepeat)
		tex.setWrapV(Texture.WMRepeat)
		self._text_layer.setTexture(tex)
		self._text_layer.setTransparency(TransparencyAttrib.MAlpha)

		self._text_layer.setShader(self._blur_shader)
		self._text_layer.setShaderInput("blur_amount", self._text_layer_settings['blur'])
		self._text_layer.setShaderInput("opacity", self._text_layer_settings['opacity'])
		self._text_layer.setShaderInput("tex_offset", Vec2(0.0, 0.0))
		self._text_layer.setShaderInput("tex_scale", Vec2(
			self._text_layer_settings['scale_x'],
			self._text_layer_settings['scale_y']))

		# Layer 5: Vignette (static)
		cm = CardMaker('vignette')
		cm.setFrame(-aspect, aspect, -self._height * 2, 0)

		self._vignette = self._parent.attachNewNode(cm.generate())
		self._vignette.setPos(0, 0, 0)

		tex = loader.loadTexture("assets/console/vignette-effect.png")
		self._vignette.setTexture(tex)
		self._vignette.setTransparency(TransparencyAttrib.MAlpha)

	def update(self, dt):
		"""Update animations"""
		self._time += dt

		# Layer 2: Mini circuitry
		s = self._mini_circuit_settings

		breath = math.sin(self._time * s['breath_speed'])
		breath2 = math.sin(self._time * s['breath_speed'] * 0.7 + 1.5)

		speed_x = s['scroll_speed'] * (1.0 + breath * s['breath_amount'])
		speed_y = s['scroll_speed'] * 0.7 * (1.0 + breath2 * s['breath_amount'])

		speed_x = max(-s['max_speed'], min(s['max_speed'], speed_x))
		speed_y = max(-s['max_speed'], min(s['max_speed'], speed_y))

		self._mini_scroll_x += speed_x * dt
		self._mini_scroll_y += speed_y * dt

		self._mini_circuit.setShaderInput("tex_offset", Vec2(self._mini_scroll_x, self._mini_scroll_y))
		self._mini_circuit.setShaderInput("blur_amount", s['blur'])
		self._mini_circuit.setShaderInput("opacity", s['opacity'])

		# Layer 3: Big circuitry
		s = self._big_circuit_settings

		breath = math.sin(self._time * s['breath_speed'] + 0.5)
		breath2 = math.sin(self._time * s['breath_speed'] * 0.7 + 2.0)

		speed_x = s['scroll_speed'] * (1.0 + breath * s['breath_amount'])
		speed_y = s['scroll_speed'] * 0.7 * (1.0 + breath2 * s['breath_amount'])

		speed_x = max(-s['max_speed'], min(s['max_speed'], speed_x))
		speed_y = max(-s['max_speed'], min(s['max_speed'], speed_y))

		self._big_scroll_x += speed_x * dt
		self._big_scroll_y += speed_y * dt

		self._big_circuit.setShaderInput("tex_offset", Vec2(self._big_scroll_x, self._big_scroll_y))
		self._big_circuit.setShaderInput("blur_amount", s['blur'])
		self._big_circuit.setShaderInput("opacity", s['opacity'])

		# Layer 4: Text
		s = self._text_layer_settings

		breath = math.sin(self._time * s['breath_speed'] + 1.0)
		breath2 = math.sin(self._time * s['breath_speed'] * 0.6 + 2.5)

		speed_x = s['scroll_speed'] * (1.0 + breath * s['breath_amount'])
		speed_y = s['scroll_speed'] * 0.7 * (1.0 + breath2 * s['breath_amount'])

		speed_x = max(-s['max_speed'], min(s['max_speed'], speed_x))
		speed_y = max(-s['max_speed'], min(s['max_speed'], speed_y))

		self._text_scroll_x += speed_x * dt
		self._text_scroll_y += speed_y * dt

		self._text_layer.setShaderInput("tex_offset", Vec2(self._text_scroll_x, self._text_scroll_y))
		self._text_layer.setShaderInput("blur_amount", s['blur'])
		self._text_layer.setShaderInput("opacity", s['opacity'])

	def set_mini_circuit(self, scroll_speed=None, breath_speed=None, breath_amount=None, blur=None, opacity=None, max_speed=None, scale_x=None, scale_y=None):
		"""Configure mini circuitry layer"""
		if scroll_speed is not None:
			self._mini_circuit_settings['scroll_speed'] = scroll_speed
		if breath_speed is not None:
			self._mini_circuit_settings['breath_speed'] = breath_speed
		if breath_amount is not None:
			self._mini_circuit_settings['breath_amount'] = breath_amount
		if blur is not None:
			self._mini_circuit_settings['blur'] = blur
		if opacity is not None:
			self._mini_circuit_settings['opacity'] = opacity
		if max_speed is not None:
			self._mini_circuit_settings['max_speed'] = max_speed
		if scale_x is not None:
			self._mini_circuit_settings['scale_x'] = scale_x
		if scale_y is not None:
			self._mini_circuit_settings['scale_y'] = scale_y
		if scale_x is not None or scale_y is not None:
			self._mini_circuit.setShaderInput("tex_scale", Vec2(
				self._mini_circuit_settings['scale_x'],
				self._mini_circuit_settings['scale_y']))

	def set_big_circuit(self, scroll_speed=None, breath_speed=None, breath_amount=None, blur=None, opacity=None, max_speed=None, scale_x=None, scale_y=None):
		"""Configure big circuitry layer"""
		if scroll_speed is not None:
			self._big_circuit_settings['scroll_speed'] = scroll_speed
		if breath_speed is not None:
			self._big_circuit_settings['breath_speed'] = breath_speed
		if breath_amount is not None:
			self._big_circuit_settings['breath_amount'] = breath_amount
		if blur is not None:
			self._big_circuit_settings['blur'] = blur
		if opacity is not None:
			self._big_circuit_settings['opacity'] = opacity
		if max_speed is not None:
			self._big_circuit_settings['max_speed'] = max_speed
		if scale_x is not None:
			self._big_circuit_settings['scale_x'] = scale_x
		if scale_y is not None:
			self._big_circuit_settings['scale_y'] = scale_y
		if scale_x is not None or scale_y is not None:
			self._big_circuit.setShaderInput("tex_scale", Vec2(
				self._big_circuit_settings['scale_x'],
				self._big_circuit_settings['scale_y']))

	def set_text_layer(self, scroll_speed=None, breath_speed=None, breath_amount=None, blur=None, opacity=None, max_speed=None, scale_x=None, scale_y=None):
		"""Configure text layer"""
		if scroll_speed is not None:
			self._text_layer_settings['scroll_speed'] = scroll_speed
		if breath_speed is not None:
			self._text_layer_settings['breath_speed'] = breath_speed
		if breath_amount is not None:
			self._text_layer_settings['breath_amount'] = breath_amount
		if blur is not None:
			self._text_layer_settings['blur'] = blur
		if opacity is not None:
			self._text_layer_settings['opacity'] = opacity
		if max_speed is not None:
			self._text_layer_settings['max_speed'] = max_speed
		if scale_x is not None:
			self._text_layer_settings['scale_x'] = scale_x
		if scale_y is not None:
			self._text_layer_settings['scale_y'] = scale_y
		if scale_x is not None or scale_y is not None:
			self._text_layer.setShaderInput("tex_scale", Vec2(
				self._text_layer_settings['scale_x'],
				self._text_layer_settings['scale_y']))

	def destroy(self):
		"""Clean up"""
		if self._bg_color:
			self._bg_color.removeNode()
		if self._mini_circuit:
			self._mini_circuit.removeNode()
		if self._big_circuit:
			self._big_circuit.removeNode()
		if self._text_layer:
			self._text_layer.removeNode()
		if self._vignette:
			self._vignette.removeNode()