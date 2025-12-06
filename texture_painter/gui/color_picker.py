"""
Custom HSV Color Picker Widget for ImGui
Hue wheel + Saturation/Value square
"""
import imgui
import math
import colorsys

class ColorPicker:
	def __init__(self, size=200):
		self.size = size
		self.wheel_thickness = 20
		self.h = 0.0  # 0-1
		self.s = 1.0  # 0-1
		self.v = 1.0  # 0-1
		self.dragging_wheel = False
		self.dragging_sv = False

	def set_rgb(self, r, g, b):
		"""Set color from RGB values (0-1 range)"""
		self.h, self.s, self.v = colorsys.rgb_to_hsv(r, g, b)

	def get_rgb(self):
		"""Get RGB values (0-1 range)"""
		return colorsys.hsv_to_rgb(self.h, self.s, self.v)

	def draw(self, label="##colorpicker"):
		"""Draw the color picker. Returns (changed, r, g, b)"""
		changed = False
		draw_list = imgui.get_window_draw_list()
		pos = imgui.get_cursor_screen_pos()

		center_x = pos[0] + self.size / 2
		center_y = pos[1] + self.size / 2

		outer_radius = self.size / 2
		inner_radius = outer_radius - self.wheel_thickness

		# Draw hue wheel
		segments = 64
		for i in range(segments):
			a1 = (i / segments) * 2 * math.pi
			a2 = ((i + 1) / segments) * 2 * math.pi

			hue = i / segments
			r, g, b = colorsys.hsv_to_rgb(hue, 1.0, 1.0)
			col = imgui.get_color_u32_rgba(r, g, b, 1.0)

			# Outer point 1
			ox1 = center_x + math.cos(a1) * outer_radius
			oy1 = center_y + math.sin(a1) * outer_radius
			# Inner point 1
			ix1 = center_x + math.cos(a1) * inner_radius
			iy1 = center_y + math.sin(a1) * inner_radius
			# Outer point 2
			ox2 = center_x + math.cos(a2) * outer_radius
			oy2 = center_y + math.sin(a2) * outer_radius
			# Inner point 2
			ix2 = center_x + math.cos(a2) * inner_radius
			iy2 = center_y + math.sin(a2) * inner_radius

			draw_list.add_quad_filled(ox1, oy1, ox2, oy2, ix2, iy2, ix1, iy1, col)

		# Draw SV square inside the wheel
		sv_size = inner_radius * 1.3  # Fit square inside circle
		sv_half = sv_size / 2
		sv_x = center_x - sv_half
		sv_y = center_y - sv_half

		# Get the hue color for the SV square
		hr, hg, hb = colorsys.hsv_to_rgb(self.h, 1.0, 1.0)
		hue_col = imgui.get_color_u32_rgba(hr, hg, hb, 1.0)
		white = imgui.get_color_u32_rgba(1, 1, 1, 1)
		black = imgui.get_color_u32_rgba(0, 0, 0, 1)
		transparent = imgui.get_color_u32_rgba(0, 0, 0, 0)

		# Base: white to hue (horizontal gradient)
		draw_list.add_rect_filled_multicolor(
			sv_x, sv_y,
			sv_x + sv_size, sv_y + sv_size,
			white, hue_col, hue_col, white
		)

		# Overlay: transparent to black (vertical gradient)
		draw_list.add_rect_filled_multicolor(
			sv_x, sv_y,
			sv_x + sv_size, sv_y + sv_size,
			transparent, transparent, black, black
		)

		# Draw SV cursor
		sv_cursor_x = sv_x + self.s * sv_size
		sv_cursor_y = sv_y + (1 - self.v) * sv_size
		draw_list.add_circle(sv_cursor_x, sv_cursor_y, 6, imgui.get_color_u32_rgba(1, 1, 1, 1), 12, 2)
		draw_list.add_circle(sv_cursor_x, sv_cursor_y, 5, imgui.get_color_u32_rgba(0, 0, 0, 1), 12, 1)

		# Draw hue cursor on wheel
		hue_angle = self.h * 2 * math.pi
		hue_radius = (outer_radius + inner_radius) / 2
		hue_cursor_x = center_x + math.cos(hue_angle) * hue_radius
		hue_cursor_y = center_y + math.sin(hue_angle) * hue_radius
		draw_list.add_circle(hue_cursor_x, hue_cursor_y, 6, imgui.get_color_u32_rgba(1, 1, 1, 1), 12, 2)
		draw_list.add_circle(hue_cursor_x, hue_cursor_y, 5, imgui.get_color_u32_rgba(0, 0, 0, 1), 12, 1)

		# Invisible button for interaction
		imgui.invisible_button(label, self.size, self.size)

		# Handle input
		io = imgui.get_io()
		mouse_x, mouse_y = io.mouse_pos

		if imgui.is_item_active():
			dx = mouse_x - center_x
			dy = mouse_y - center_y
			dist = math.sqrt(dx * dx + dy * dy)

			# Check if clicking on wheel
			if not self.dragging_sv and (dist >= inner_radius - 5 or self.dragging_wheel):
				self.dragging_wheel = True
				self.dragging_sv = False
				angle = math.atan2(dy, dx)
				if angle < 0:
					angle += 2 * math.pi
				self.h = angle / (2 * math.pi)
				changed = True
			# Check if clicking on SV square
			elif dist < inner_radius or self.dragging_sv:
				self.dragging_sv = True
				self.dragging_wheel = False
				# Clamp to SV square
				self.s = max(0, min(1, (mouse_x - sv_x) / sv_size))
				self.v = max(0, min(1, 1 - (mouse_y - sv_y) / sv_size))
				changed = True
		else:
			self.dragging_wheel = False
			self.dragging_sv = False

		return changed, *self.get_rgb()

# Singleton for easy use
_picker = None

def color_picker_hsv(label, r, g, b, size=200):
	"""
	Draw an HSV color picker widget.
	Returns (changed, r, g, b)
	"""
	global _picker
	if _picker is None or _picker.size != size:
		_picker = ColorPicker(size)

	# Sync input color
	_picker.set_rgb(r, g, b)

	return _picker.draw(label)