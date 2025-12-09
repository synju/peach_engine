from direct.showbase.DirectObject import DirectObject
from direct.showbase.ShowBase import ShowBase
from panda3d.core import WindowProperties, KeyboardButton, MouseButton

# Global created by ShowBase
base: ShowBase

class InputHandler(DirectObject):
	"""Handles keyboard and mouse input using direct polling"""

	def __init__(self):
		super().__init__()

		# Track key states
		self._prev_keys = {}
		self._curr_keys = {}

		# Define keys to track
		self._key_map = {
			'w': KeyboardButton.asciiKey('w'),
			'a': KeyboardButton.asciiKey('a'),
			's': KeyboardButton.asciiKey('s'),
			'd': KeyboardButton.asciiKey('d'),
			'q': KeyboardButton.asciiKey('q'),
			'e': KeyboardButton.asciiKey('e'),
			'r': KeyboardButton.asciiKey('r'),
			'f': KeyboardButton.asciiKey('f'),

			'f1': KeyboardButton.f1(),
			'f2': KeyboardButton.f2(),
			'f3': KeyboardButton.f3(),
			'f4': KeyboardButton.f4(),
			'f5': KeyboardButton.f5(),
			'f6': KeyboardButton.f6(),
			'f7': KeyboardButton.f7(),
			'f8': KeyboardButton.f8(),
			'f9': KeyboardButton.f9(),
			'f10': KeyboardButton.f10(),
			'f11': KeyboardButton.f11(),
			'f12': KeyboardButton.f12(),

			'space': KeyboardButton.space(),
			'lshift': KeyboardButton.lshift(),
			'rshift': KeyboardButton.rshift(),
			'lcontrol': KeyboardButton.lcontrol(),
			'rcontrol': KeyboardButton.rcontrol(),
			'escape': KeyboardButton.escape(),
			'enter': KeyboardButton.enter(),
			'tab': KeyboardButton.tab(),
			'backspace': KeyboardButton.backspace(),
			'up': KeyboardButton.up(),
			'down': KeyboardButton.down(),
			'left': KeyboardButton.left(),
			'right': KeyboardButton.right(),
		}

		# Add number keys
		for i in range(10):
			self._key_map[str(i)] = KeyboardButton.asciiKey(str(i))

		# Add letter keys
		for c in 'abcdefghijklmnopqrstuvwxyz':
			if c not in self._key_map:
				self._key_map[c] = KeyboardButton.asciiKey(c)

		# Track mouse
		self.mouse_locked = False
		self._mouse_pos = (0, 0)
		self.mouse_delta = (0, 0)
		self._last_mouse_pos = None
		self._skip_frames = 0

		# Mouse button states
		self._curr_mouse = {}
		self._prev_mouse = {}

	# Keyboard - matches CozyEngine naming
	def is_key_pressed(self, key):
		"""Check if key is currently held down"""
		if key == 'shift':
			return self._curr_keys.get('lshift', False) or self._curr_keys.get('rshift', False)
		if key == 'control':
			return self._curr_keys.get('lcontrol', False) or self._curr_keys.get('rcontrol', False)
		return self._curr_keys.get(key, False)

	def is_key_down(self, key):
		"""Check if key was just pressed this frame"""
		if key == 'shift':
			return (self._curr_keys.get('lshift', False) and not self._prev_keys.get('lshift', False)) or \
				(self._curr_keys.get('rshift', False) and not self._prev_keys.get('rshift', False))
		if key == 'control':
			return (self._curr_keys.get('lcontrol', False) and not self._prev_keys.get('lcontrol', False)) or \
				(self._curr_keys.get('rcontrol', False) and not self._prev_keys.get('rcontrol', False))
		return self._curr_keys.get(key, False) and not self._prev_keys.get(key, False)

	def is_key_up(self, key):
		"""Check if key was just released this frame"""
		if key == 'shift':
			return (not self._curr_keys.get('lshift', False) and self._prev_keys.get('lshift', False)) or \
				(not self._curr_keys.get('rshift', False) and self._prev_keys.get('rshift', False))
		if key == 'control':
			return (not self._curr_keys.get('lcontrol', False) and self._prev_keys.get('lcontrol', False)) or \
				(not self._curr_keys.get('rcontrol', False) and self._prev_keys.get('rcontrol', False))
		return not self._curr_keys.get(key, False) and self._prev_keys.get(key, False)

	# Mouse buttons - matches CozyEngine naming
	def is_mouse_pressed(self, button=1):
		"""Check if mouse button is currently held down (1=left, 2=middle, 3=right)"""
		return self._curr_mouse.get(button, False)

	def is_mouse_down(self, button=1):
		"""Check if mouse button was just pressed this frame"""
		return self._curr_mouse.get(button, False) and not self._prev_mouse.get(button, False)

	def is_mouse_up(self, button=1):
		"""Check if mouse button was just released this frame"""
		return not self._curr_mouse.get(button, False) and self._prev_mouse.get(button, False)

	def get_mouse_pos(self):
		"""Get current mouse position in pixels"""
		return self._mouse_pos

	def set_mouse_locked(self, locked):
		"""Lock/unlock mouse to window center"""
		self.mouse_locked = locked
		props = WindowProperties()
		props.setCursorHidden(locked)
		props.setMouseMode(WindowProperties.M_confined if locked else WindowProperties.M_absolute)
		base.win.requestProperties(props)

		if locked:
			self._skip_frames = 2
			self.mouse_delta = (0, 0)
			self._last_mouse_pos = None

	def update(self):
		"""Update input state - call each frame"""
		# Store previous state
		self._prev_keys = self._curr_keys.copy()
		self._prev_mouse = self._curr_mouse.copy()

		# Poll keyboard state
		if base.mouseWatcherNode.hasMouse():
			for key_name, key_button in self._key_map.items():
				self._curr_keys[key_name] = base.mouseWatcherNode.isButtonDown(key_button)

			# Poll mouse buttons
			self._curr_mouse[1] = base.mouseWatcherNode.isButtonDown(MouseButton.one())
			self._curr_mouse[2] = base.mouseWatcherNode.isButtonDown(MouseButton.two())
			self._curr_mouse[3] = base.mouseWatcherNode.isButtonDown(MouseButton.three())

			# Get mouse position in pixels
			mx = base.mouseWatcherNode.getMouseX()
			my = base.mouseWatcherNode.getMouseY()
			w = base.win.getXSize()
			h = base.win.getYSize()
			# Convert from -1..1 to pixels
			self._mouse_pos = (int((mx + 1) * w / 2), int((1 - my) * h / 2))

		# Mouse delta handling for locked mouse
		if not self.mouse_locked:
			self.mouse_delta = (0, 0)
			self._last_mouse_pos = None
			return

		if not base.mouseWatcherNode.hasMouse():
			self.mouse_delta = (0, 0)
			return

		mx = base.mouseWatcherNode.getMouseX()
		my = base.mouseWatcherNode.getMouseY()

		# Skip frames after locking
		if self._skip_frames > 0:
			self._skip_frames -= 1
			self.mouse_delta = (0, 0)
			self._last_mouse_pos = (mx, my)
			return

		# Calculate delta from last position
		if self._last_mouse_pos is not None:
			dx = mx - self._last_mouse_pos[0]
			dy = my - self._last_mouse_pos[1]
			self.mouse_delta = (dx, dy)
		else:
			self.mouse_delta = (0, 0)

		self._last_mouse_pos = (mx, my)

		# Recenter if near edge
		if abs(mx) > 0.8 or abs(my) > 0.8:
			w = base.win.getXSize()
			h = base.win.getYSize()
			base.win.movePointer(0, w // 2, h // 2)
			self._last_mouse_pos = None
			self._skip_frames = 1

# Backwards compatibility aliases
InputHandler.is_key_held = InputHandler.is_key_pressed
InputHandler.is_key_just_pressed = InputHandler.is_key_down
InputHandler.is_key_released = InputHandler.is_key_up
InputHandler.is_mouse_held = InputHandler.is_mouse_pressed
InputHandler.is_mouse_just_pressed = InputHandler.is_mouse_down

# Global instance
input_handler = None

def get_input():
	"""Get the global input handler"""
	global input_handler
	if input_handler is None:
		input_handler = InputHandler()
	return input_handler