from direct.showbase.DirectObject import DirectObject
from direct.showbase.ShowBase import ShowBase
from panda3d.core import WindowProperties, KeyboardButton, MouseButton
import threading

# Global created by ShowBase
base: ShowBase

class InputHandler(DirectObject):
	"""Handles keyboard, mouse, and gamepad input using direct polling"""

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

		# Gamepad state
		self._gamepad_available = False
		self._gamepad_thread = None
		self._gamepad_running = False

		# Gamepad axes (normalized -1 to 1 for sticks, 0 to 1 for triggers)
		self.left_stick_x = 0.0
		self.left_stick_y = 0.0
		self.right_stick_x = 0.0
		self.right_stick_y = 0.0
		self.left_trigger = 0.0
		self.right_trigger = 0.0

		# Gamepad buttons (current and previous frame)
		self._gamepad_buttons = {}
		self._prev_gamepad_buttons = {}

		# Deadzone for sticks
		self.stick_deadzone = 0.15

		# Initialize gamepad
		self._init_gamepad()

	def _init_gamepad(self):
		"""Initialize gamepad support using inputs library"""
		try:
			import inputs
			if inputs.devices.gamepads:
				self._gamepad_available = True
				self._gamepad_running = True
				self._gamepad_thread = threading.Thread(target=self._gamepad_loop, daemon=True)
				self._gamepad_thread.start()
				print(f"Gamepad connected: {inputs.devices.gamepads[0]}")
			else:
				print("No gamepad detected")
		except ImportError:
			print("inputs library not installed. Run: pip install inputs")
		except Exception as e:
			print(f"Gamepad init error: {e}")

	def _gamepad_loop(self):
		"""Background thread to read gamepad events"""
		import inputs

		while self._gamepad_running:
			try:
				events = inputs.get_gamepad()
				for event in events:
					self._process_gamepad_event(event)
			except Exception as e:
				# Controller disconnected or error
				self._gamepad_available = False
				break

	def _process_gamepad_event(self, event):
		"""Process a single gamepad event"""
		code = event.code
		state = event.state

		# Left stick
		if code == 'ABS_X':
			self.left_stick_x = self._normalize_stick(state)
		elif code == 'ABS_Y':
			self.left_stick_y = self._normalize_stick(state)

		# Right stick
		elif code == 'ABS_RX':
			self.right_stick_x = self._normalize_stick(state)
		elif code == 'ABS_RY':
			self.right_stick_y = self._normalize_stick(state)

		# Triggers (0-255 range)
		elif code == 'ABS_Z':
			self.left_trigger = state / 255.0
		elif code == 'ABS_RZ':
			self.right_trigger = state / 255.0

		# D-pad
		elif code == 'ABS_HAT0X':
			self._gamepad_buttons['dpad_left'] = state == -1
			self._gamepad_buttons['dpad_right'] = state == 1
		elif code == 'ABS_HAT0Y':
			self._gamepad_buttons['dpad_up'] = state == -1
			self._gamepad_buttons['dpad_down'] = state == 1

		# Face buttons
		elif code == 'BTN_SOUTH':  # A
			self._gamepad_buttons['a'] = state == 1
		elif code == 'BTN_EAST':  # B
			self._gamepad_buttons['b'] = state == 1
		elif code == 'BTN_WEST':  # X
			self._gamepad_buttons['x'] = state == 1
		elif code == 'BTN_NORTH':  # Y
			self._gamepad_buttons['y'] = state == 1

		# Bumpers
		elif code == 'BTN_TL':  # Left bumper
			self._gamepad_buttons['lb'] = state == 1
		elif code == 'BTN_TR':  # Right bumper
			self._gamepad_buttons['rb'] = state == 1

		# Stick clicks
		elif code == 'BTN_THUMBL':
			self._gamepad_buttons['left_stick'] = state == 1
		elif code == 'BTN_THUMBR':
			self._gamepad_buttons['right_stick'] = state == 1

		# Start/Back
		elif code == 'BTN_START':
			self._gamepad_buttons['start'] = state == 1
		elif code == 'BTN_SELECT':
			self._gamepad_buttons['back'] = state == 1

		# Guide button (Xbox button)
		elif code == 'BTN_MODE':
			self._gamepad_buttons['guide'] = state == 1

	def _normalize_stick(self, value):
		"""Normalize stick value from -32768..32767 to -1..1 with deadzone"""
		normalized = value / 32768.0
		if abs(normalized) < self.stick_deadzone:
			return 0.0
		# Rescale to remove deadzone
		sign = 1 if normalized > 0 else -1
		return sign * (abs(normalized) - self.stick_deadzone) / (1.0 - self.stick_deadzone)

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

	# Gamepad methods
	def is_gamepad_available(self):
		"""Check if a gamepad is connected"""
		return self._gamepad_available

	def is_gamepad_button_pressed(self, button):
		"""Check if gamepad button is currently held down"""
		return self._gamepad_buttons.get(button, False)

	def is_gamepad_button_down(self, button):
		"""Check if gamepad button was just pressed this frame"""
		return self._gamepad_buttons.get(button, False) and not self._prev_gamepad_buttons.get(button, False)

	def is_gamepad_button_up(self, button):
		"""Check if gamepad button was just released this frame"""
		return not self._gamepad_buttons.get(button, False) and self._prev_gamepad_buttons.get(button, False)

	def get_left_stick(self):
		"""Get left stick as (x, y) tuple, normalized -1 to 1"""
		return (self.left_stick_x, self.left_stick_y)

	def get_right_stick(self):
		"""Get right stick as (x, y) tuple, normalized -1 to 1"""
		return (self.right_stick_x, self.right_stick_y)

	def get_triggers(self):
		"""Get triggers as (left, right) tuple, normalized 0 to 1"""
		return (self.left_trigger, self.right_trigger)

	def update(self):
		"""Update input state - call each frame"""
		# Store previous state
		self._prev_keys = self._curr_keys.copy()
		self._prev_mouse = self._curr_mouse.copy()
		self._prev_gamepad_buttons = self._gamepad_buttons.copy()

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

	def destroy(self):
		"""Clean up resources"""
		self._gamepad_running = False
		if self._gamepad_thread:
			self._gamepad_thread.join(timeout=0.5)

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