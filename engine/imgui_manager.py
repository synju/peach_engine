"""
ImGui integration for Panda3D using pyimgui

Install: pip install imgui[full]
"""
from direct.showbase.ShowBase import ShowBase
from direct.task import Task

import imgui
from imgui.integrations.opengl import ProgrammablePipelineRenderer

base: ShowBase

class ImGuiManager:
	"""Manages ImGui rendering within Panda3D"""

	def __init__(self, engine):
		self.engine = engine

		# Initialize ImGui
		imgui.create_context()

		io = imgui.get_io()
		io.display_size = (base.win.getXSize(), base.win.getYSize())
		io.fonts.get_tex_data_as_rgba32()

		# Create renderer
		self._renderer = ProgrammablePipelineRenderer()

		# Mouse state
		self._mouse_down = [False, False, False]

		# Keyboard state
		self._keys_down = {}

		# Setup mouse input
		base.accept("mouse1", self._on_mouse_down, [0])
		base.accept("mouse1-up", self._on_mouse_up, [0])
		base.accept("mouse2", self._on_mouse_down, [2])  # Middle
		base.accept("mouse2-up", self._on_mouse_up, [2])
		base.accept("mouse3", self._on_mouse_down, [1])  # Right
		base.accept("mouse3-up", self._on_mouse_up, [1])

		# Scroll wheel
		base.accept("wheel_up", self._on_scroll, [0, 1])
		base.accept("wheel_down", self._on_scroll, [0, -1])

		# Setup keyboard input
		self._setup_keyboard()

		# Track window size
		self._last_width = base.win.getXSize()
		self._last_height = base.win.getYSize()

	def _setup_keyboard(self):
		"""Setup keyboard input handling"""
		# Map Panda3D keys to ImGui keys
		self._key_map = {
			'arrow_up': imgui.KEY_UP_ARROW,
			'arrow_down': imgui.KEY_DOWN_ARROW,
			'arrow_left': imgui.KEY_LEFT_ARROW,
			'arrow_right': imgui.KEY_RIGHT_ARROW,
			'enter': imgui.KEY_ENTER,
			'backspace': imgui.KEY_BACKSPACE,
			'escape': imgui.KEY_ESCAPE,
			'tab': imgui.KEY_TAB,
			'space': imgui.KEY_SPACE,
			'delete': imgui.KEY_DELETE,
			'home': imgui.KEY_HOME,
			'end': imgui.KEY_END,
			'page_up': imgui.KEY_PAGE_UP,
			'page_down': imgui.KEY_PAGE_DOWN,
		}

		# Register key handlers
		for panda_key, imgui_key in self._key_map.items():
			base.accept(panda_key, self._on_key_down, [imgui_key])
			base.accept(f"{panda_key}-up", self._on_key_up, [imgui_key])

	def _on_key_down(self, key):
		self._keys_down[key] = True

	def _on_key_up(self, key):
		self._keys_down[key] = False

	def _on_mouse_down(self, button):
		self._mouse_down[button] = True

	def _on_mouse_up(self, button):
		self._mouse_down[button] = False

	def _on_scroll(self, x, y):
		io = imgui.get_io()
		io.mouse_wheel = y

	def begin_frame(self):
		"""Call at the start of each frame before drawing UI"""
		io = imgui.get_io()

		# Update display size if window resized
		width = base.win.getXSize()
		height = base.win.getYSize()
		if width != self._last_width or height != self._last_height:
			io.display_size = (width, height)
			self._last_width = width
			self._last_height = height

		# Update mouse position
		if base.mouseWatcherNode.hasMouse():
			mx = base.mouseWatcherNode.getMouseX()
			my = base.mouseWatcherNode.getMouseY()
			# Convert from -1,1 to pixel coords
			x = int((mx + 1) / 2 * width)
			y = int((1 - my) / 2 * height)
			io.mouse_pos = (x, y)

		# Update mouse buttons
		io.mouse_down[0] = self._mouse_down[0]
		io.mouse_down[1] = self._mouse_down[1]
		io.mouse_down[2] = self._mouse_down[2]

		# Update keyboard state
		for key, is_down in self._keys_down.items():
			io.keys_down[key] = is_down

		imgui.new_frame()

	def end_frame(self):
		"""Call at the end of each frame to render UI"""
		imgui.render()
		imgui.end_frame()
		self._renderer.render(imgui.get_draw_data())

		# Reset scroll
		imgui.get_io().mouse_wheel = 0

	def want_capture_mouse(self):
		"""Returns True if ImGui wants mouse input (hovering over UI)"""
		return imgui.get_io().want_capture_mouse

	def want_capture_keyboard(self):
		"""Returns True if ImGui wants keyboard input"""
		return imgui.get_io().want_capture_keyboard

	def destroy(self):
		"""Cleanup"""
		self._renderer.shutdown()

# Convenience functions for common UI patterns
def begin_main_menu_bar():
	return imgui.begin_main_menu_bar()

def end_main_menu_bar():
	imgui.end_main_menu_bar()

def begin_menu(label, enabled=True):
	return imgui.begin_menu(label, enabled)

def end_menu():
	imgui.end_menu()

def menu_item(label, shortcut="", selected=False, enabled=True):
	return imgui.menu_item(label, shortcut, selected, enabled)

def separator():
	imgui.separator()