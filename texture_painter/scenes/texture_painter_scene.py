"""
Texture Painter using ImGui for UI
"""
import os
import math
import builtins
from engine.scene import Scene
from engine.imgui_manager import ImGuiManager
from texture_painter.orbit_camera import OrbitCamera
from texture_painter.gui.color_picker import color_picker_hsv

try:
	from texture_painter.painting_system import PaintingSystem

	HAS_PAINTING = True
except ImportError:
	HAS_PAINTING = False
	print("Warning: painting_system not found")
import imgui

from panda3d.core import (
	GeomNode, BitMask32, Point3, Vec3, Vec4, LineSegs, NodePath
)

# Try to import Bullet physics
try:
	from panda3d.bullet import BulletWorld, BulletRigidBodyNode, BulletTriangleMesh, BulletTriangleMeshShape

	HAS_BULLET = True
except ImportError:
	HAS_BULLET = False
	print("Warning: panda3d-bullet not found. Brush cursor will use bounding box collision.")

# Texture types for PBR workflow
TEXTURE_TYPES = [
	('Diffuse/Albedo', 'diffuse', 'Base color of the material'),
	('Normal', 'normal', 'Surface detail via normal mapping'),
	('Roughness', 'roughness', 'Surface roughness (0=smooth, 1=rough)'),
	('Metallic', 'metallic', 'Metalness (0=dielectric, 1=metal)'),
	('Ambient Occlusion', 'ao', 'Ambient occlusion for soft shadows'),
	('Emission', 'emission', 'Self-illumination/glow'),
	('Height/Displacement', 'height', 'Height map for displacement'),
	('Opacity', 'opacity', 'Transparency mask'),
]

TEXTURE_SIZES = [256, 512, 1024, 2048, 4096]

class TexturePainterScene(Scene):
	"""3D Texture Painting Application using ImGui"""

	def __init__(self, engine):
		super().__init__(engine, 'texture_painter')
		self.imgui = None

		# Model state
		self.model = None
		self.model_path = None
		self.model_name = "No model loaded"

		# Camera
		self.orbit_camera = None

		# Textures list - each texture has layers
		self.textures = []
		self.selected_texture_index = -1

		# Brush settings
		self.brush_size = 20
		self.brush_opacity = 100
		self.brush_hardness = 80
		self.brush_color = [1.0, 0.5, 0.2]

		# Brush shapes: 0=Round, 1=Square, 2=Soft, 3=Flat
		self.brush_shapes = ['Round', 'Square', 'Soft', 'Flat']
		self.brush_shape_index = 0
		self.brush_angle = 0  # Rotation angle for brush
		self.brush_spacing = 25  # Percentage of brush size

		# Tools
		self.tools = ['Brush', 'Fill']
		self.current_tool = 0  # 0=Brush, 1=Fill

		# Pen/Tablet settings
		self.pen_pressure_size = True  # Pressure affects size
		self.pen_pressure_opacity = True  # Pressure affects opacity
		self.pen_pressure_hardness = False  # Pressure affects hardness
		self.pen_size_min = 10  # Minimum size percentage when pressure = 0
		self.pen_opacity_min = 20  # Minimum opacity percentage when pressure = 0
		self.pen_smoothing = 50  # Stroke smoothing 0-100
		self.show_pen_panel = True  # Show pen settings panel

		# View options
		self.show_grid = True
		self.show_wireframe = False

		# Sidebar configuration
		self.left_sidebar_width = 220
		self.right_sidebar_width = 220
		self.sidebar_sections = {
			'tools': True,  # Collapsed state
			'brush': True,
			'pen': False,  # Collapsed by default
			'textures': True,
			'layers': True,
			'history': True,
			'lighting': False,
		}

		# Panel visibility
		self.show_panels = {
			'tools': True,
			'brush': True,
			'pen': True,
			'textures': True,
			'layers': True,
			'history': True,
			'lighting': True,
			'axis_gizmo': True,
		}

		# Panel order (can be reordered by dragging)
		self.left_panel_order = ['tools', 'brush', 'pen']
		self.right_panel_order = ['textures', 'layers', 'history', 'lighting']

		# Lighting presets
		self.lighting_preset = 0  # 0=Studio, 1=Outdoor, 2=Flat, 3=Rim
		self.lighting_presets = ['Studio', 'Outdoor', 'Flat', 'Rim Light']
		self.lights = []

		# Scene objects
		self.grid = None
		self.origin_gizmo = None

		# Dialog states
		self.show_new_texture_dialog = False
		self.new_texture_type_index = 0
		self.new_texture_size_index = 2  # Default 1024
		self.new_texture_name = ""

		# Rename state
		self._renaming_texture = -1
		self._rename_buffer = ""
		self._renaming_layer = -1
		self._layer_rename_buffer = ""

		# File browser state (simple version)
		self.show_open_dialog = False
		self._config_file = os.path.expanduser("~/.texture_painter_config")
		self.file_browser_path = self._load_last_directory()
		self.file_browser_files = []
		self.file_browser_selected = ""
		self.file_browser_index = 0  # For keyboard navigation

		# Brush cursor
		self.brush_cursor = None
		self.brush_hit_pos = None
		self.brush_hit_normal = None

		# Bullet physics for raycasting
		self.bullet_world = None
		self.bullet_body = None
		self._raycast_debug = False
		self._hit_debug_count = 0

		# Painting system
		if HAS_PAINTING:
			self.painting_system = PaintingSystem()
		else:
			self.painting_system = None
		self.is_painting = False
		self.last_paint_pos = None

		# Track previous brush settings for cursor update
		self._prev_brush_size = None
		self._prev_brush_shape = None
		self._prev_brush_angle = None
		self._prev_brush_color = None

	def on_enter(self):
		super().on_enter()
		self.imgui = ImGuiManager(self.engine)
		self._setup_camera()
		self._setup_lighting()
		self._setup_grid()
		self._setup_collision()
		self._setup_brush_cursor()
		self._setup_keyboard_shortcuts()

		# Start without any model - user loads via File > Open
		print("Ready - use File > Open to load a model, or File > New Primitive for a test shape")

	def _setup_keyboard_shortcuts(self):
		"""Setup keyboard shortcuts for undo/redo etc"""
		builtins.base.accept('control-z', self._on_undo)
		builtins.base.accept('control-y', self._on_redo)
		builtins.base.accept('control-shift-z', self._on_redo)  # Alternative redo
		builtins.base.accept('control-o', self._on_open)
		# Tool shortcuts
		builtins.base.accept('b', self._select_brush_tool)
		builtins.base.accept('g', self._select_fill_tool)

	def _on_open(self):
		"""Handle Ctrl+O"""
		self.show_open_dialog = True
		self._refresh_file_browser()

	def _select_brush_tool(self):
		self.current_tool = 0

	def _select_fill_tool(self):
		self.current_tool = 1

	def _on_undo(self):
		"""Handle Ctrl+Z"""
		if self.painting_system:
			if self.painting_system.undo():
				self._sync_ui_from_painting_system()

	def _on_redo(self):
		"""Handle Ctrl+Y or Ctrl+Shift+Z"""
		if self.painting_system:
			if self.painting_system.redo():
				self._sync_ui_from_painting_system()

	def _sync_ui_from_painting_system(self):
		"""Sync UI state after undo/redo"""
		if not self.painting_system:
			return
		# Sync selected layer in UI
		if self.textures and 0 <= self.selected_texture_index < len(self.textures):
			tex = self.textures[self.selected_texture_index]
			tex['selected_layer'] = self.painting_system.active_layer_index
			# Also sync layer count in UI texture
			tex['layers'] = [{'name': l['name'], 'opacity': l['opacity'], 'visible': l['visible']}
											 for l in self.painting_system.layers]

	def _setup_lighting(self):
		"""Setup scene lighting using preset system"""
		self._apply_lighting_preset(self.lighting_preset)

	def _setup_grid(self):
		"""Create the ground grid and origin marker"""
		from engine import colors

		# Grid
		self.grid = self.engine.utils.create_grid(30, colors.gray)
		self.grid.reparentTo(builtins.base.render)

		# Origin axes (XYZ gizmo at center)
		self.origin_gizmo = builtins.base.render.attachNewNode("origin_gizmo")
		axis_length = 1.0

		# X axis - red
		x_axis = self.engine.utils.create_line((0, 0, 0), (axis_length, 0, 0), colors.red)
		x_axis.reparentTo(self.origin_gizmo)

		# Y axis - green
		y_axis = self.engine.utils.create_line((0, 0, 0), (0, axis_length, 0), colors.green)
		y_axis.reparentTo(self.origin_gizmo)

		# Z axis - blue
		z_axis = self.engine.utils.create_line((0, 0, 0), (0, 0, axis_length), colors.blue)
		z_axis.reparentTo(self.origin_gizmo)

	def _setup_camera(self):
		"""Setup orbit camera"""
		self.orbit_camera = OrbitCamera(
			self.engine,
			target=(0, 0, 0),
			distance=5.0,
			yaw=45.0,
			pitch=30.0
		)
		self.engine.renderer.set_camera(self.orbit_camera)

	def _setup_collision(self):
		"""Setup Bullet physics world for brush raycasting"""
		if HAS_BULLET:
			self.bullet_world = BulletWorld()
			print("Bullet physics initialized")
		else:
			self.bullet_world = None
			print("WARNING: Bullet physics not available - brush cursor won't work")

	def _setup_brush_cursor(self):
		"""Create the brush cursor visual (a circle that follows the surface)"""
		self.brush_cursor = builtins.base.render.attachNewNode("brush_cursor")
		self._update_brush_cursor_geometry()

	def _update_brush_cursor_geometry(self):
		"""Rebuild brush cursor geometry based on current brush settings"""
		# Remove old geometry
		self.brush_cursor.node().removeAllChildren()
		for child in self.brush_cursor.getChildren():
			child.removeNode()

		# Create circle using LineSegs
		segs = LineSegs()
		segs.setThickness(2.0)

		r, g, b = self.brush_color
		segs.setColor(r, g, b, 1.0)

		# Circle radius in world units (brush_size is in pixels, approximate conversion)
		radius = self.brush_size * 0.01  # Scale factor - adjust as needed
		segments = 32

		shape = self.brush_shapes[self.brush_shape_index]

		if shape in ['Round', 'Soft']:
			# Draw circle
			for i in range(segments + 1):
				angle = (i / segments) * 2 * math.pi
				x = math.cos(angle) * radius
				y = math.sin(angle) * radius
				if i == 0:
					segs.moveTo(x, y, 0)
				else:
					segs.drawTo(x, y, 0)
		elif shape == 'Square':
			# Draw square
			segs.moveTo(-radius, -radius, 0)
			segs.drawTo(radius, -radius, 0)
			segs.drawTo(radius, radius, 0)
			segs.drawTo(-radius, radius, 0)
			segs.drawTo(-radius, -radius, 0)
		elif shape == 'Flat':
			# Draw rotated rectangle
			angle_rad = math.radians(self.brush_angle)
			hw = radius
			hh = radius * 0.3
			cos_a = math.cos(angle_rad)
			sin_a = math.sin(angle_rad)
			corners = [
				(cos_a * (-hw) - sin_a * (-hh), sin_a * (-hw) + cos_a * (-hh)),
				(cos_a * (hw) - sin_a * (-hh), sin_a * (hw) + cos_a * (-hh)),
				(cos_a * (hw) - sin_a * (hh), sin_a * (hw) + cos_a * (hh)),
				(cos_a * (-hw) - sin_a * (hh), sin_a * (-hw) + cos_a * (hh)),
			]
			segs.moveTo(corners[0][0], corners[0][1], 0)
			for cx, cy in corners[1:]:
				segs.drawTo(cx, cy, 0)
			segs.drawTo(corners[0][0], corners[0][1], 0)

		# Add crosshair at center
		cross_size = radius * 0.2
		segs.moveTo(-cross_size, 0, 0)
		segs.drawTo(cross_size, 0, 0)
		segs.moveTo(0, -cross_size, 0)
		segs.drawTo(0, cross_size, 0)

		cursor_geom = segs.create()
		self.brush_cursor.attachNewNode(cursor_geom)
		self.brush_cursor.setLightOff()
		self.brush_cursor.setBin("fixed", 40)
		self.brush_cursor.setDepthTest(False)
		self.brush_cursor.setDepthWrite(False)

	def _update_brush_raycast(self):
		"""Update brush position via Bullet raycast"""
		# Hide brush cursor for non-brush tools
		if self.current_tool != 0:  # Not brush tool
			if self.brush_cursor:
				self.brush_cursor.hide()
			self.brush_hit_pos = None
			return

		if not self.model or not self.bullet_world or not self.bullet_body:
			if self.brush_cursor:
				self.brush_cursor.hide()
			self.brush_hit_pos = None
			return

		# Don't check ImGui capture when actively painting - we need raycast updates
		if not self.is_painting:
			if self.imgui and self.imgui.want_capture_mouse():
				self.brush_cursor.hide()
				return

		# Get mouse position
		if not builtins.base.mouseWatcherNode.hasMouse():
			self.brush_cursor.hide()
			return

		mpos = builtins.base.mouseWatcherNode.getMouse()

		# Get ray from camera through mouse
		cam = builtins.base.camera
		lens = builtins.base.camLens

		# Near and far points in camera space
		near_point = Point3()
		far_point = Point3()
		lens.extrude(mpos, near_point, far_point)

		# Transform to world space
		from_pos = builtins.base.render.getRelativePoint(cam, near_point)
		to_pos = builtins.base.render.getRelativePoint(cam, far_point)

		# Bullet raycast
		result = self.bullet_world.rayTestClosest(from_pos, to_pos)

		if result.hasHit():
			self.brush_hit_pos = result.getHitPos()
			self.brush_hit_normal = result.getHitNormal()

			# Position cursor at hit point
			self.brush_cursor.setPos(self.brush_hit_pos)

			# Orient cursor to align with surface normal
			# Create a coordinate frame from the normal
			up = self.brush_hit_normal

			# Find a perpendicular vector for right
			if abs(up.z) < 0.9:
				right = up.cross(Vec3(0, 0, 1))
			else:
				right = up.cross(Vec3(0, 1, 0))
			right.normalize()

			forward = right.cross(up)
			forward.normalize()

			# Set rotation using lookAt
			self.brush_cursor.lookAt(
				self.brush_hit_pos + forward,
				up
			)

			self.brush_cursor.show()
		else:
			self.brush_cursor.hide()
			self.brush_hit_pos = None
			self.brush_hit_normal = None

	def _check_brush_cursor_update(self):
		"""Check if brush settings changed and update cursor geometry"""
		needs_update = False

		if self._prev_brush_size != self.brush_size:
			self._prev_brush_size = self.brush_size
			needs_update = True

		if self._prev_brush_shape != self.brush_shape_index:
			self._prev_brush_shape = self.brush_shape_index
			needs_update = True

		if self._prev_brush_angle != self.brush_angle:
			self._prev_brush_angle = self.brush_angle
			needs_update = True

		if self._prev_brush_color != self.brush_color:
			self._prev_brush_color = self.brush_color.copy()
			needs_update = True

		if needs_update and self.brush_cursor:
			self._update_brush_cursor_geometry()

	def _setup_bullet_collision(self, model):
		"""Create Bullet collision mesh from model geometry"""
		if not HAS_BULLET:
			return

		# Remove old collision body if exists
		if self.bullet_body:
			self.bullet_world.removeRigidBody(self.bullet_body)
			self.bullet_body = None

		# Create triangle mesh from model geometry
		mesh = BulletTriangleMesh()

		# Find all GeomNodes in the model
		geom_nodes = model.findAllMatches('**/+GeomNode')

		for geom_np in geom_nodes:
			geom_node = geom_np.node()
			transform = geom_np.getTransform(model)

			for i in range(geom_node.getNumGeoms()):
				geom = geom_node.getGeom(i)
				mesh.addGeom(geom, True, transform)

		if mesh.getNumTriangles() == 0:
			print("Warning: No triangles found in model for collision")
			return

		print(f"Created collision mesh with {mesh.getNumTriangles()} triangles")

		# Create shape and body
		shape = BulletTriangleMeshShape(mesh, dynamic=False)
		body_node = BulletRigidBodyNode('model_collision')
		body_node.addShape(shape)
		body_node.setMass(0)  # Static object

		# Attach to render and add to world
		body_np = builtins.base.render.attachNewNode(body_node)
		body_np.setPos(model.getPos())
		body_np.setHpr(model.getHpr())
		body_np.setScale(model.getScale())

		self.bullet_world.attachRigidBody(body_node)
		self.bullet_body = body_node

	def handle_input(self, input_handler):
		super().handle_input(input_handler)

		# Only handle 3D input if ImGui doesn't want mouse
		if self.imgui and not self.imgui.want_capture_mouse():
			if self.orbit_camera:
				self.orbit_camera.handle_input(input_handler)

	def update(self, dt):
		super().update(dt)

		# Update orbit camera (pass imgui state for scroll handling)
		if self.orbit_camera:
			imgui_wants_mouse = self.imgui.want_capture_mouse() if self.imgui else False
			self.orbit_camera.update(dt, imgui_wants_mouse)

		# Update brush cursor and handle painting
		self._update_brush_raycast()
		try:
			self._handle_painting()
		except Exception as e:
			print(f"Painting error: {e}")

		if not self.imgui:
			return

		try:
			self.imgui.begin_frame()

			self._draw_menu_bar()
			self._draw_left_sidebar()
			self._draw_right_sidebar()
			if self.show_panels['axis_gizmo']:
				self._draw_axis_gizmo()

			# Dialogs
			if self.show_new_texture_dialog:
				self._draw_new_texture_dialog()
			if self.show_open_dialog:
				self._draw_open_model_dialog()

			self.imgui.end_frame()
		except Exception as e:
			print(f"ImGui error: {e}")
			import traceback
			traceback.print_exc()

		# Update brush cursor geometry if settings changed (do after imgui frame)
		self._check_brush_cursor_update()

	def _handle_painting(self):
		"""Handle painting input"""
		# Check if painting is available
		if not self.painting_system:
			return

		# Check if layers have been created
		if not self.textures or not self.painting_system.layers:
			# Only print once
			if not hasattr(self, '_no_layers_debug'):
				print(f"No textures/layers: textures={len(self.textures) if self.textures else 0}, layers={len(self.painting_system.layers) if self.painting_system and self.painting_system.layers else 0}")
				self._no_layers_debug = True
			return

		# Check mouse button state first
		try:
			mouse_watcher = builtins.base.mouseWatcherNode
			mouse_down = mouse_watcher.isButtonDown('mouse1')
		except:
			return

		if not mouse_down:
			# End stroke when mouse released
			if self.is_painting:
				self.painting_system.end_stroke()
			self.is_painting = False
			self.last_paint_pos = None
			return

		# Mouse is down - check other conditions
		if not self.model:
			return

		# Check if ImGui wants mouse - skip this check when actively painting
		# Once we start painting, continue until mouse is released
		if not self.is_painting:
			if self.imgui and self.imgui.want_capture_mouse():
				return

		# Handle Fill tool - only triggers on first click
		if self.current_tool == 1:  # Fill tool
			if not self.is_painting:
				self.painting_system.fill_layer(self.brush_color)
				self.is_painting = True  # Prevent re-triggering while held
			return

		# Brush tool (current_tool == 0) needs hit position
		if not self.brush_hit_pos:
			return

		# We have a valid hit position - paint!

		# Begin stroke (saves history) on first paint
		if not self.is_painting:
			self.painting_system.begin_stroke()

		# Get hit normal for face filtering
		hit_normal = getattr(self, 'brush_hit_normal', None)

		if self.is_painting and self.last_paint_pos:
			# Continue stroke - paint from last position to current position
			self.painting_system.paint_stroke_world(
				self.last_paint_pos, self.brush_hit_pos,
				self.brush_color,
				self.brush_size,
				self.brush_opacity,
				self.brush_hardness,
				self.brush_spacing,
				self.brush_shapes[self.brush_shape_index],
				hit_normal=hit_normal
			)
		else:
			# Start new stroke - just paint at current point
			self.painting_system.paint_at_world_pos(
				self.brush_hit_pos,
				self.brush_color,
				self.brush_size,
				self.brush_opacity,
				self.brush_hardness,
				self.brush_shapes[self.brush_shape_index],
				hit_normal=hit_normal
			)

		self.last_paint_pos = self.brush_hit_pos
		self.is_painting = True

		# Flush paint to GPU every frame
		self.painting_system.flush_paint()

	def _draw_menu_bar(self):
		"""Draw main menu bar"""
		if imgui.begin_main_menu_bar():
			if imgui.begin_menu("File"):
				clicked, _ = imgui.menu_item("New Project", "Ctrl+N")
				if clicked:
					self._on_new()

				clicked, _ = imgui.menu_item("Open Model...", "Ctrl+O")
				if clicked:
					self._on_open()

				if imgui.begin_menu("New Primitive"):
					clicked, _ = imgui.menu_item("Cube")
					if clicked:
						self._create_test_cube()
					imgui.end_menu()

				imgui.separator()

				clicked, _ = imgui.menu_item("Save Textures", "Ctrl+S")
				if clicked:
					self._on_save()

				clicked, _ = imgui.menu_item("Export All...", "")
				if clicked:
					self._on_export()

				imgui.separator()

				clicked, _ = imgui.menu_item("Exit", "Alt+F4")
				if clicked:
					self._on_exit()

				imgui.end_menu()

			if imgui.begin_menu("Edit"):
				clicked, _ = imgui.menu_item("Undo", "Ctrl+Z")
				clicked, _ = imgui.menu_item("Redo", "Ctrl+Y")
				imgui.separator()
				clicked, _ = imgui.menu_item("Clear Layer")
				imgui.end_menu()

			if imgui.begin_menu("View"):
				clicked, _ = imgui.menu_item("Reset Camera")
				if clicked:
					self._reset_camera()
				imgui.separator()
				clicked, self.show_grid = imgui.menu_item("Show Grid", "", self.show_grid)
				if clicked and self.grid:
					if self.show_grid:
						self.grid.show()
					else:
						self.grid.hide()
				clicked, self.show_wireframe = imgui.menu_item("Show Wireframe", "", self.show_wireframe)
				imgui.end_menu()

			if imgui.begin_menu("Panels"):
				imgui.text("Left Sidebar")
				_, self.show_panels['tools'] = imgui.menu_item("  Tools", "", self.show_panels['tools'])
				_, self.show_panels['brush'] = imgui.menu_item("  Brush", "", self.show_panels['brush'])
				_, self.show_panels['pen'] = imgui.menu_item("  Pen Pressure", "", self.show_panels['pen'])
				imgui.separator()
				imgui.text("Right Sidebar")
				_, self.show_panels['textures'] = imgui.menu_item("  Textures", "", self.show_panels['textures'])
				_, self.show_panels['layers'] = imgui.menu_item("  Layers", "", self.show_panels['layers'])
				_, self.show_panels['history'] = imgui.menu_item("  History", "", self.show_panels['history'])
				_, self.show_panels['lighting'] = imgui.menu_item("  Lighting", "", self.show_panels['lighting'])
				imgui.separator()
				_, self.show_panels['axis_gizmo'] = imgui.menu_item("Axis Gizmo", "", self.show_panels['axis_gizmo'])
				imgui.end_menu()

			imgui.end_main_menu_bar()

	def _draw_left_sidebar(self):
		"""Draw left sidebar with tools, brush, and pen settings"""
		# Check if any left panels are visible
		if not any([self.show_panels[p] for p in self.left_panel_order]):
			return

		win_height = builtins.base.win.getYSize()
		menu_bar_height = 20

		imgui.set_next_window_position(0, menu_bar_height, imgui.ALWAYS)
		imgui.set_next_window_size(self.left_sidebar_width, win_height - menu_bar_height, imgui.ALWAYS)

		flags = (imgui.WINDOW_NO_MOVE | imgui.WINDOW_NO_RESIZE |
						 imgui.WINDOW_NO_COLLAPSE | imgui.WINDOW_NO_TITLE_BAR)

		imgui.begin("##LeftSidebar", flags=flags)

		# Draw panels in order
		self._draw_reorderable_panels(self.left_panel_order, 'left')

		imgui.end()

	def _draw_right_sidebar(self):
		"""Draw right sidebar with textures, layers, history, and lighting"""
		# Check if any right panels are visible
		if not any([self.show_panels[p] for p in self.right_panel_order]):
			return

		win_width = builtins.base.win.getXSize()
		win_height = builtins.base.win.getYSize()
		menu_bar_height = 20

		imgui.set_next_window_position(win_width - self.right_sidebar_width, menu_bar_height, imgui.ALWAYS)
		imgui.set_next_window_size(self.right_sidebar_width, win_height - menu_bar_height, imgui.ALWAYS)

		flags = (imgui.WINDOW_NO_MOVE | imgui.WINDOW_NO_RESIZE |
						 imgui.WINDOW_NO_COLLAPSE | imgui.WINDOW_NO_TITLE_BAR)

		imgui.begin("##RightSidebar", flags=flags)

		# Draw panels in order
		self._draw_reorderable_panels(self.right_panel_order, 'right')

		imgui.end()

	def _draw_reorderable_panels(self, panel_order, side):
		"""Draw panels in order"""
		# Panel display names and content functions
		panel_info = {
			'tools': ('Tools', self._draw_tools_content),
			'brush': ('Brush', self._draw_brush_content),
			'pen': ('Pen / Tablet', self._draw_pen_content),
			'textures': ('Textures', self._draw_textures_content),
			'layers': ('Layers', self._draw_layers_content),
			'history': ('History', self._draw_history_content),
			'lighting': ('Lighting', self._draw_lighting_content),
		}

		for panel_id in panel_order:
			if not self.show_panels.get(panel_id, False):
				continue

			display_name, content_func = panel_info[panel_id]

			# Draw the collapsing header
			expanded, visible = imgui.collapsing_header(display_name, True)

			# Handle close button
			if not visible:
				self.show_panels[panel_id] = False
				continue

			# Draw content if expanded
			if expanded:
				content_func()

	def _draw_axis_gizmo(self):
		"""Draw an axis orientation gizmo in the top-right corner"""
		import math

		# Panel size and position
		gizmo_size = 100
		margin = 10
		win_width = builtins.base.win.getXSize()
		menu_bar_height = 20

		# Position to the left of the right sidebar
		pos_x = win_width - self.right_sidebar_width - gizmo_size - margin
		pos_y = menu_bar_height + margin

		imgui.set_next_window_position(pos_x, pos_y, imgui.ALWAYS)
		imgui.set_next_window_size(gizmo_size, gizmo_size + 20, imgui.ALWAYS)

		flags = (imgui.WINDOW_NO_MOVE | imgui.WINDOW_NO_RESIZE |
						 imgui.WINDOW_NO_COLLAPSE | imgui.WINDOW_NO_SCROLLBAR)

		imgui.begin("Axis", flags=flags)

		# Get camera orientation
		if self.orbit_camera:
			heading = self.orbit_camera.yaw  # Rotation around Z (yaw)
			pitch = self.orbit_camera.pitch  # Rotation around X (pitch)
		else:
			heading = 0
			pitch = 0

		# Convert to radians
		h_rad = math.radians(heading)
		p_rad = math.radians(pitch)

		# Get draw list and center position
		draw_list = imgui.get_window_draw_list()
		win_pos = imgui.get_window_position()
		center_x = win_pos[0] + gizmo_size / 2
		center_y = win_pos[1] + gizmo_size / 2 + 10  # Offset for title bar

		axis_length = 35

		# Calculate axis end points based on camera rotation
		# X axis (red) - points right in world space
		x_x = math.cos(h_rad)
		x_y = -math.sin(h_rad) * math.sin(p_rad)

		# Y axis (green) - points forward in world space
		y_x = math.sin(h_rad)
		y_y = math.cos(h_rad) * math.sin(p_rad)

		# Z axis (blue) - points up in world space
		z_x = 0
		z_y = -math.cos(p_rad)

		# Draw axes (draw back-to-front based on which points toward camera)
		axes = [
			('X', x_x, x_y, imgui.get_color_u32_rgba(1, 0, 0, 1), imgui.get_color_u32_rgba(0.5, 0, 0, 1)),
			('Y', y_x, y_y, imgui.get_color_u32_rgba(0, 1, 0, 1), imgui.get_color_u32_rgba(0, 0.5, 0, 1)),
			('Z', z_x, z_y, imgui.get_color_u32_rgba(0, 0.5, 1, 1), imgui.get_color_u32_rgba(0, 0.25, 0.5, 1)),
		]

		# Sort by depth (y component - more negative = further back)
		axes.sort(key=lambda a: a[2], reverse=True)

		for name, ax, ay, color, dark_color in axes:
			end_x = center_x + ax * axis_length
			end_y = center_y + ay * axis_length

			# Use darker color if pointing away (negative y means toward camera)
			line_color = color if ay <= 0 else dark_color

			# Draw axis line
			draw_list.add_line(center_x, center_y, end_x, end_y, line_color, 2.0)

			# Draw axis label
			draw_list.add_text(end_x - 4, end_y - 8, line_color, name)

		# Draw center dot
		draw_list.add_circle_filled(center_x, center_y, 3, imgui.get_color_u32_rgba(1, 1, 1, 1))

		imgui.end()

	def _draw_tools_content(self):
		"""Draw tools content for sidebar"""
		button_size = 32

		# Brush tool
		is_brush = self.current_tool == 0
		if is_brush:
			imgui.push_style_color(imgui.COLOR_BUTTON, 0.3, 0.5, 0.8, 1.0)
		if imgui.button("B##brush", button_size, button_size):
			self.current_tool = 0
		if imgui.is_item_hovered():
			imgui.set_tooltip("Brush (B)")
		if is_brush:
			imgui.pop_style_color()

		imgui.same_line()

		# Fill tool
		is_fill = self.current_tool == 1
		if is_fill:
			imgui.push_style_color(imgui.COLOR_BUTTON, 0.3, 0.5, 0.8, 1.0)
		if imgui.button("G##fill", button_size, button_size):
			self.current_tool = 1
		if imgui.is_item_hovered():
			imgui.set_tooltip("Fill Layer (G)")
		if is_fill:
			imgui.pop_style_color()

		imgui.spacing()

	def _draw_brush_content(self):
		"""Draw brush settings content for sidebar"""
		# Brush shape selection
		imgui.text("Shape")
		draw_list = imgui.get_window_draw_list()
		p = imgui.get_cursor_screen_pos()

		# Draw shape buttons
		shape_size = 36
		for i, shape_name in enumerate(self.brush_shapes):
			if i > 0:
				imgui.same_line()

			selected = (i == self.brush_shape_index)

			# Button background
			bx = p[0] + i * (shape_size + 4)
			by = p[1]

			if selected:
				draw_list.add_rect_filled(bx, by, bx + shape_size, by + shape_size,
																	imgui.get_color_u32_rgba(0.3, 0.5, 0.8, 1.0))
			else:
				draw_list.add_rect_filled(bx, by, bx + shape_size, by + shape_size,
																	imgui.get_color_u32_rgba(0.2, 0.2, 0.2, 1.0))

			# Draw shape preview
			cx = bx + shape_size / 2
			cy = by + shape_size / 2
			preview_r = shape_size * 0.35
			white = imgui.get_color_u32_rgba(0.9, 0.9, 0.9, 1.0)

			if shape_name == 'Round':
				draw_list.add_circle_filled(cx, cy, preview_r, white)
			elif shape_name == 'Square':
				draw_list.add_rect_filled(cx - preview_r, cy - preview_r,
																	cx + preview_r, cy + preview_r, white)
			elif shape_name == 'Soft':
				for ring in range(5, 0, -1):
					alpha = ring / 5.0
					col = imgui.get_color_u32_rgba(0.9, 0.9, 0.9, alpha)
					draw_list.add_circle_filled(cx, cy, preview_r * ring / 5, col)
			elif shape_name == 'Flat':
				draw_list.add_rect_filled(cx - preview_r, cy - preview_r * 0.3,
																	cx + preview_r, cy + preview_r * 0.3, white)

		# Invisible buttons for selection
		imgui.set_cursor_screen_pos((p[0], p[1]))
		for i in range(len(self.brush_shapes)):
			if imgui.invisible_button(f"##shape{i}", shape_size, shape_size):
				self.brush_shape_index = i
			if i < len(self.brush_shapes) - 1:
				imgui.same_line(spacing=4)

		imgui.dummy(0, 5)

		# Brush parameters
		imgui.separator()
		changed, self.brush_size = imgui.slider_int("Size", self.brush_size, 1, 200)
		changed, self.brush_opacity = imgui.slider_int("Opacity", self.brush_opacity, 1, 100)
		changed, self.brush_hardness = imgui.slider_int("Hardness", self.brush_hardness, 0, 100)
		changed, self.brush_spacing = imgui.slider_int("Spacing", self.brush_spacing, 1, 100)

		if self.brush_shapes[self.brush_shape_index] == 'Flat':
			changed, self.brush_angle = imgui.slider_int("Angle", self.brush_angle, 0, 180)

		# Brush preview
		imgui.separator()
		imgui.text("Preview")

		preview_size = 80
		p = imgui.get_cursor_screen_pos()
		preview_cx = p[0] + preview_size / 2
		preview_cy = p[1] + preview_size / 2

		draw_list.add_rect_filled(p[0], p[1], p[0] + preview_size, p[1] + preview_size,
															imgui.get_color_u32_rgba(0.15, 0.15, 0.15, 1.0))

		r, g, b = self.brush_color
		brush_col = imgui.get_color_u32_rgba(r, g, b, self.brush_opacity / 100.0)
		display_size = min(self.brush_size, preview_size - 10) / 2

		shape = self.brush_shapes[self.brush_shape_index]
		if shape == 'Round':
			draw_list.add_circle_filled(preview_cx, preview_cy, display_size, brush_col)
		elif shape == 'Square':
			draw_list.add_rect_filled(preview_cx - display_size, preview_cy - display_size,
																preview_cx + display_size, preview_cy + display_size, brush_col)
		elif shape == 'Soft':
			steps = 10
			for i in range(steps, 0, -1):
				t = i / steps
				alpha = (self.brush_opacity / 100.0) * (1 - (1 - t) ** (self.brush_hardness / 30 + 1))
				col = imgui.get_color_u32_rgba(r, g, b, alpha)
				draw_list.add_circle_filled(preview_cx, preview_cy, display_size * t, col)
		elif shape == 'Flat':
			import math
			angle_rad = math.radians(self.brush_angle)
			hw = display_size
			hh = display_size * 0.3
			cos_a = math.cos(angle_rad)
			sin_a = math.sin(angle_rad)
			corners = [
				(preview_cx + cos_a * (-hw) - sin_a * (-hh), preview_cy + sin_a * (-hw) + cos_a * (-hh)),
				(preview_cx + cos_a * (hw) - sin_a * (-hh), preview_cy + sin_a * (hw) + cos_a * (-hh)),
				(preview_cx + cos_a * (hw) - sin_a * (hh), preview_cy + sin_a * (hw) + cos_a * (hh)),
				(preview_cx + cos_a * (-hw) - sin_a * (hh), preview_cy + sin_a * (-hw) + cos_a * (hh)),
			]
			draw_list.add_quad_filled(corners[0][0], corners[0][1], corners[1][0], corners[1][1],
																corners[2][0], corners[2][1], corners[3][0], corners[3][1], brush_col)

		imgui.dummy(preview_size, preview_size)

		imgui.separator()
		imgui.text("Color")

		r, g, b = self.brush_color
		changed, r, g, b = color_picker_hsv("##colorpicker", r, g, b, size=160)
		if changed:
			self.brush_color = [r, g, b]

		imgui.spacing()

	def _draw_pen_content(self):
		"""Draw pen/tablet settings content for sidebar"""
		imgui.text("Pressure Controls")
		imgui.separator()

		_, self.pen_pressure_size = imgui.checkbox("Size", self.pen_pressure_size)
		if self.pen_pressure_size:
			imgui.same_line()
			imgui.push_item_width(80)
			_, self.pen_size_min = imgui.slider_int("##sizemin", self.pen_size_min, 0, 100)
			imgui.pop_item_width()
			if imgui.is_item_hovered():
				imgui.set_tooltip("Minimum size %")

		_, self.pen_pressure_opacity = imgui.checkbox("Opacity", self.pen_pressure_opacity)
		if self.pen_pressure_opacity:
			imgui.same_line()
			imgui.push_item_width(80)
			_, self.pen_opacity_min = imgui.slider_int("##opamin", self.pen_opacity_min, 0, 100)
			imgui.pop_item_width()
			if imgui.is_item_hovered():
				imgui.set_tooltip("Minimum opacity %")

		_, self.pen_pressure_hardness = imgui.checkbox("Hardness", self.pen_pressure_hardness)

		imgui.separator()
		imgui.text("Smoothing")
		_, self.pen_smoothing = imgui.slider_int("##smooth", self.pen_smoothing, 0, 100)

		imgui.spacing()

	def _draw_textures_content(self):
		"""Draw textures content for sidebar"""
		# Model info
		imgui.text_colored(f"Model: {self.model_name}", 0.7, 0.7, 0.7)
		imgui.separator()

		# Opacity slider at top
		if 0 <= self.selected_texture_index < len(self.textures):
			tex = self.textures[self.selected_texture_index]
			imgui.text("Opacity:")
			imgui.same_line()
			imgui.push_item_width(-1)
			changed, new_opacity = imgui.slider_float(
				"##texopacity", tex['opacity'], 0.0, 1.0, f"{int(tex['opacity'] * 100)}%%"
			)
			imgui.pop_item_width()
			if changed:
				tex['opacity'] = new_opacity
				if self.painting_system:
					self.painting_system.set_texture_opacity(new_opacity)
			imgui.separator()

		# Add texture button
		if self.model is not None:
			if imgui.button("+ Add Texture"):
				self.show_new_texture_dialog = True
				self.new_texture_name = f"Texture_{len(self.textures) + 1}"
		else:
			imgui.text_colored("Load a model first", 0.5, 0.5, 0.5)

		imgui.separator()

		# Texture list
		drag_source = -1
		drag_target = -1

		for i, tex in enumerate(self.textures):
			type_colors = {
				'diffuse': (0.9, 0.9, 0.9),
				'normal': (0.5, 0.5, 1.0),
				'roughness': (0.5, 0.8, 0.5),
				'metallic': (0.8, 0.8, 0.5),
			}
			color = type_colors.get(tex['type'], (0.7, 0.7, 0.7))

			selected = (i == self.selected_texture_index)

			# Checkbox for visibility
			changed, tex['visible'] = imgui.checkbox(f"##texvis{i}", tex['visible'])
			imgui.same_line()

			# Renaming
			if self._renaming_texture == i:
				imgui.push_item_width(120)
				changed, self._rename_buffer = imgui.input_text(f"##texrename{i}", self._rename_buffer, 64)
				imgui.pop_item_width()
				if imgui.is_item_deactivated():
					if self._rename_buffer.strip():
						tex['name'] = self._rename_buffer.strip()
					self._renaming_texture = -1
			else:
				label = f"{tex['name']} ({tex['type']})"
				clicked, _ = imgui.selectable(label, selected)

				if imgui.is_item_hovered() and imgui.is_mouse_double_clicked(0):
					self._renaming_texture = i
					self._rename_buffer = tex['name']

				if clicked:
					self.selected_texture_index = i

				if imgui.begin_drag_drop_source():
					imgui.set_drag_drop_payload('TEXTURE_DND', str(i).encode())
					imgui.text(tex['name'])
					imgui.end_drag_drop_source()

				if imgui.begin_drag_drop_target():
					payload = imgui.accept_drag_drop_payload('TEXTURE_DND')
					if payload is not None:
						drag_source = int(payload.decode())
						drag_target = i
					imgui.end_drag_drop_target()

		# Handle reorder
		if drag_source >= 0 and drag_target >= 0 and drag_source != drag_target:
			tex = self.textures.pop(drag_source)
			self.textures.insert(drag_target, tex)
			if self.selected_texture_index == drag_source:
				self.selected_texture_index = drag_target

		imgui.spacing()

	def _draw_layers_content(self):
		"""Draw layers content for sidebar"""
		if self.selected_texture_index < 0 or self.selected_texture_index >= len(self.textures):
			imgui.text_colored("Select a texture", 0.5, 0.5, 0.5)
			return

		tex = self.textures[self.selected_texture_index]

		# Opacity slider
		if self.painting_system and self.painting_system.layers:
			idx = self.painting_system.active_layer_index
			if 0 <= idx < len(self.painting_system.layers):
				layer = self.painting_system.layers[idx]
				imgui.text("Opacity:")
				imgui.same_line()
				imgui.push_item_width(-1)
				changed, new_opacity = imgui.slider_float(
					"##layeropacity", layer['opacity'], 0.0, 1.0, f"{int(layer['opacity'] * 100)}%%"
				)
				imgui.pop_item_width()
				if changed:
					self.painting_system.set_layer_opacity(idx, new_opacity)

		imgui.separator()

		# Add/Remove buttons
		if imgui.button("+##addlayer", 25, 20):
			if self.painting_system:
				new_name = f"Layer {len(self.painting_system.layers) + 1}"
				self.painting_system.add_layer(new_name)
		imgui.same_line()
		if imgui.button("-##dellayer", 25, 20):
			if self.painting_system and len(self.painting_system.layers) > 1:
				self.painting_system.remove_layer(self.painting_system.active_layer_index)

		imgui.separator()

		# Layer list
		if not self.painting_system or not self.painting_system.layers:
			imgui.text_colored("No layers", 0.5, 0.5, 0.5)
			return

		selected_layer_idx = self.painting_system.active_layer_index
		drag_source = -1
		drag_target = -1

		# Display layers in reverse order (top layer first, like Photoshop)
		num_layers = len(self.painting_system.layers)
		for display_idx in range(num_layers):
			i = num_layers - 1 - display_idx  # Reverse: show highest index first
			layer = self.painting_system.layers[i]
			selected = (i == selected_layer_idx)

			# Visibility checkbox
			changed, layer['visible'] = imgui.checkbox(f"##layervis{i}", layer['visible'])
			if changed and self.painting_system:
				self.painting_system.set_layer_visible(i, layer['visible'])
			imgui.same_line()

			# Renaming
			if self._renaming_layer == i:
				imgui.push_item_width(100)
				changed, self._layer_rename_buffer = imgui.input_text(f"##layerrename{i}", self._layer_rename_buffer, 64)
				imgui.pop_item_width()
				if imgui.is_item_deactivated():
					if self._layer_rename_buffer.strip():
						layer['name'] = self._layer_rename_buffer.strip()
					self._renaming_layer = -1
			else:
				clicked, _ = imgui.selectable(layer['name'], selected)

				if imgui.is_item_hovered() and imgui.is_mouse_double_clicked(0):
					self._renaming_layer = i
					self._layer_rename_buffer = layer['name']

				if clicked:
					if self.painting_system:
						self.painting_system.set_active_layer(i)
					tex['selected_layer'] = i

				if imgui.begin_drag_drop_source():
					imgui.set_drag_drop_payload('LAYER_DND', str(i).encode())
					imgui.text(layer['name'])
					imgui.end_drag_drop_source()

				if imgui.begin_drag_drop_target():
					payload = imgui.accept_drag_drop_payload('LAYER_DND')
					if payload is not None:
						drag_source = int(payload.decode())
						drag_target = i
					imgui.end_drag_drop_target()

		# Handle reorder
		if drag_source >= 0 and drag_target >= 0 and drag_source != drag_target:
			if self.painting_system:
				self.painting_system.reorder_layer(drag_source, drag_target)

		imgui.spacing()

	def _draw_history_content(self):
		"""Draw history content for sidebar"""
		if not self.painting_system or not self.painting_system.history:
			imgui.text_colored("No history yet", 0.5, 0.5, 0.5)
			return

		# Undo/Redo buttons
		can_undo = self.painting_system.history_index > 0
		can_redo = self.painting_system.history_index < len(self.painting_system.history) - 1

		if not can_undo:
			imgui.push_style_var(imgui.STYLE_ALPHA, 0.5)
		if imgui.button("Undo"):
			if can_undo:
				self.painting_system.undo()
				self._sync_ui_from_painting_system()
		if not can_undo:
			imgui.pop_style_var()

		imgui.same_line()

		if not can_redo:
			imgui.push_style_var(imgui.STYLE_ALPHA, 0.5)
		if imgui.button("Redo"):
			if can_redo:
				self.painting_system.redo()
				self._sync_ui_from_painting_system()
		if not can_redo:
			imgui.pop_style_var()

		imgui.same_line()
		imgui.text(f"({self.painting_system.history_index + 1}/{len(self.painting_system.history)})")

		imgui.separator()

		# History list
		history = self.painting_system.get_history_list()
		current_idx = self.painting_system.history_index

		for i in range(len(history) - 1, -1, -1):
			idx, name = history[i]
			is_current = (idx == current_idx)
			is_future = (idx > current_idx)

			if is_future:
				imgui.push_style_var(imgui.STYLE_ALPHA, 0.4)
			if is_current:
				imgui.push_style_color(imgui.COLOR_TEXT, 0.3, 1.0, 0.3, 1.0)

			clicked, _ = imgui.selectable(f"{idx + 1}. {name}", is_current)

			if is_current:
				imgui.pop_style_color()
			if is_future:
				imgui.pop_style_var()

			if clicked and not is_current:
				self.painting_system.goto_history(idx)
				self._sync_ui_from_painting_system()

		imgui.spacing()

	def _draw_lighting_content(self):
		"""Draw lighting controls"""
		changed, self.lighting_preset = imgui.combo(
			"Preset", self.lighting_preset, self.lighting_presets
		)
		if changed:
			self._apply_lighting_preset(self.lighting_preset)

		imgui.spacing()
		imgui.separator()
		imgui.spacing()

		# Show current preset description
		descriptions = [
			"Three-point studio lighting",
			"Bright outdoor sun + sky",
			"Even, shadowless lighting",
			"Dramatic backlit silhouette"
		]
		imgui.text_wrapped(descriptions[self.lighting_preset])

	def _apply_lighting_preset(self, preset):
		"""Apply a lighting preset"""
		from panda3d.core import AmbientLight, DirectionalLight, PointLight
		from panda3d.core import Vec4, Vec3

		# Remove existing lights - must clearLight before removeNode
		for light in self.lights:
			builtins.base.render.clearLight(light)
			light.removeNode()
		self.lights.clear()

		if preset == 0:  # Studio
			# Key light
			key = DirectionalLight('key')
			key.setColor(Vec4(1.0, 0.98, 0.95, 1))
			key_np = builtins.base.render.attachNewNode(key)
			key_np.setHpr(45, -45, 0)
			builtins.base.render.setLight(key_np)
			self.lights.append(key_np)

			# Fill light
			fill = DirectionalLight('fill')
			fill.setColor(Vec4(0.3, 0.35, 0.4, 1))
			fill_np = builtins.base.render.attachNewNode(fill)
			fill_np.setHpr(-45, -30, 0)
			builtins.base.render.setLight(fill_np)
			self.lights.append(fill_np)

			# Back light
			back = DirectionalLight('back')
			back.setColor(Vec4(0.4, 0.4, 0.45, 1))
			back_np = builtins.base.render.attachNewNode(back)
			back_np.setHpr(180, -60, 0)
			builtins.base.render.setLight(back_np)
			self.lights.append(back_np)

			# Ambient
			amb = AmbientLight('ambient')
			amb.setColor(Vec4(0.15, 0.15, 0.18, 1))
			amb_np = builtins.base.render.attachNewNode(amb)
			builtins.base.render.setLight(amb_np)
			self.lights.append(amb_np)

		elif preset == 1:  # Outdoor
			# Sun
			sun = DirectionalLight('sun')
			sun.setColor(Vec4(1.0, 0.95, 0.8, 1))
			sun_np = builtins.base.render.attachNewNode(sun)
			sun_np.setHpr(30, -60, 0)
			builtins.base.render.setLight(sun_np)
			self.lights.append(sun_np)

			# Sky ambient
			amb = AmbientLight('sky')
			amb.setColor(Vec4(0.4, 0.45, 0.6, 1))
			amb_np = builtins.base.render.attachNewNode(amb)
			builtins.base.render.setLight(amb_np)
			self.lights.append(amb_np)

		elif preset == 2:  # Flat
			# Even ambient only
			amb = AmbientLight('flat')
			amb.setColor(Vec4(0.9, 0.9, 0.9, 1))
			amb_np = builtins.base.render.attachNewNode(amb)
			builtins.base.render.setLight(amb_np)
			self.lights.append(amb_np)

		elif preset == 3:  # Rim Light
			# Strong back light
			rim = DirectionalLight('rim')
			rim.setColor(Vec4(1.0, 1.0, 1.0, 1))
			rim_np = builtins.base.render.attachNewNode(rim)
			rim_np.setHpr(180, -30, 0)
			builtins.base.render.setLight(rim_np)
			self.lights.append(rim_np)

			# Subtle fill
			fill = DirectionalLight('fill')
			fill.setColor(Vec4(0.2, 0.2, 0.25, 1))
			fill_np = builtins.base.render.attachNewNode(fill)
			fill_np.setHpr(0, -30, 0)
			builtins.base.render.setLight(fill_np)
			self.lights.append(fill_np)

			# Dark ambient
			amb = AmbientLight('ambient')
			amb.setColor(Vec4(0.1, 0.1, 0.12, 1))
			amb_np = builtins.base.render.attachNewNode(amb)
			builtins.base.render.setLight(amb_np)
			self.lights.append(amb_np)

		# Update painting system shader lighting
		self._update_shader_lighting(preset)

	def _update_shader_lighting(self, preset):
		"""Update lighting uniforms in painting shader"""
		if not self.painting_system:
			return

		import math

		def hpr_to_dir(h, p):
			"""Convert heading/pitch to direction vector"""
			h_rad = math.radians(h)
			p_rad = math.radians(p)
			x = math.sin(h_rad) * math.cos(p_rad)
			y = -math.cos(h_rad) * math.cos(p_rad)
			z = -math.sin(p_rad)
			return (x, y, z)

		if preset == 0:  # Studio
			self.painting_system.update_lighting(
				light_dir0=hpr_to_dir(45, -45),   # Key
				light_color0=(1.0, 0.98, 0.95),
				light_dir1=hpr_to_dir(-45, -30),  # Fill
				light_color1=(0.3, 0.35, 0.4),
				ambient=(0.15, 0.15, 0.18)
			)
		elif preset == 1:  # Outdoor
			self.painting_system.update_lighting(
				light_dir0=hpr_to_dir(30, -60),   # Sun
				light_color0=(1.0, 0.95, 0.8),
				light_dir1=(0, 0, -1),            # No second light
				light_color1=(0, 0, 0),
				ambient=(0.4, 0.45, 0.6)
			)
		elif preset == 2:  # Flat
			self.painting_system.update_lighting(
				light_dir0=(0, 0, -1),
				light_color0=(0, 0, 0),
				light_dir1=(0, 0, -1),
				light_color1=(0, 0, 0),
				ambient=(0.9, 0.9, 0.9)
			)
		elif preset == 3:  # Rim
			self.painting_system.update_lighting(
				light_dir0=hpr_to_dir(180, -30),  # Rim
				light_color0=(1.0, 1.0, 1.0),
				light_dir1=hpr_to_dir(0, -30),    # Fill
				light_color1=(0.2, 0.2, 0.25),
				ambient=(0.1, 0.1, 0.12)
			)

	def _draw_toolbar(self):
		"""Draw vertical toolbar on the left"""
		imgui.set_next_window_position(0, 20, imgui.FIRST_USE_EVER)
		imgui.set_next_window_size(50, 120, imgui.FIRST_USE_EVER)

		imgui.begin("Tools", flags=imgui.WINDOW_NO_TITLE_BAR | imgui.WINDOW_NO_RESIZE)

		button_size = 36

		# Brush tool
		is_brush = self.current_tool == 0
		if is_brush:
			imgui.push_style_color(imgui.COLOR_BUTTON, 0.3, 0.5, 0.8, 1.0)
		if imgui.button("B##brush", button_size, button_size):
			self.current_tool = 0
		if imgui.is_item_hovered():
			imgui.set_tooltip("Brush (B)")
		if is_brush:
			imgui.pop_style_color()

		# Fill tool
		is_fill = self.current_tool == 1
		if is_fill:
			imgui.push_style_color(imgui.COLOR_BUTTON, 0.3, 0.5, 0.8, 1.0)
		if imgui.button("G##fill", button_size, button_size):
			self.current_tool = 1
		if imgui.is_item_hovered():
			imgui.set_tooltip("Fill Layer (G)")
		if is_fill:
			imgui.pop_style_color()

		imgui.end()

	def _draw_brush_panel(self):
		"""Draw brush settings panel on the left"""
		imgui.set_next_window_position(55, 20, imgui.FIRST_USE_EVER)
		imgui.set_next_window_size(220, 500, imgui.FIRST_USE_EVER)

		imgui.begin("Brush")

		# Brush shape selection
		imgui.text("Shape")
		draw_list = imgui.get_window_draw_list()
		p = imgui.get_cursor_screen_pos()

		# Draw shape buttons
		shape_size = 40
		for i, shape_name in enumerate(self.brush_shapes):
			if i > 0:
				imgui.same_line()

			selected = (i == self.brush_shape_index)

			# Button background
			bx = p[0] + i * (shape_size + 5)
			by = p[1]

			if selected:
				draw_list.add_rect_filled(bx, by, bx + shape_size, by + shape_size,
																	imgui.get_color_u32_rgba(0.3, 0.5, 0.8, 1.0))
			else:
				draw_list.add_rect_filled(bx, by, bx + shape_size, by + shape_size,
																	imgui.get_color_u32_rgba(0.2, 0.2, 0.2, 1.0))

			# Draw shape preview
			cx = bx + shape_size / 2
			cy = by + shape_size / 2
			preview_r = shape_size * 0.35
			white = imgui.get_color_u32_rgba(0.9, 0.9, 0.9, 1.0)
			gray = imgui.get_color_u32_rgba(0.6, 0.6, 0.6, 1.0)

			if shape_name == 'Round':
				draw_list.add_circle_filled(cx, cy, preview_r, white)
			elif shape_name == 'Square':
				draw_list.add_rect_filled(cx - preview_r, cy - preview_r,
																	cx + preview_r, cy + preview_r, white)
			elif shape_name == 'Soft':
				# Soft brush - gradient circle (approximate with rings)
				for ring in range(5, 0, -1):
					alpha = ring / 5.0
					col = imgui.get_color_u32_rgba(0.9, 0.9, 0.9, alpha)
					draw_list.add_circle_filled(cx, cy, preview_r * ring / 5, col)
			elif shape_name == 'Flat':
				# Flat/ellipse brush
				draw_list.add_rect_filled(cx - preview_r, cy - preview_r * 0.3,
																	cx + preview_r, cy + preview_r * 0.3, white)

		# Invisible buttons for selection
		imgui.set_cursor_screen_pos((p[0], p[1]))
		for i in range(len(self.brush_shapes)):
			if imgui.invisible_button(f"##shape{i}", shape_size, shape_size):
				self.brush_shape_index = i
			if i < len(self.brush_shapes) - 1:
				imgui.same_line(spacing=5)

		imgui.dummy(0, 5)

		# Brush parameters
		imgui.separator()
		changed, self.brush_size = imgui.slider_int("Size", self.brush_size, 1, 200)
		changed, self.brush_opacity = imgui.slider_int("Opacity", self.brush_opacity, 1, 100)
		changed, self.brush_hardness = imgui.slider_int("Hardness", self.brush_hardness, 0, 100)
		changed, self.brush_spacing = imgui.slider_int("Spacing", self.brush_spacing, 1, 100)

		if self.brush_shapes[self.brush_shape_index] == 'Flat':
			changed, self.brush_angle = imgui.slider_int("Angle", self.brush_angle, 0, 180)

		# Brush preview (actual size representation)
		imgui.separator()
		imgui.text("Brush Preview")

		preview_size = 100
		p = imgui.get_cursor_screen_pos()
		preview_cx = p[0] + preview_size / 2
		preview_cy = p[1] + preview_size / 2

		# Background
		draw_list.add_rect_filled(p[0], p[1], p[0] + preview_size, p[1] + preview_size,
															imgui.get_color_u32_rgba(0.15, 0.15, 0.15, 1.0))

		# Draw brush at scaled size
		r, g, b = self.brush_color
		brush_col = imgui.get_color_u32_rgba(r, g, b, self.brush_opacity / 100.0)

		# Scale brush to fit in preview
		display_size = min(self.brush_size, preview_size - 10) / 2

		shape = self.brush_shapes[self.brush_shape_index]
		if shape == 'Round':
			draw_list.add_circle_filled(preview_cx, preview_cy, display_size, brush_col)
		elif shape == 'Square':
			draw_list.add_rect_filled(preview_cx - display_size, preview_cy - display_size,
																preview_cx + display_size, preview_cy + display_size, brush_col)
		elif shape == 'Soft':
			# Approximate soft brush with concentric circles
			steps = 10
			for i in range(steps, 0, -1):
				t = i / steps
				alpha = (self.brush_opacity / 100.0) * (1 - (1 - t) ** (self.brush_hardness / 30 + 1))
				col = imgui.get_color_u32_rgba(r, g, b, alpha)
				draw_list.add_circle_filled(preview_cx, preview_cy, display_size * t, col)
		elif shape == 'Flat':
			import math
			angle_rad = math.radians(self.brush_angle)
			# Draw rotated rectangle (approximate with polygon)
			hw = display_size
			hh = display_size * 0.3
			cos_a = math.cos(angle_rad)
			sin_a = math.sin(angle_rad)
			corners = [
				(preview_cx + cos_a * (-hw) - sin_a * (-hh), preview_cy + sin_a * (-hw) + cos_a * (-hh)),
				(preview_cx + cos_a * (hw) - sin_a * (-hh), preview_cy + sin_a * (hw) + cos_a * (-hh)),
				(preview_cx + cos_a * (hw) - sin_a * (hh), preview_cy + sin_a * (hw) + cos_a * (hh)),
				(preview_cx + cos_a * (-hw) - sin_a * (hh), preview_cy + sin_a * (-hw) + cos_a * (hh)),
			]
			draw_list.add_quad_filled(corners[0][0], corners[0][1], corners[1][0], corners[1][1],
																corners[2][0], corners[2][1], corners[3][0], corners[3][1], brush_col)

		imgui.dummy(preview_size, preview_size)

		imgui.separator()
		imgui.text("Color")

		# Custom HSV color picker - always visible
		r, g, b = self.brush_color
		changed, r, g, b = color_picker_hsv("##colorpicker", r, g, b, size=180)
		if changed:
			self.brush_color = [r, g, b]

		imgui.end()

	def _draw_texture_panel(self):
		"""Draw texture management panel"""
		win_width = builtins.base.win.getXSize()
		panel_width = 220

		imgui.set_next_window_position(win_width - panel_width, 20, imgui.FIRST_USE_EVER)
		imgui.set_next_window_size(panel_width, 200, imgui.FIRST_USE_EVER)

		imgui.begin("Textures")

		# Model info
		imgui.text_colored(f"Model: {self.model_name}", 0.7, 0.7, 0.7)
		imgui.separator()

		# Opacity slider at top (like Photoshop)
		if 0 <= self.selected_texture_index < len(self.textures):
			tex = self.textures[self.selected_texture_index]
			imgui.text("Opacity:")
			imgui.same_line()
			imgui.push_item_width(panel_width - 80)
			changed, new_opacity = imgui.slider_float(
				"##texopacity_top", tex['opacity'], 0.0, 1.0, f"{int(tex['opacity'] * 100)}%%"
			)
			imgui.pop_item_width()
			if changed:
				tex['opacity'] = new_opacity
				if self.painting_system:
					self.painting_system.set_texture_opacity(new_opacity)
			imgui.separator()

		# Add texture button (only if model loaded)
		if self.model is not None:
			if imgui.button("+ Add Texture"):
				self.show_new_texture_dialog = True
				self.new_texture_name = f"Texture_{len(self.textures) + 1}"
		else:
			imgui.text_colored("Load a model first", 0.5, 0.5, 0.5)

		imgui.separator()

		# Texture list with drag reorder and double-click rename
		drag_source = -1
		drag_target = -1

		for i, tex in enumerate(self.textures):
			# Texture type icon/color hint
			type_colors = {
				'diffuse': (0.9, 0.9, 0.9),
				'normal': (0.5, 0.5, 1.0),
				'roughness': (0.5, 0.8, 0.5),
				'metallic': (0.8, 0.8, 0.5),
				'ao': (0.6, 0.6, 0.6),
				'emission': (1.0, 0.8, 0.3),
				'height': (0.7, 0.5, 0.3),
				'opacity': (0.8, 0.4, 0.8),
			}
			col = type_colors.get(tex['type'], (0.7, 0.7, 0.7))

			# Selection
			selected = (i == self.selected_texture_index)

			# Check if renaming this texture
			is_renaming = (hasattr(self, '_renaming_texture') and self._renaming_texture == i)

			# Visibility checkbox
			changed, tex['visible'] = imgui.checkbox(f"##vis{i}", tex['visible'])
			imgui.same_line()

			if is_renaming:
				# Show text input for renaming
				imgui.push_item_width(panel_width - 60)
				enter_pressed, self._rename_buffer = imgui.input_text(
					f"##texrename{i}", self._rename_buffer, 64,
					imgui.INPUT_TEXT_ENTER_RETURNS_TRUE
				)
				imgui.pop_item_width()

				# Finish rename on Enter or click elsewhere
				if enter_pressed or (not imgui.is_item_active() and imgui.is_mouse_clicked(0)):
					tex['name'] = self._rename_buffer if self._rename_buffer else tex['name']
					self._renaming_texture = -1
			else:
				# Selectable with color hint
				imgui.push_style_color(imgui.COLOR_TEXT, col[0], col[1], col[2])
				clicked, _ = imgui.selectable(
					f"{tex['name']} ({tex['size']})",
					selected,
					width=panel_width - 60
				)
				imgui.pop_style_color()

				# Double-click to rename
				if imgui.is_item_hovered() and imgui.is_mouse_double_clicked(0):
					self._renaming_texture = i
					self._rename_buffer = tex['name']

				if clicked:
					self.selected_texture_index = i

				# Drag source
				if imgui.begin_drag_drop_source():
					imgui.set_drag_drop_payload('TEXTURE_DND', str(i).encode())
					imgui.text(tex['name'])
					imgui.end_drag_drop_source()

				# Drag target
				if imgui.begin_drag_drop_target():
					payload = imgui.accept_drag_drop_payload('TEXTURE_DND')
					if payload is not None:
						drag_source = int(payload.decode())
						drag_target = i
					imgui.end_drag_drop_target()

		# Handle reorder
		if drag_source >= 0 and drag_target >= 0 and drag_source != drag_target:
			tex = self.textures.pop(drag_source)
			self.textures.insert(drag_target, tex)
			# Update selection index
			if self.selected_texture_index == drag_source:
				self.selected_texture_index = drag_target
			elif drag_source < self.selected_texture_index <= drag_target:
				self.selected_texture_index -= 1
			elif drag_target <= self.selected_texture_index < drag_source:
				self.selected_texture_index += 1

		imgui.end()

	def _draw_layers_panel(self):
		"""Draw layers panel for selected texture"""
		win_width = builtins.base.win.getXSize()
		panel_width = 220

		imgui.set_next_window_position(win_width - panel_width, 225, imgui.FIRST_USE_EVER)
		imgui.set_next_window_size(panel_width, 300, imgui.FIRST_USE_EVER)

		imgui.begin("Layers")

		if self.selected_texture_index < 0 or self.selected_texture_index >= len(self.textures):
			imgui.text_colored("Select a texture", 0.5, 0.5, 0.5)
			imgui.end()
			return

		tex = self.textures[self.selected_texture_index]
		imgui.text(f"Layers for: {tex['name']}")
		imgui.separator()

		# Get layers from painting system if available
		if self.painting_system and self.painting_system.layers:
			layers = self.painting_system.layers
			selected_layer_idx = self.painting_system.active_layer_index
		else:
			layers = tex.get('layers', [])
			selected_layer_idx = tex.get('selected_layer', 0)

		# Opacity slider at top (like Photoshop)
		if 0 <= selected_layer_idx < len(layers):
			layer = layers[selected_layer_idx]
			imgui.text("Opacity:")
			imgui.same_line()
			imgui.push_item_width(panel_width - 80)
			changed, new_opacity = imgui.slider_float(
				"##layeropacity_top", layer['opacity'], 0.0, 1.0, f"{int(layer['opacity'] * 100)}%%"
			)
			imgui.pop_item_width()
			if changed:
				layer['opacity'] = new_opacity
				if self.painting_system:
					self.painting_system.set_layer_opacity(selected_layer_idx, new_opacity)
			imgui.separator()

		# Add/Remove layer buttons
		if imgui.button("+##addlayer"):
			if self.painting_system:
				self.painting_system.add_layer(f"Layer {len(layers) + 1}")
		imgui.same_line()
		if imgui.button("-##removelayer"):
			if self.painting_system and len(layers) > 1:
				self.painting_system.remove_layer(selected_layer_idx)

		imgui.separator()

		# Layer list with drag reorder and double-click rename
		drag_source = -1
		drag_target = -1

		for i, layer in enumerate(layers):
			selected = (i == selected_layer_idx)

			# Check if renaming this layer
			is_renaming = (hasattr(self, '_renaming_layer') and self._renaming_layer == i)

			# Visibility
			changed, new_visible = imgui.checkbox(f"##layervis{i}", layer['visible'])
			if changed:
				layer['visible'] = new_visible
				if self.painting_system:
					self.painting_system.set_layer_visible(i, new_visible)
			imgui.same_line()

			if is_renaming:
				# Show text input for renaming
				imgui.push_item_width(panel_width - 60)
				enter_pressed, self._layer_rename_buffer = imgui.input_text(
					f"##layerrename{i}", self._layer_rename_buffer, 64,
					imgui.INPUT_TEXT_ENTER_RETURNS_TRUE
				)
				imgui.pop_item_width()

				# Finish rename on Enter or click elsewhere
				if enter_pressed or (not imgui.is_item_active() and imgui.is_mouse_clicked(0)):
					layer['name'] = self._layer_rename_buffer if self._layer_rename_buffer else layer['name']
					self._renaming_layer = -1
			else:
				# Selectable
				clicked, _ = imgui.selectable(layer['name'], selected, width=panel_width - 60)

				# Double-click to rename
				if imgui.is_item_hovered() and imgui.is_mouse_double_clicked(0):
					self._renaming_layer = i
					self._layer_rename_buffer = layer['name']

				if clicked:
					if self.painting_system:
						self.painting_system.set_active_layer(i)
					tex['selected_layer'] = i

				# Drag source
				if imgui.begin_drag_drop_source():
					imgui.set_drag_drop_payload('LAYER_DND', str(i).encode())
					imgui.text(layer['name'])
					imgui.end_drag_drop_source()

				# Drag target
				if imgui.begin_drag_drop_target():
					payload = imgui.accept_drag_drop_payload('LAYER_DND')
					if payload is not None:
						drag_source = int(payload.decode())
						drag_target = i
					imgui.end_drag_drop_target()

		# Handle reorder
		if drag_source >= 0 and drag_target >= 0 and drag_source != drag_target:
			if self.painting_system:
				self.painting_system.reorder_layer(drag_source, drag_target)
			# Update UI selection
			if tex['selected_layer'] == drag_source:
				tex['selected_layer'] = drag_target
			elif drag_source < tex['selected_layer'] <= drag_target:
				tex['selected_layer'] -= 1
			elif drag_target <= tex['selected_layer'] < drag_source:
				tex['selected_layer'] += 1

		imgui.end()

	def _draw_history_panel(self):
		"""Draw history panel for undo/redo"""
		win_width = builtins.base.win.getXSize()
		panel_width = 220

		imgui.set_next_window_position(win_width - panel_width, 545, imgui.FIRST_USE_EVER)
		imgui.set_next_window_size(panel_width, 200, imgui.FIRST_USE_EVER)

		imgui.begin("History")

		if not self.painting_system or not self.painting_system.history:
			imgui.text_colored("No history yet", 0.5, 0.5, 0.5)
			imgui.end()
			return

		# Undo/Redo buttons
		can_undo = self.painting_system.history_index > 0
		can_redo = self.painting_system.history_index < len(self.painting_system.history) - 1

		if not can_undo:
			imgui.push_style_var(imgui.STYLE_ALPHA, 0.5)
		if imgui.button("Undo"):
			if can_undo:
				self.painting_system.undo()
				self._sync_ui_from_painting_system()
		if not can_undo:
			imgui.pop_style_var()

		imgui.same_line()

		if not can_redo:
			imgui.push_style_var(imgui.STYLE_ALPHA, 0.5)
		if imgui.button("Redo"):
			if can_redo:
				self.painting_system.redo()
				self._sync_ui_from_painting_system()
		if not can_redo:
			imgui.pop_style_var()

		imgui.same_line()
		imgui.text(f"({self.painting_system.history_index + 1}/{len(self.painting_system.history)})")

		imgui.separator()

		# History list
		history = self.painting_system.get_history_list()
		current_idx = self.painting_system.history_index

		# Show in reverse order (newest at top)
		for i in range(len(history) - 1, -1, -1):
			idx, name = history[i]
			is_current = (idx == current_idx)
			is_future = (idx > current_idx)

			# Dim future states (would be lost on undo then paint)
			if is_future:
				imgui.push_style_var(imgui.STYLE_ALPHA, 0.4)

			# Highlight current state
			if is_current:
				imgui.push_style_color(imgui.COLOR_TEXT, 0.3, 1.0, 0.3, 1.0)

			clicked, _ = imgui.selectable(f"{idx + 1}. {name}", is_current)

			if is_current:
				imgui.pop_style_color()
			if is_future:
				imgui.pop_style_var()

			if clicked and not is_current:
				self.painting_system.goto_history(idx)
				self._sync_ui_from_painting_system()

		imgui.end()

	def _draw_new_texture_dialog(self):
		"""Draw dialog for creating new texture"""
		imgui.set_next_window_size(350, 200)

		# Center the dialog
		win_width = builtins.base.win.getXSize()
		win_height = builtins.base.win.getYSize()
		imgui.set_next_window_position(win_width / 2 - 175, win_height / 2 - 100)

		imgui.begin("New Texture", flags=imgui.WINDOW_NO_RESIZE | imgui.WINDOW_NO_COLLAPSE)

		# Texture name
		changed, self.new_texture_name = imgui.input_text("Name", self.new_texture_name, 64)

		# Texture type dropdown
		type_names = [t[0] for t in TEXTURE_TYPES]
		clicked, self.new_texture_type_index = imgui.combo("Type", self.new_texture_type_index, type_names)

		# Show description
		imgui.text_colored(TEXTURE_TYPES[self.new_texture_type_index][2], 0.6, 0.6, 0.6)

		# Size dropdown
		size_strs = [f"{s}x{s}" for s in TEXTURE_SIZES]
		clicked, self.new_texture_size_index = imgui.combo("Size", self.new_texture_size_index, size_strs)

		imgui.separator()

		# Buttons
		if imgui.button("Create", width=100):
			self._create_texture(
				name=self.new_texture_name,
				tex_type=TEXTURE_TYPES[self.new_texture_type_index][1],
				size=TEXTURE_SIZES[self.new_texture_size_index]
			)
			self.show_new_texture_dialog = False

		imgui.same_line()

		if imgui.button("Cancel", width=100):
			self.show_new_texture_dialog = False

		imgui.end()

	def _draw_open_model_dialog(self):
		"""Simple file browser for opening models"""
		imgui.set_next_window_size(500, 400)

		win_width = builtins.base.win.getXSize()
		win_height = builtins.base.win.getYSize()
		imgui.set_next_window_position(win_width / 2 - 250, win_height / 2 - 200)

		imgui.begin("Open Model", flags=imgui.WINDOW_NO_RESIZE)

		# Build filtered list (dirs + model files)
		filtered_items = []
		for item in self.file_browser_files:
			is_dir = item.endswith('/')
			if is_dir:
				filtered_items.append(item)
			else:
				ext = os.path.splitext(item)[1].lower()
				if ext in ['.gltf', '.glb', '.obj', '.egg', '.bam']:
					filtered_items.append(item)

		# Handle keyboard navigation
		if imgui.is_window_focused(imgui.FOCUS_ROOT_AND_CHILD_WINDOWS):
			if imgui.is_key_pressed(imgui.KEY_DOWN_ARROW):
				self.file_browser_index = min(self.file_browser_index + 1, len(filtered_items) - 1)
				if filtered_items:
					item = filtered_items[self.file_browser_index]
					self.file_browser_selected = item.rstrip('/')
			elif imgui.is_key_pressed(imgui.KEY_UP_ARROW):
				self.file_browser_index = max(self.file_browser_index - 1, 0)
				if filtered_items:
					item = filtered_items[self.file_browser_index]
					self.file_browser_selected = item.rstrip('/')
			elif imgui.is_key_pressed(imgui.KEY_ENTER):
				if filtered_items and 0 <= self.file_browser_index < len(filtered_items):
					item = filtered_items[self.file_browser_index]
					if item.endswith('/'):
						# Enter directory
						self.file_browser_path = os.path.join(self.file_browser_path, item.rstrip('/'))
						self._refresh_file_browser()
						self.file_browser_index = 0
					else:
						# Open file
						full_path = os.path.join(self.file_browser_path, item)
						self._load_model(full_path)
						self.show_open_dialog = False
			elif imgui.is_key_pressed(imgui.KEY_BACKSPACE):
				# Go up directory
				parent = os.path.dirname(self.file_browser_path)
				if parent and parent != self.file_browser_path:
					self.file_browser_path = parent
					self._refresh_file_browser()
					self.file_browser_index = 0
			elif imgui.is_key_pressed(imgui.KEY_ESCAPE):
				self.show_open_dialog = False

		# Drive selection (Windows)
		if os.name == 'nt':
			import string
			drives = [f"{d}:\\" for d in string.ascii_uppercase if os.path.exists(f"{d}:\\")]

			# Find current drive index
			current_drive = os.path.splitdrive(self.file_browser_path)[0] + "\\"
			drive_index = drives.index(current_drive) if current_drive in drives else 0

			imgui.set_next_item_width(60)
			changed, new_index = imgui.combo("##drive", drive_index, drives)
			if changed:
				self.file_browser_path = drives[new_index]
				self._refresh_file_browser()
				self.file_browser_index = 0
			imgui.same_line()

		# Current path
		imgui.text(f"Path: {self.file_browser_path}")

		# Refresh file list
		if imgui.button("Refresh"):
			self._refresh_file_browser()
			self.file_browser_index = 0

		imgui.same_line()
		if imgui.button("Up") or imgui.is_key_pressed(imgui.KEY_BACKSPACE):
			parent = os.path.dirname(self.file_browser_path)
			# On Windows, don't go above drive root
			if parent and parent != self.file_browser_path:
				self.file_browser_path = parent
				self._refresh_file_browser()
				self.file_browser_index = 0

		imgui.separator()

		# File list
		imgui.begin_child("files", 0, -50)

		for i, item in enumerate(filtered_items):
			is_dir = item.endswith('/')
			name = item.rstrip('/')

			is_selected = (i == self.file_browser_index)

			if is_dir:
				clicked, _ = imgui.selectable(f"[DIR] {name}", is_selected)
				if clicked:
					self.file_browser_index = i
					self.file_browser_path = os.path.join(self.file_browser_path, name)
					self._refresh_file_browser()
					self.file_browser_index = 0
			else:
				clicked, _ = imgui.selectable(name, is_selected)
				if clicked:
					self.file_browser_index = i
					self.file_browser_selected = name

			# Scroll to selected item
			if is_selected and imgui.is_key_pressed(imgui.KEY_DOWN_ARROW) or imgui.is_key_pressed(imgui.KEY_UP_ARROW):
				imgui.set_scroll_here_y()

		imgui.end_child()

		imgui.separator()

		# Open/Cancel buttons
		if imgui.button("Open", width=100) and self.file_browser_selected:
			full_path = os.path.join(self.file_browser_path, self.file_browser_selected)
			self._load_model(full_path)
			self.show_open_dialog = False

		imgui.same_line()

		if imgui.button("Cancel", width=100):
			self.show_open_dialog = False

		imgui.end()

	def _refresh_file_browser(self):
		"""Refresh file browser listing"""
		try:
			items = os.listdir(self.file_browser_path)
			dirs = sorted([f + '/' for f in items if os.path.isdir(os.path.join(self.file_browser_path, f))])
			files = sorted([f for f in items if os.path.isfile(os.path.join(self.file_browser_path, f))])
			self.file_browser_files = dirs + files
			self._save_last_directory()
		except Exception as e:
			self.file_browser_files = []

	def _load_last_directory(self):
		"""Load last browsed directory from config"""
		try:
			if os.path.exists(self._config_file):
				with open(self._config_file, 'r') as f:
					path = f.read().strip()
					if os.path.isdir(path):
						return path
		except:
			pass
		return os.getcwd()

	def _save_last_directory(self):
		"""Save current directory to config"""
		try:
			with open(self._config_file, 'w') as f:
				f.write(self.file_browser_path)
		except:
			pass

	def _create_test_cube(self):
		"""Create a native Panda3D cube with proper UVs for testing"""
		from panda3d.core import GeomVertexFormat, GeomVertexData, Geom, GeomTriangles
		from panda3d.core import GeomVertexWriter, GeomNode

		# Create vertex format with position, normal, and UV
		format = GeomVertexFormat.getV3n3t2()
		vdata = GeomVertexData('cube', format, Geom.UHStatic)

		vertex = GeomVertexWriter(vdata, 'vertex')
		normal = GeomVertexWriter(vdata, 'normal')
		texcoord = GeomVertexWriter(vdata, 'texcoord')

		# Define cube vertices for each face (with proper UVs)
		faces = [
			# Front face (Z+)
			((-1, -1, 1), (1, -1, 1), (1, 1, 1), (-1, 1, 1), (0, 0, 1)),
			# Back face (Z-)
			((1, -1, -1), (-1, -1, -1), (-1, 1, -1), (1, 1, -1), (0, 0, -1)),
			# Top face (Y+)
			((-1, 1, -1), (-1, 1, 1), (1, 1, 1), (1, 1, -1), (0, 1, 0)),
			# Bottom face (Y-)
			((-1, -1, -1), (1, -1, -1), (1, -1, 1), (-1, -1, 1), (0, -1, 0)),
			# Right face (X+)
			((1, -1, -1), (1, 1, -1), (1, 1, 1), (1, -1, 1), (1, 0, 0)),
			# Left face (X-)
			((-1, -1, 1), (-1, 1, 1), (-1, 1, -1), (-1, -1, -1), (-1, 0, 0)),
		]

		# UV offsets for each face (3 columns x 2 rows)
		# Use SQUARE tiles for consistent brush size
		face_uv_offsets = [
			(0.0, 0.333),  # Face 0: row 1
			(0.333, 0.333),  # Face 1: row 1
			(0.666, 0.333),  # Face 2: row 1
			(0.0, 0.0),  # Face 3: row 0
			(0.333, 0.0),  # Face 4: row 0
			(0.666, 0.0),  # Face 5: row 0
		]
		uv_scale = (0.333, 0.333)  # Square tiles

		for face_idx, (v0, v1, v2, v3, n) in enumerate(faces):
			uv_off = face_uv_offsets[face_idx]
			# UVs for this face corners
			uvs = [
				(uv_off[0], uv_off[1]),
				(uv_off[0] + uv_scale[0], uv_off[1]),
				(uv_off[0] + uv_scale[0], uv_off[1] + uv_scale[1]),
				(uv_off[0], uv_off[1] + uv_scale[1])
			]
			for v, uv in zip([v0, v1, v2, v3], uvs):
				vertex.addData3f(v[0], v[1], v[2])
				normal.addData3f(n[0], n[1], n[2])
				texcoord.addData2f(uv[0], uv[1])

		# Create triangles
		tris = GeomTriangles(Geom.UHStatic)
		for face_idx in range(6):
			base = face_idx * 4
			tris.addVertices(base, base + 1, base + 2)
			tris.addVertices(base, base + 2, base + 3)
		tris.closePrimitive()

		# Create geom
		geom = Geom(vdata)
		geom.addPrimitive(tris)

		# Create node
		node = GeomNode('test_cube')
		node.addGeom(geom)

		# Create NodePath
		self.model = builtins.base.render.attachNewNode(node)
		self.model.setPos(0, 0, 1)

		# Store triangle data for painting system
		# Give each face a UNIQUE UV region so paint doesn't appear on all faces
		# Layout: 3x2 grid, each face gets 1/3 width and 1/2 height
		self._native_cube_triangles = []
		from panda3d.core import LPoint3f, LPoint2f
		model_pos = self.model.getPos()
		ox, oy, oz = model_pos.x, model_pos.y, model_pos.z

		# UV offsets for each face (3 columns x 2 rows) - MUST match visual geometry
		face_uv_offsets = [
			(0.0, 0.333),  # Face 0: row 1
			(0.333, 0.333),  # Face 1: row 1
			(0.666, 0.333),  # Face 2: row 1
			(0.0, 0.0),  # Face 3: row 0
			(0.333, 0.0),  # Face 4: row 0
			(0.666, 0.0),  # Face 5: row 0
		]
		uv_scale = (0.333, 0.333)  # Square tiles

		for face_idx, (v0, v1, v2, v3, n) in enumerate(faces):
			uv_off = face_uv_offsets[face_idx]
			# UVs for this face, scaled and offset
			uv0 = (uv_off[0], uv_off[1])
			uv1 = (uv_off[0] + uv_scale[0], uv_off[1])
			uv2 = (uv_off[0] + uv_scale[0], uv_off[1] + uv_scale[1])
			uv3 = (uv_off[0], uv_off[1] + uv_scale[1])

			# Two triangles per face - offset to world space
			self._native_cube_triangles.append((
				LPoint3f(v0[0] + ox, v0[1] + oy, v0[2] + oz),
				LPoint3f(v1[0] + ox, v1[1] + oy, v1[2] + oz),
				LPoint3f(v2[0] + ox, v2[1] + oy, v2[2] + oz),
				LPoint2f(uv0[0], uv0[1]),
				LPoint2f(uv1[0], uv1[1]),
				LPoint2f(uv2[0], uv2[1])
			))
			self._native_cube_triangles.append((
				LPoint3f(v0[0] + ox, v0[1] + oy, v0[2] + oz),
				LPoint3f(v2[0] + ox, v2[1] + oy, v2[2] + oz),
				LPoint3f(v3[0] + ox, v3[1] + oy, v3[2] + oz),
				LPoint2f(uv0[0], uv0[1]),
				LPoint2f(uv2[0], uv2[1]),
				LPoint2f(uv3[0], uv3[1])
			))

		# Setup collision directly from our triangle data (more reliable than extracting from geom)
		if HAS_BULLET and self.bullet_world:
			from panda3d.bullet import BulletTriangleMesh, BulletTriangleMeshShape, BulletRigidBodyNode

			mesh = BulletTriangleMesh()
			for v0, v1, v2, uv0, uv1, uv2 in self._native_cube_triangles:
				mesh.addTriangle(v0, v1, v2)

			print(f"Created collision mesh with {mesh.getNumTriangles()} triangles")

			shape = BulletTriangleMeshShape(mesh, dynamic=False)
			body_node = BulletRigidBodyNode('model_collision')
			body_node.addShape(shape)
			body_node.setMass(0)

			body_np = builtins.base.render.attachNewNode(body_node)
			# Don't offset - triangles are already in world space

			self.bullet_world.attachRigidBody(body_node)
			self.bullet_body = body_node
			self._raycast_debug = False  # Reset debug flag
			self._hit_debug_count = 0  # Reset hit debug
			print(f"Bullet body created: {self.bullet_body}")

		# Setup painting - pass the triangles directly
		if self.painting_system:
			self.painting_system.setup_for_model(self.model, texture_size=1024)
			# Override with our pre-computed triangles
			self.painting_system.triangles = self._native_cube_triangles
			# Recompute average UV scale with actual triangles
			self.painting_system._compute_avg_uv_scale()
			print(f"Set {len(self._native_cube_triangles)} triangles for painting")
			# Update shader lighting to match current preset
			self._update_shader_lighting(self.lighting_preset)

		# Apply a basic white color to model (texture will be applied when user creates one)
		self.model.setColor(0.8, 0.8, 0.8, 1)

		# Frame camera
		if self.orbit_camera:
			self.orbit_camera.set_target(0, 0, 1)
			self.orbit_camera.distance = 5
			self.orbit_camera._update_position()

		self.model_name = "test_cube"
		print("Created native Panda3D test cube with UVs")

	def _load_model(self, path):
		"""Load a 3D model"""
		try:
			from panda3d.core import Filename

			# Register glTF loader if needed
			ext = os.path.splitext(path)[1].lower()
			if ext in ['.gltf', '.glb']:
				try:
					import gltf
					# For older versions, patch the loader
					# For newer versions (1.3+), just importing gltf is enough
					if hasattr(gltf, 'patch_loader') and not hasattr(builtins.base.loader, '_gltf_registered'):
						gltf.patch_loader(builtins.base.loader)
						builtins.base.loader._gltf_registered = True
				except ImportError:
					print("panda3d-gltf not installed. Run: pip install panda3d-gltf")
					return

			# Remove old model
			if self.model:
				self.model.removeNode()
				self.model = None

			# Convert Windows path to Panda3D path
			panda_path = Filename.fromOsSpecific(path)

			print(f"Loading model: {path}")
			print(f"Panda path: {panda_path}")

			model = builtins.base.loader.loadModel(panda_path)

			if model:
				model.reparentTo(builtins.base.render)

				# CRITICAL: Disable glTF shaders to allow texture display
				model.setShaderOff(100)
				for child in model.findAllMatches('**'):
					child.setShaderOff(100)

				# Setup Bullet collision mesh from actual geometry
				if HAS_BULLET and self.bullet_world:
					self._setup_bullet_collision(model)

				# Setup painting system for this model
				if self.painting_system:
					try:
						self.painting_system.setup_for_model(model, texture_size=1024)
						self._update_shader_lighting(self.lighting_preset)
					except Exception as e:
						print(f"Painting system setup error: {e}")

				# Get model bounds for framing
				bounds = model.getTightBounds()
				if bounds:
					min_pt, max_pt = bounds
					center = (min_pt + max_pt) / 2
					size = (max_pt - min_pt).length()

					print(f"Model loaded: center={center}, size={size}")

					# Store model reference
					self.model = model
					self.model_path = path
					self.model_name = os.path.basename(path)

					# Frame camera on model
					if self.orbit_camera:
						self.orbit_camera.set_target(center.x, center.y, center.z)
						self.orbit_camera.distance = max(size * 2, 1.0)
						self.orbit_camera._update_position()
				else:
					print("Model has no bounds")
					self.model = model
					self.model_path = path
					self.model_name = os.path.basename(path)
					self._reset_camera()
			else:
				print(f"Failed to load model: {path}")
				self.model_name = "Failed to load"

			# Clear textures for new model
			self.textures = []
			self.selected_texture_index = -1

			print(f"Loaded model: {path}")

		except Exception as e:
			print(f"Error loading model: {e}")
			self.model = None
			self.model_name = "Error loading model"

	def _create_texture(self, name, tex_type, size):
		"""Create a new texture with a default layer"""
		texture = {
			'name': name,
			'type': tex_type,
			'size': size,
			'opacity': 1.0,
			'visible': True,
			'selected_layer': 0,
			'layers': [
				{
					'name': 'Base',
					'opacity': 1.0,
					'visible': True,
					'data': None  # Will hold actual texture data
				}
			]
		}
		self.textures.append(texture)
		self.selected_texture_index = len(self.textures) - 1
		print(f"Created texture: {name} ({tex_type}, {size}x{size})")

		# Initialize painting system with this texture
		if self.painting_system and self.model:
			self.painting_system.texture_size = size
			self.painting_system.create_texture_for_painting()

	def _add_layer_to_texture(self, tex_index):
		"""Add a layer to the specified texture"""
		if 0 <= tex_index < len(self.textures):
			tex = self.textures[tex_index]
			layer_num = len(tex['layers']) + 1
			tex['layers'].insert(0, {
				'name': f'Layer {layer_num}',
				'opacity': 1.0,
				'visible': True,
				'data': None
			})
			tex['selected_layer'] = 0
			# Sync with painting system
			if self.painting_system:
				self.painting_system.add_layer(f'Layer {layer_num}')

	def _remove_layer_from_texture(self, tex_index):
		"""Remove selected layer from texture"""
		if 0 <= tex_index < len(self.textures):
			tex = self.textures[tex_index]
			if len(tex['layers']) > 1:
				sel = tex.get('selected_layer', 0)
				tex['layers'].pop(sel)
				if sel >= len(tex['layers']):
					tex['selected_layer'] = len(tex['layers']) - 1
				# Sync with painting system
				if self.painting_system:
					self.painting_system.remove_layer(sel)

	def _reset_camera(self):
		"""Reset camera to default view"""
		if self.orbit_camera:
			self.orbit_camera.reset()

	# Menu callbacks
	def _on_new(self):
		"""New project - clear everything"""
		if self.model:
			self.model.removeNode()
		self.model = None
		self.model_path = None
		self.model_name = "No model loaded"
		self.textures = []
		self.selected_texture_index = -1

	def _on_open(self):
		"""Open file browser"""
		self.show_open_dialog = True
		self._refresh_file_browser()

	def _on_save(self):
		print("Save Textures - TODO")

	def _on_export(self):
		print("Export All - TODO")

	def _on_exit(self):
		self.engine.running = False

	def on_exit(self):
		super().on_exit()
		if self.model:
			self.model.removeNode()
		if self.grid:
			self.grid.removeNode()
		if self.origin_gizmo:
			self.origin_gizmo.removeNode()
		if self.orbit_camera:
			self.orbit_camera.destroy()
		if self.imgui:
			self.imgui.destroy()