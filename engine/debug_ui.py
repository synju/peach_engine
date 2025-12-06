from panda3d.core import TextNode
from .ui_container import UIContainer
from .ui_element import UIText, UIBox

class DebugUI:
    """Debug UI with position and angle display"""

    def __init__(self):
        self.container = UIContainer()

        # Position display - top left (grouped)
        self.pos_group = self.container.add(UIBox(
            anchor='top-left', offset_x=135, offset_y=36, width=242, height=50,
            fill_color=(0, 0, 0, 1)
        ))

        self.pos_label = self.container.add(UIText(
            'Position', anchor='top-left', offset_x=19, offset_y=26, size=14
        ))
        self.pos_label._text_node.setAlign(TextNode.ALeft)

        self.pos_x_box = self.container.add(UIBox(
            anchor='top-left', offset_x=55, offset_y=44, width=70, height=22
        ))
        self.pos_y_box = self.container.add(UIBox(
            anchor='top-left', offset_x=135, offset_y=44, width=70, height=22
        ))
        self.pos_z_box = self.container.add(UIBox(
            anchor='top-left', offset_x=215, offset_y=44, width=70, height=22
        ))

        self.pos_x = self.container.add(UIText(
            'x:0.00', anchor='top-left', offset_x=55, offset_y=46, size=14
        ))
        self.pos_y = self.container.add(UIText(
            'y:0.00', anchor='top-left', offset_x=135, offset_y=46, size=14
        ))
        self.pos_z = self.container.add(UIText(
            'z:0.00', anchor='top-left', offset_x=215, offset_y=46, size=14
        ))

        # Rotation display - top right (grouped)
        self.ang_group = self.container.add(UIBox(
            anchor='top-right', offset_x=-135, offset_y=36, width=242, height=50,
            fill_color=(0, 0, 0, 1)
        ))

        self.ang_label = self.container.add(UIText(
            'Rotation', anchor='top-right', offset_x=-241, offset_y=26, size=14
        ))
        self.ang_label._text_node.setAlign(TextNode.ALeft)

        self.ang_x_box = self.container.add(UIBox(
            anchor='top-right', offset_x=-215, offset_y=44, width=70, height=22
        ))
        self.ang_y_box = self.container.add(UIBox(
            anchor='top-right', offset_x=-135, offset_y=44, width=70, height=22
        ))
        self.ang_z_box = self.container.add(UIBox(
            anchor='top-right', offset_x=-55, offset_y=44, width=70, height=22
        ))

        self.ang_x = self.container.add(UIText(
            'x:0', anchor='top-right', offset_x=-215, offset_y=46, size=14
        ))
        self.ang_y = self.container.add(UIText(
            'y:0', anchor='top-right', offset_x=-135, offset_y=46, size=14
        ))
        self.ang_z = self.container.add(UIText(
            'z:0', anchor='top-right', offset_x=-55, offset_y=46, size=14
        ))

        # Instructions - bottom center
        self.instructions_box = self.container.add(UIBox(
            anchor='bottom-center', offset_x=0, offset_y=-25, width=540, height=24,
            fill_color=(0, 0, 0, 1)
        ))
        self.instructions = self.container.add(UIText(
            'Right-click hold: look/move | WASD: move | Space: up | Ctrl: down | Shift: fast',
            anchor='bottom-center', offset_x=0, offset_y=-25, size=12
        ))

    def set_visible(self, visible):
        self.container.set_visible(visible)

    def update_values(self, position, rotation):
        """Update displayed values"""
        self.pos_x.text = f'x:{position[0]:.2f}'
        self.pos_y.text = f'y:{position[1]:.2f}'
        self.pos_z.text = f'z:{position[2]:.2f}'
        self.ang_x.text = f'x:{int(rotation[0])}'
        self.ang_y.text = f'y:{int(rotation[1])}'
        self.ang_z.text = f'z:{int(rotation[2])}'

    def update(self):
        self.container.update()