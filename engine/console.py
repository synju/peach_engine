from direct.showbase.ShowBase import ShowBase
from direct.gui.DirectGui import DirectFrame, DirectEntry, DirectLabel
from direct.gui.OnscreenText import OnscreenText
from panda3d.core import (
	TextNode, CardMaker, TransparencyAttrib,
	WindowProperties, NodePath, TextureStage,
	Texture, PNMImage
)

from engine.console_bg import ConsoleBackground

base: ShowBase


class Console:
	"""Quake 3 style drop-down console"""

	def __init__(self, engine, toggle_key='`', history_size=100):
		self.engine = engine
		self.toggle_key = toggle_key
		self.history_size = history_size

		self._is_open = False
		self._command_history = []
		self._history_index = -1
		self._output_lines = []
		self._max_output_lines = 34

		# Console dimensions (covers top half of screen)
		self._height = 0.5  # Half screen height in aspect2d coords

		# GUI elements
		self._background = None
		self._red_line = None
		self._input_field = None
		self._output_text = None
		self._scroll_task = None

		# Command handlers
		self._commands = {}

		# Register built-in commands
		self._register_builtin_commands()

		# Create console GUI
		self._create_console()

		# Hide initially
		self._console_root.hide()

		# Register toggle key
		base.accept(self.toggle_key, self.toggle)

	def _create_console(self):
		"""Create the console GUI elements"""
		# Root node for entire console
		self._console_root = base.aspect2d.attachNewNode("console_root")
		self._console_root.setPos(0, 0, 1 - self._height)

		# Background
		self._background = ConsoleBackground(self._console_root, self._height)

		# Start update task
		self._scroll_task = base.taskMgr.add(self._update_background, "console_update")

		# Red line at bottom
		self._create_red_line()

		# Output text area
		self._create_output_area()

		# Input field
		self._create_input_field()

	def _update_background(self, task):
		"""Update background animation"""
		if not self._is_open:
			return task.cont

		dt = globalClock.getDt()
		self._background.update(dt)
		return task.cont

	def _create_red_line(self):
		"""Create red separator line at bottom of console"""
		cm = CardMaker('red_line')
		aspect = base.getAspectRatio()
		cm.setFrame(-aspect, aspect, -0.005, 0.005)

		self._red_line = self._console_root.attachNewNode(cm.generate())
		self._red_line.setPos(0, 0, -self._height * 2)
		self._red_line.setColor(1, 0, 0, 1)

	def _create_output_area(self):
		"""Create scrollable output text area"""
		self._output_nodes = []
		line_height = 0.028
		start_y = -0.03

		for i in range(self._max_output_lines):
			text = OnscreenText(
				text="",
				pos=(-base.getAspectRatio() + 0.03, start_y - (i * line_height)),
				scale=0.025,
				fg=(0.8, 0.8, 0.8, 1),
				align=TextNode.ALeft,
				parent=self._console_root,
				mayChange=True
			)
			self._output_nodes.append(text)

	def _create_input_field(self):
		"""Create command input field"""
		aspect = base.getAspectRatio()

		# Input prompt
		self._prompt = OnscreenText(
			text="]",
			pos=(-aspect + 0.02, -self._height * 2 + 0.02),
			scale=0.025,
			fg=(1, 1, 1, 1),
			align=TextNode.ALeft,
			parent=self._console_root
		)

		# Input field
		self._input_field = DirectEntry(
			parent=self._console_root,
			scale=0.025,
			pos=(-aspect + 0.05, 0, -self._height * 2 + 0.018),
			width=60,
			numLines=1,
			focus=0,
			frameColor=(0, 0, 0, 0),
			text_fg=(1, 1, 1, 1),
			cursorKeys=True,
			command=self._on_command_entered,
			focusInCommand=self._on_focus_in,
			focusOutCommand=self._on_focus_out
		)

		# Key bindings for input
		self._input_field.bind('press-arrow_up-', self._history_up)
		self._input_field.bind('press-arrow_down-', self._history_down)

	def _on_focus_in(self):
		"""Called when input field gains focus"""
		pass

	def _on_focus_out(self):
		"""Called when input field loses focus"""
		pass

	def _history_up(self, event):
		"""Navigate command history up"""
		if not self._command_history:
			return

		if self._history_index < len(self._command_history) - 1:
			self._history_index += 1
			cmd = self._command_history[-(self._history_index + 1)]
			self._input_field.enterText(cmd)

	def _history_down(self, event):
		"""Navigate command history down"""
		if self._history_index > 0:
			self._history_index -= 1
			cmd = self._command_history[-(self._history_index + 1)]
			self._input_field.enterText(cmd)
		elif self._history_index == 0:
			self._history_index = -1
			self._input_field.enterText("")

	def _on_command_entered(self, text):
		"""Handle command submission"""
		text = text.strip()
		if not text:
			return

		# Add to history
		self._command_history.append(text)
		if len(self._command_history) > self.history_size:
			self._command_history.pop(0)
		self._history_index = -1

		# Echo command
		self.print(f"] {text}")

		# Parse and execute
		parts = text.split(None, 1)
		cmd = parts[0].lower()
		args = parts[1] if len(parts) > 1 else ""

		if cmd in self._commands:
			try:
				result = self._commands[cmd](args)
				if result:
					self.print(result)
			except Exception as e:
				self.print(f"^1Error: {e}")
		else:
			self.print(f"Unknown command: {cmd}")

		# Clear input and re-focus
		self._input_field.enterText("")
		self._input_field['focus'] = 1

	def _update_output_display(self):
		"""Update the visible output lines"""
		visible_lines = self._output_lines[-self._max_output_lines:]

		for i, node in enumerate(self._output_nodes):
			if i < len(visible_lines):
				node.setText(visible_lines[i])
			else:
				node.setText("")

	def print(self, text):
		"""Print text to console output"""
		lines = text.split('\n')
		for line in lines:
			self._output_lines.append(line)

		# Trim if too many
		if len(self._output_lines) > 500:
			self._output_lines = self._output_lines[-500:]

		self._update_output_display()

	def toggle(self):
		"""Toggle console visibility"""
		if self._is_open:
			self.close()
		else:
			self.open()

	def open(self):
		"""Open the console"""
		if self._is_open:
			return

		self._is_open = True
		self._console_root.show()

		# Release mouse
		props = WindowProperties()
		props.setCursorHidden(False)
		props.setMouseMode(WindowProperties.MAbsolute)
		base.win.requestProperties(props)

		# Tell input handler mouse is unlocked
		if hasattr(self.engine, 'input_handler'):
			self.engine.input_handler.mouse_locked = False

		# Focus input field
		self._input_field['focus'] = 1

	def close(self):
		"""Close the console"""
		if not self._is_open:
			return

		self._is_open = False
		self._console_root.hide()

		# Clear input field
		self._input_field.enterText("")

		# Capture mouse
		props = WindowProperties()
		props.setCursorHidden(True)
		props.setMouseMode(WindowProperties.MRelative)
		base.win.requestProperties(props)

		# Tell input handler mouse is locked
		if hasattr(self.engine, 'input_handler'):
			self.engine.input_handler.mouse_locked = True

		# Unfocus input
		self._input_field['focus'] = 0

	@property
	def is_open(self):
		return self._is_open

	def register_command(self, name, callback, help_text=""):
		"""Register a console command"""
		name = name.lower()
		self._commands[name] = callback
		if help_text:
			# Store help text separately instead of on the callback
			if not hasattr(self, '_command_help'):
				self._command_help = {}
			self._command_help[name] = help_text

	def _register_builtin_commands(self):
		"""Register built-in commands"""
		self._command_help = {}

		def cmd_help(args):
			lines = ["Available commands:"]
			for name in sorted(self._commands.keys()):
				help_text = self._command_help.get(name, '')
				if help_text:
					lines.append(f"  {name} - {help_text}")
				else:
					lines.append(f"  {name}")
			return '\n'.join(lines)

		def cmd_clear(args):
			self._output_lines.clear()
			self._update_output_display()
			return None

		def cmd_quit(args):
			base.userExit()
			return None

		def cmd_echo(args):
			return args

		self._commands['help'] = cmd_help
		self._commands['clear'] = cmd_clear
		self._commands['quit'] = cmd_quit
		self._commands['exit'] = cmd_quit
		self._commands['echo'] = cmd_echo

		self._command_help['help'] = "Show available commands"
		self._command_help['clear'] = "Clear console output"
		self._command_help['quit'] = "Exit the game"
		self._command_help['echo'] = "Print text to console"

	def destroy(self):
		"""Clean up console"""
		if self._scroll_task:
			base.taskMgr.remove(self._scroll_task)

		base.ignore(self.toggle_key)

		if self._background:
			self._background.destroy()

		if self._console_root:
			self._console_root.removeNode()