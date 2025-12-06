# Texture Painter Project

## Overview
A 3D texture painting application built on top of a custom Panda3D game engine, similar to tools like Substance Painter or Blender's texture paint mode.

## Tech Stack
- **Engine**: Custom Panda3D-based game engine
- **UI**: ImGui (via panda3d-imgui)
- **Physics**: Bullet (for brush raycasting)
- **Formats**: glTF, OBJ, EGG, BAM

## Current Status: UI Polish Phase

### Recently Completed
- ✅ UV coordinate mapping fixed (V-flip issue for Blender exports)
- ✅ Painting works correctly on all cube faces
- ✅ World-space brush cursor with Bullet raycasting
- ✅ Multi-layer support with GPU compositing shader
- ✅ Undo/redo history system
- ✅ File browser with keyboard navigation (↑↓ Enter Backspace Esc)
- ✅ Remembers last opened directory

### In Progress
- 🔧 Panel visibility toggles (Panels menu)
- 🔧 Lighting presets (Studio, Outdoor, Flat, Rim)
- 🔧 Collapsing header behavior cleanup

### Core Architecture
```
texture_painter/
├── painting_system.py    # Paint logic, UV mapping, layers, history
├── texture_painter_scene.py  # Main scene, ImGui UI, file browser
└── orbit_camera.py       # Camera controls
```

### Key Systems
1. **PaintingSystem** - Handles UV lookup, brush stamping, layer compositing
2. **OrbitCamera** - Middle-mouse orbit, scroll zoom
3. **ImGui Panels** - Tools, Brush, Textures, Layers, History, Lighting

### Known Issues
- Panel close buttons need removal (close via menu only)
- Some UI sections need DEFAULT_OPEN flag

### Next Up
- Export textures to PNG
- PBR texture channel support
- Brush presets
- Symmetry painting