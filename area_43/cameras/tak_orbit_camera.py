import math
from direct.showbase.ShowBase import ShowBase
from engine.camera import Camera

base: ShowBase


class TakOrbitCamera(Camera):
    """Orbital camera for Tak that orbits around a fixed center point"""

    def __init__(
        self, engine, center=(4, 4, 0), distance=15.0, near_clip=0.1, far_clip=10000
    ):
        super().__init__(engine, (0, 0, 0), (0, 0, 0), near_clip, far_clip)

        self.center = list(center)
        self.distance = distance

        # Zoom limits
        self.min_distance = 5.0
        self.max_distance = 30.0
        self.zoom_speed = 1.0

        # Orbit angles
        self.heading = 45  # Start at 45 degrees
        self.pitch = 30  # Start looking down at 30 degrees

        # Mouse sensitivity
        self.sensitivity = 100.0

        # Pitch limits
        self.min_pitch = 5
        self.max_pitch = 85

        # Orbit dragging
        self.is_dragging = False

        # Register scroll events
        base.accept("wheel_up", self._zoom_in)
        base.accept("wheel_down", self._zoom_out)

    def _zoom_in(self):
        self.distance = max(self.min_distance, self.distance - self.zoom_speed)

    def _zoom_out(self):
        self.distance = min(self.max_distance, self.distance + self.zoom_speed)

    def handle_input(self, input_handler):
        """Handle mouse drag for orbiting"""
        # Mouse drag for orbit (right click)
        if input_handler.is_mouse_pressed(3):  # Right mouse
            if not self.is_dragging:
                self.is_dragging = True

            dx, dy = input_handler.mouse_delta
            self.heading -= dx * self.sensitivity
            self.pitch -= dy * self.sensitivity
            self.pitch = max(self.min_pitch, min(self.max_pitch, self.pitch))
        else:
            self.is_dragging = False

    def update(self, dt):
        """Update camera position to orbit around center"""
        # Calculate desired camera position based on orbit angles
        heading_rad = math.radians(self.heading)
        pitch_rad = math.radians(self.pitch)

        # Offset from center
        offset_x = math.sin(heading_rad) * math.cos(pitch_rad) * self.distance
        offset_y = -math.cos(heading_rad) * math.cos(pitch_rad) * self.distance
        offset_z = math.sin(pitch_rad) * self.distance

        self.position = [
            self.center[0] + offset_x,
            self.center[1] + offset_y,
            self.center[2] + offset_z,
        ]

        # Look at center
        self.rotation = [-self.pitch, self.heading, 0]

        self._apply_transform()

    def set_center(self, x, y, z):
        """Set the orbit center"""
        self.center = [x, y, z]

    def destroy(self):
        """Clean up"""
        self.deactivate()
