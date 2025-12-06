"""
Painting System - Handles texture painting on 3D models
"""
import math
from panda3d.core import (
    PNMImage, Texture, TextureStage, Shader, ShaderAttrib,
    GeomVertexReader, GeomNode, Point3, Vec3, Vec2, Vec4,
    PTAFloat, PTALVecBase4f, LPoint3f
)


class HistoryState:
    """Stores a snapshot of all layers for undo/redo"""
    def __init__(self, name, layers, active_index):
        self.name = name
        self.active_index = active_index
        # Deep copy all layer images
        self.layer_data = []
        for layer in layers:
            img_copy = PNMImage(layer['image'].getXSize(), layer['image'].getYSize(), 4)
            img_copy.copyFrom(layer['image'])
            self.layer_data.append({
                'name': layer['name'],
                'image': img_copy,
                'opacity': layer['opacity'],
                'visible': layer['visible']
            })


class PaintingSystem:
    """Manages texture painting on a 3D model with GPU-accelerated layer compositing"""

    MAX_LAYERS = 8  # Max layers supported by shader
    MAX_HISTORY = 30  # Max undo steps

    def __init__(self):
        self.model = None
        self.texture_size = 1024

        # History for undo/redo
        self.history = []  # List of HistoryState
        self.history_index = -1  # Current position in history
        self.stroke_in_progress = False  # Track if we're mid-stroke

        # Mesh data for UV lookup
        self.triangles = []  # List of (v0, v1, v2, uv0, uv1, uv2) tuples

        # Layer system - each layer has its own texture
        self.layers = []  # List of {'name': str, 'image': PNMImage, 'texture': Texture, 'opacity': float, 'visible': bool}

        # Shader for GPU compositing
        self.layer_shader = None
        self.layer_opacities = None  # PTAFloat for shader
        self.layer_visible = None    # PTAFloat for shader
        self._geom_nodes = []  # GeomNodes to apply shader to

        # Stored lighting state (so it persists across _apply_shader calls)
        self._lighting_state = {
            'light_dir0': (0.5, -0.5, -0.7),
            'light_color0': (0.8, 0.78, 0.75),
            'light_dir1': (-0.5, 0.3, -0.5),
            'light_color1': (0.3, 0.32, 0.35),
            'ambient': (0.15, 0.15, 0.18)
        }

        # Texture opacity (overall)
        self.texture_opacity = 1.0

        # Painting state
        self.is_painting = False
        self.needs_update = False
        self.active_layer_index = 0
        self._first_paint = False
        self._update_debug = False

        # UV scale tracking for consistent brush size across faces
        self._last_uv_scale = 1.0
        self._avg_uv_scale = 1.0  # Average UV scale across model
        self._uv_debug = False

    def _create_layer_shader(self):
        """Create shader for GPU layer compositing with lighting"""
        vertex = """
#version 130
in vec4 p3d_Vertex;
in vec3 p3d_Normal;
in vec2 p3d_MultiTexCoord0;
uniform mat4 p3d_ModelViewProjectionMatrix;
uniform mat4 p3d_ModelMatrix;
uniform mat3 p3d_NormalMatrix;
out vec2 texcoord;
out vec3 worldNormal;
out vec3 worldPos;

void main() {
    gl_Position = p3d_ModelViewProjectionMatrix * p3d_Vertex;
    texcoord = p3d_MultiTexCoord0;
    worldNormal = normalize(p3d_NormalMatrix * p3d_Normal);
    worldPos = vec3(p3d_ModelMatrix * p3d_Vertex);
}
"""
        # Fragment shader composites up to 8 layers using individual uniforms
        fragment = """
#version 130
in vec2 texcoord;
in vec3 worldNormal;
in vec3 worldPos;
out vec4 fragColor;

uniform sampler2D layer0;
uniform sampler2D layer1;
uniform sampler2D layer2;
uniform sampler2D layer3;
uniform sampler2D layer4;
uniform sampler2D layer5;
uniform sampler2D layer6;
uniform sampler2D layer7;

uniform float opacity0, opacity1, opacity2, opacity3, opacity4, opacity5, opacity6, opacity7;
uniform float visible0, visible1, visible2, visible3, visible4, visible5, visible6, visible7;
uniform int numLayers;

// Simple lighting uniforms (set from Python)
uniform vec3 lightDir0;
uniform vec3 lightColor0;
uniform vec3 lightDir1;
uniform vec3 lightColor1;
uniform vec3 ambientLight;

vec4 blendLayer(vec4 result, vec4 layerColor, float opacity, float visible) {
    if (visible < 0.5) return result;
    float srcAlpha = layerColor.a * opacity;
    vec3 srcRGB = layerColor.rgb * opacity;
    result.rgb = srcRGB + result.rgb * (1.0 - srcAlpha);
    result.a = srcAlpha + result.a * (1.0 - srcAlpha);
    return result;
}

void main() {
    // Start with base gray color
    vec4 result = vec4(0.0);
    vec3 baseColor = vec3(0.5);  // Default gray
    
    // Composite all visible layers
    if (numLayers > 0 && visible0 > 0.5) {
        vec4 c = texture(layer0, texcoord);
        result = blendLayer(result, c, opacity0, visible0);
    }
    if (numLayers > 1 && visible1 > 0.5) {
        vec4 c = texture(layer1, texcoord);
        result = blendLayer(result, c, opacity1, visible1);
    }
    if (numLayers > 2 && visible2 > 0.5) {
        vec4 c = texture(layer2, texcoord);
        result = blendLayer(result, c, opacity2, visible2);
    }
    if (numLayers > 3 && visible3 > 0.5) {
        vec4 c = texture(layer3, texcoord);
        result = blendLayer(result, c, opacity3, visible3);
    }
    if (numLayers > 4 && visible4 > 0.5) {
        vec4 c = texture(layer4, texcoord);
        result = blendLayer(result, c, opacity4, visible4);
    }
    if (numLayers > 5 && visible5 > 0.5) {
        vec4 c = texture(layer5, texcoord);
        result = blendLayer(result, c, opacity5, visible5);
    }
    if (numLayers > 6 && visible6 > 0.5) {
        vec4 c = texture(layer6, texcoord);
        result = blendLayer(result, c, opacity6, visible6);
    }
    if (numLayers > 7 && visible7 > 0.5) {
        vec4 c = texture(layer7, texcoord);
        result = blendLayer(result, c, opacity7, visible7);
    }
    
    // Blend paint over base color
    if (result.a > 0.01) {
        vec3 paintColor = result.rgb / result.a;
        baseColor = mix(baseColor, paintColor, result.a);
    }
    
    // Calculate lighting
    vec3 N = normalize(worldNormal);
    
    // Ambient
    vec3 litColor = ambientLight * baseColor;
    
    // Directional light 0
    float NdotL0 = max(dot(N, normalize(lightDir0)), 0.0);
    litColor += lightColor0 * baseColor * NdotL0;
    
    // Directional light 1
    float NdotL1 = max(dot(N, normalize(lightDir1)), 0.0);
    litColor += lightColor1 * baseColor * NdotL1;
    
    fragColor = vec4(litColor, 1.0);
}
"""
        self.layer_shader = Shader.make(Shader.SL_GLSL, vertex, fragment)

    def _apply_shader(self):
        """Apply the layer compositing shader to the model"""
        if not self.model or not self.layer_shader:
            return


        # Find all GeomNodes - these are what actually render
        geom_nodes = self.model.findAllMatches('**/+GeomNode')

        if not geom_nodes:
            if hasattr(self.model.node(), 'getNumGeoms'):
                geom_nodes = [self.model]


        # Apply shader to each GeomNode with high priority
        for geom_np in geom_nodes:
            # CRITICAL: Clear existing texture attributes from glTF
            # This prevents the original textures from interfering with our paint shader
            geom_np.clearTexture()
            geom_np.setTextureOff(200)  # Disable any inherited textures with high priority

            geom_np.setShader(self.layer_shader, 200)

            # Set layer textures
            for i in range(self.MAX_LAYERS):
                if i < len(self.layers):
                    tex = self.layers[i]['texture']
                else:
                    if not hasattr(self, '_dummy_tex'):
                        dummy_img = PNMImage(1, 1, 4)
                        dummy_img.fill(0, 0, 0)
                        dummy_img.alphaFill(0)
                        self._dummy_tex = Texture('dummy')
                        self._dummy_tex.load(dummy_img)
                    tex = self._dummy_tex

                geom_np.setShaderInput(f"layer{i}", tex)

            # Set uniforms
            for i in range(self.MAX_LAYERS):
                if i < len(self.layers):
                    geom_np.setShaderInput(f"opacity{i}", self.layers[i]['opacity'])
                    geom_np.setShaderInput(f"visible{i}", 1.0 if self.layers[i]['visible'] else 0.0)
                else:
                    geom_np.setShaderInput(f"opacity{i}", 0.0)
                    geom_np.setShaderInput(f"visible{i}", 0.0)
            geom_np.setShaderInput("numLayers", len(self.layers))

            # Apply stored lighting state
            from panda3d.core import Vec3
            geom_np.setShaderInput("lightDir0", Vec3(*self._lighting_state['light_dir0']))
            geom_np.setShaderInput("lightColor0", Vec3(*self._lighting_state['light_color0']))
            geom_np.setShaderInput("lightDir1", Vec3(*self._lighting_state['light_dir1']))
            geom_np.setShaderInput("lightColor1", Vec3(*self._lighting_state['light_color1']))
            geom_np.setShaderInput("ambientLight", Vec3(*self._lighting_state['ambient']))

        # Store geom nodes for later updates
        self._geom_nodes = geom_nodes

    def update_lighting(self, light_dir0, light_color0, light_dir1, light_color1, ambient):
        """Update lighting uniforms on all geom nodes"""
        # Store lighting state so it persists across _apply_shader calls
        self._lighting_state = {
            'light_dir0': light_dir0,
            'light_color0': light_color0,
            'light_dir1': light_dir1,
            'light_color1': light_color1,
            'ambient': ambient
        }

        if not hasattr(self, '_geom_nodes') or not self._geom_nodes:
            return

        from panda3d.core import Vec3
        for geom_np in self._geom_nodes:
            geom_np.setShaderInput("lightDir0", Vec3(*light_dir0))
            geom_np.setShaderInput("lightColor0", Vec3(*light_color0))
            geom_np.setShaderInput("lightDir1", Vec3(*light_dir1))
            geom_np.setShaderInput("lightColor1", Vec3(*light_color1))
            geom_np.setShaderInput("ambientLight", Vec3(*ambient))


    def _update_shader_uniforms(self):
        """Update shader uniforms for opacity and visibility"""
        if not hasattr(self, '_geom_nodes') or not self._geom_nodes:
            return

        # Update uniforms on all GeomNodes
        for geom_np in self._geom_nodes:
            for i in range(self.MAX_LAYERS):
                if i < len(self.layers):
                    geom_np.setShaderInput(f"opacity{i}", self.layers[i]['opacity'])
                    geom_np.setShaderInput(f"visible{i}", 1.0 if self.layers[i]['visible'] else 0.0)
                else:
                    geom_np.setShaderInput(f"opacity{i}", 0.0)
                    geom_np.setShaderInput(f"visible{i}", 0.0)
            geom_np.setShaderInput("numLayers", len(self.layers))

    def setup_for_model(self, model, texture_size=1024):
        """Extract mesh data and prepare for painting"""
        self.model = model
        self.texture_size = texture_size
        self.triangles = []
        self.layers = []
        self._geom_nodes = []
        self.active_layer_index = 0
        self._last_uv_scale = 1.0
        self._avg_uv_scale = 1.0
        self._flush_debug_done = False
        self._paint_uv_debug = False

        # Edge adjacency map for cross-edge painting
        self.edge_adjacency = {}  # edge_key -> list of (tri_index, edge_verts, edge_uvs)

        # Extract triangles with UVs from model geometry
        self._extract_mesh_data(model)

        # Build edge adjacency map
        self._build_edge_adjacency()

        # Compute average UV scale across all triangles
        self._compute_avg_uv_scale()

        # Analyze UV layout for debugging
        self._analyze_uv_layout()

        # Create initial paint texture
        self._create_paint_texture()

    def _build_edge_adjacency(self):
        """Build a map of shared edges between triangles"""
        self.edge_adjacency = {}

        def make_edge_key(v1, v2):
            """Create a canonical key for an edge (order-independent)"""
            # Round to avoid floating point issues
            p1 = (round(v1.x, 4), round(v1.y, 4), round(v1.z, 4))
            p2 = (round(v2.x, 4), round(v2.y, 4), round(v2.z, 4))
            return tuple(sorted([p1, p2]))

        for tri_idx, (v0, v1, v2, uv0, uv1, uv2) in enumerate(self.triangles):
            # Three edges per triangle
            edges = [
                (v0, v1, uv0, uv1),
                (v1, v2, uv1, uv2),
                (v2, v0, uv2, uv0),
            ]

            for va, vb, uva, uvb in edges:
                key = make_edge_key(va, vb)
                if key not in self.edge_adjacency:
                    self.edge_adjacency[key] = []
                self.edge_adjacency[key].append({
                    'tri_idx': tri_idx,
                    'v_start': va,
                    'v_end': vb,
                    'uv_start': uva,
                    'uv_end': uvb,
                    'triangle': (v0, v1, v2, uv0, uv1, uv2)
                })

        # Count shared edges for debug
        shared_count = sum(1 for edges in self.edge_adjacency.values() if len(edges) > 1)
        print(f"Built edge adjacency: {len(self.edge_adjacency)} edges, {shared_count} shared")


    def _compute_avg_uv_scale(self):
        """Compute average UV scale across all triangles"""
        if not self.triangles:
            self._avg_uv_scale = 1.0
            return

        total_scale = 0.0
        count = 0
        for v0, v1, v2, uv0, uv1, uv2 in self.triangles:
            scale = self._calc_uv_scale(v0, v1, v2, uv0, uv1, uv2)
            if scale > 0.0001:
                total_scale += scale
                count += 1

        if count > 0:
            self._avg_uv_scale = total_scale / count
        else:
            self._avg_uv_scale = 1.0

    def _analyze_uv_layout(self):
        """Analyze and print UV regions per face for debugging"""
        from panda3d.core import Point3

        # Collect UV bounds per face
        face_uvs = {'+X': [], '-X': [], '+Y': [], '-Y': [], '+Z': [], '-Z': []}

        for v0, v1, v2, uv0, uv1, uv2 in self.triangles:
            # Calculate face normal
            e1 = Point3(v1.x - v0.x, v1.y - v0.y, v1.z - v0.z)
            e2 = Point3(v2.x - v0.x, v2.y - v0.y, v2.z - v0.z)
            normal = Point3(
                e1.y * e2.z - e1.z * e2.y,
                e1.z * e2.x - e1.x * e2.z,
                e1.x * e2.y - e1.y * e2.x
            )

            # Determine face
            ax, ay, az = abs(normal.x), abs(normal.y), abs(normal.z)
            if ax > ay and ax > az:
                face = "+X" if normal.x > 0 else "-X"
            elif ay > az:
                face = "+Y" if normal.y > 0 else "-Y"
            else:
                face = "+Z" if normal.z > 0 else "-Z"

            # Store UV center for this triangle
            uv_center = ((uv0.x + uv1.x + uv2.x) / 3, (uv0.y + uv1.y + uv2.y) / 3)
            face_uvs[face].append(uv_center)

        print("\n=== UV LAYOUT ANALYSIS ===")
        for face, uvs in face_uvs.items():
            if uvs:
                avg_u = sum(uv[0] for uv in uvs) / len(uvs)
                avg_v = sum(uv[1] for uv in uvs) / len(uvs)
                print(f"  {face} face: UV center ~ ({avg_u:.2f}, {avg_v:.2f})")
        print("===========================\n")

    def _extract_mesh_data(self, model):
        """Extract all triangles with their UV coordinates"""
        geom_nodes = model.findAllMatches('**/+GeomNode')

        for geom_np in geom_nodes:
            geom_node = geom_np.node()
            transform = geom_np.getTransform(model)
            mat = transform.getMat()

            for i in range(geom_node.getNumGeoms()):
                geom = geom_node.getGeom(i)
                self._extract_triangles_from_geom(geom, mat)


    def _extract_triangles_from_geom(self, geom, transform_mat):
        """Extract triangles from a single Geom"""
        vdata = geom.getVertexData()

        # Create readers
        vertex_reader = GeomVertexReader(vdata, 'vertex')

        # Check for UVs - try different column names (glTF uses different names)
        uv_column = None
        for name in ['texcoord', 'texcoord.0', 'texcoord0']:
            if vdata.hasColumn(name):
                uv_column = name
                break

        if not uv_column:
            # List available columns for debugging
            fmt = vdata.getFormat()
            cols = [fmt.getColumn(i).getName() for i in range(fmt.getNumColumns())]
            return

        uv_reader = GeomVertexReader(vdata, uv_column)

        # Read all vertices and UVs
        vertices = []
        uvs = []

        while not vertex_reader.isAtEnd():
            v = vertex_reader.getData3()
            # Transform vertex to model space
            v = transform_mat.xformPoint(Point3(v))
            vertices.append(v)

        while not uv_reader.isAtEnd():
            uv = uv_reader.getData2()
            uvs.append(Vec2(uv))

        # Process each primitive
        for prim_idx in range(geom.getNumPrimitives()):
            prim = geom.getPrimitive(prim_idx)
            prim = prim.decompose()  # Convert to triangles

            for i in range(prim.getNumPrimitives()):
                start = prim.getPrimitiveStart(i)

                # Get vertex indices
                i0 = prim.getVertex(start)
                i1 = prim.getVertex(start + 1)
                i2 = prim.getVertex(start + 2)

                if i0 < len(vertices) and i1 < len(vertices) and i2 < len(vertices):
                    if i0 < len(uvs) and i1 < len(uvs) and i2 < len(uvs):
                        self.triangles.append((
                            vertices[i0], vertices[i1], vertices[i2],
                            uvs[i0], uvs[i1], uvs[i2]
                        ))

    def _create_paint_texture(self):
        """Initialize shader for GPU layer compositing"""
        # Create the layer compositing shader
        self._create_layer_shader()

    def create_texture_for_painting(self):
        """Create a paint texture when user adds one through UI"""
        # Add a default base layer if none exist (transparent)
        if not self.layers:
            self.add_layer("Base")

        # Initialize history with current state
        self.clear_history()

        return True

    def add_layer(self, name, fill_color=None, record_history=True):
        """Add a new layer (transparent by default) with its own GPU texture"""
        if len(self.layers) >= self.MAX_LAYERS:
            return -1

        # Create image - with premultiplied alpha, transparent = (0,0,0,0)
        img = PNMImage(self.texture_size, self.texture_size, 4)
        if fill_color is not None:
            # For non-transparent fill, premultiply the color
            img.fill(fill_color[0] * fill_color[3], fill_color[1] * fill_color[3], fill_color[2] * fill_color[3])
            img.alphaFill(fill_color[3])
        else:
            # Transparent = black with zero alpha (premultiplied)
            img.fill(0.0, 0.0, 0.0)
            img.alphaFill(0.0)

        # Create GPU texture for this layer
        tex = Texture(f'layer_{name}')
        tex.load(img)
        tex.setMagfilter(Texture.FTLinear)
        tex.setMinfilter(Texture.FTLinear)
        tex.setWrapU(Texture.WMClamp)
        tex.setWrapV(Texture.WMClamp)

        layer = {
            'name': name,
            'image': img,
            'texture': tex,
            'opacity': 1.0,
            'visible': True
        }
        self.layers.append(layer)  # Add at end (top in UI since we display reversed)
        self.active_layer_index = len(self.layers) - 1  # Select the new top layer

        # Update shader with new layer
        self._apply_shader()

        # Save state AFTER adding
        if record_history:
            self.save_history("Add Layer")

        return len(self.layers) - 1

    def remove_layer(self, index):
        """Remove a layer"""
        if 0 <= index < len(self.layers) and len(self.layers) > 1:
            self.layers.pop(index)
            if self.active_layer_index >= len(self.layers):
                self.active_layer_index = len(self.layers) - 1
            # Re-apply shader with updated layers
            self._apply_shader()
            # Save state AFTER removing
            self.save_history("Delete Layer")

    def reorder_layer(self, from_index, to_index):
        """Move a layer from one position to another"""
        if 0 <= from_index < len(self.layers) and 0 <= to_index < len(self.layers):
            layer = self.layers.pop(from_index)
            self.layers.insert(to_index, layer)
            # Update active layer index
            if self.active_layer_index == from_index:
                self.active_layer_index = to_index
            elif from_index < self.active_layer_index <= to_index:
                self.active_layer_index -= 1
            elif to_index <= self.active_layer_index < from_index:
                self.active_layer_index += 1
            # Re-apply shader with reordered layers
            self._apply_shader()
            # Save state AFTER reordering
            self.save_history("Reorder Layer")

    def set_active_layer(self, index):
        """Set active layer with history"""
        if 0 <= index < len(self.layers) and index != self.active_layer_index:
            self.active_layer_index = index
            # Save state AFTER selection
            self.save_history("Select Layer")

    def set_layer_opacity(self, index, opacity):
        """Set a layer's opacity - updates GPU shader uniform"""
        if 0 <= index < len(self.layers):
            self.layers[index]['opacity'] = max(0.0, min(1.0, opacity))
            self._update_shader_uniforms()

    def set_layer_visible(self, index, visible):
        """Set a layer's visibility - updates GPU shader uniform"""
        if 0 <= index < len(self.layers):
            self.layers[index]['visible'] = visible
            self._update_shader_uniforms()

    def set_texture_opacity(self, opacity):
        """Set overall texture opacity"""
        self.texture_opacity = max(0.0, min(1.0, opacity))
        if self.model:
            self.model.setColorScale(1, 1, 1, self.texture_opacity)

    # --- History Management ---

    def save_history(self, action_name="Paint"):
        """Save current state to history (call AFTER making changes)"""
        if not self.layers:
            return

        # Remove any redo states if we're not at the end
        if self.history_index < len(self.history) - 1:
            self.history = self.history[:self.history_index + 1]

        # Create new history state
        state = HistoryState(action_name, self.layers, self.active_layer_index)
        self.history.append(state)

        # Trim old history if over limit
        if len(self.history) > self.MAX_HISTORY:
            self.history.pop(0)

        self.history_index = len(self.history) - 1

    def begin_stroke(self):
        """Call when starting a paint stroke"""
        self.stroke_in_progress = True

    def end_stroke(self):
        """Call when ending a paint stroke - saves state for undo"""
        if self.stroke_in_progress:
            self.save_history("Brush Stroke")
            self.stroke_in_progress = False

    def undo(self):
        """Undo to previous state"""
        if self.history_index > 0:
            self.history_index -= 1
            self._restore_state(self.history[self.history_index])
            return True
        return False

    def redo(self):
        """Redo to next state"""
        if self.history_index < len(self.history) - 1:
            self.history_index += 1
            self._restore_state(self.history[self.history_index])
            return True
        return False

    def goto_history(self, index):
        """Jump to specific history state"""
        if 0 <= index < len(self.history):
            self.history_index = index
            self._restore_state(self.history[index])
            return True
        return False

    def _restore_state(self, state):
        """Restore layers from a history state"""
        # Handle layer count differences
        saved_count = len(state.layer_data)
        current_count = len(self.layers)

        # Remove extra layers
        while len(self.layers) > saved_count:
            self.layers.pop()

        # Add missing layers
        while len(self.layers) < saved_count:
            img = PNMImage(self.texture_size, self.texture_size, 4)
            tex = Texture(f'layer_restored_{len(self.layers)}')
            tex.load(img)
            tex.setMagfilter(Texture.FTLinear)
            tex.setMinfilter(Texture.FTLinear)
            tex.setWrapU(Texture.WMClamp)
            tex.setWrapV(Texture.WMClamp)
            self.layers.append({
                'name': '',
                'image': img,
                'texture': tex,
                'opacity': 1.0,
                'visible': True
            })

        # Restore layer data
        for i, saved in enumerate(state.layer_data):
            self.layers[i]['image'].copyFrom(saved['image'])
            self.layers[i]['name'] = saved['name']
            self.layers[i]['opacity'] = saved['opacity']
            self.layers[i]['visible'] = saved['visible']
            self.layers[i]['texture'].load(self.layers[i]['image'])

        self.active_layer_index = min(state.active_index, len(self.layers) - 1)
        self._apply_shader()

    def get_history_list(self):
        """Get list of history entries for UI"""
        return [(i, h.name) for i, h in enumerate(self.history)]

    def clear_history(self):
        """Clear all history"""
        self.history = []
        self.history_index = -1
        if self.layers:
            self.save_history("Initial")

    def apply_texture_to_model(self):
        """Apply the layer compositing shader to the model"""
        self._apply_shader()

    def get_uv_at_position(self, hit_pos):
        """Find UV coordinates at a world position using triangle lookup"""
        if not self.triangles:
            return None

        # Debug first call
        if not self._uv_debug:
            self._uv_debug = True

        # Find closest triangle
        closest_dist = float('inf')
        best_uv = None
        best_uv_scale = 1.0

        for v0, v1, v2, uv0, uv1, uv2 in self.triangles:
            # Get triangle center
            cx = (v0.x + v1.x + v2.x) / 3
            cy = (v0.y + v1.y + v2.y) / 3
            cz = (v0.z + v1.z + v2.z) / 3

            dx = hit_pos.x - cx
            dy = hit_pos.y - cy
            dz = hit_pos.z - cz
            dist = math.sqrt(dx*dx + dy*dy + dz*dz)

            if dist < closest_dist:
                closest_dist = dist
                # Try barycentric interpolation
                uv = self._point_to_uv(hit_pos, v0, v1, v2, uv0, uv1, uv2)
                if uv:
                    best_uv = uv
                else:
                    # Fallback to center UV
                    best_uv = Vec2((uv0.x + uv1.x + uv2.x) / 3,
                                  (uv0.y + uv1.y + uv2.y) / 3)

                # Calculate UV scale (texels per world unit)
                best_uv_scale = self._calc_uv_scale(v0, v1, v2, uv0, uv1, uv2)

        # Accept if within reasonable distance (model might be scaled)
        if best_uv and closest_dist < 10.0:
            self._last_uv_scale = best_uv_scale
            return best_uv

        return None

    def _calc_uv_scale(self, v0, v1, v2, uv0, uv1, uv2):
        """Calculate UV density - how many texture pixels per world unit"""
        # World space edge lengths
        edge1_world = math.sqrt((v1.x-v0.x)**2 + (v1.y-v0.y)**2 + (v1.z-v0.z)**2)
        edge2_world = math.sqrt((v2.x-v0.x)**2 + (v2.y-v0.y)**2 + (v2.z-v0.z)**2)

        # UV space edge lengths
        edge1_uv = math.sqrt((uv1.x-uv0.x)**2 + (uv1.y-uv0.y)**2)
        edge2_uv = math.sqrt((uv2.x-uv0.x)**2 + (uv2.y-uv0.y)**2)

        # Average UV units per world unit
        if edge1_world > 0.0001 and edge2_world > 0.0001:
            scale1 = edge1_uv / edge1_world
            scale2 = edge2_uv / edge2_world
            return (scale1 + scale2) / 2.0

        return 1.0

    def _point_to_uv(self, p, v0, v1, v2, uv0, uv1, uv2):
        """Convert world point to UV using barycentric coordinates"""
        # Compute vectors
        v0v1 = v1 - v0
        v0v2 = v2 - v0
        v0p = p - v0

        # Compute dot products
        d00 = v0v1.dot(v0v1)
        d01 = v0v1.dot(v0v2)
        d11 = v0v2.dot(v0v2)
        d20 = v0p.dot(v0v1)
        d21 = v0p.dot(v0v2)

        # Compute barycentric coordinates
        denom = d00 * d11 - d01 * d01
        if abs(denom) < 1e-10:
            return None

        v = (d11 * d20 - d01 * d21) / denom
        w = (d00 * d21 - d01 * d20) / denom
        u = 1.0 - v - w

        # Check if point is inside triangle (with some tolerance)
        tolerance = 0.1
        if u >= -tolerance and v >= -tolerance and w >= -tolerance and u <= 1 + tolerance and v <= 1 + tolerance and w <= 1 + tolerance:
            # Interpolate UV
            result_uv = Vec2(
                u * uv0.x + v * uv1.x + w * uv2.x,
                u * uv0.y + v * uv1.y + w * uv2.y
            )
            return result_uv

        return None

    def paint_at_world_pos(self, world_pos, color, size, opacity, hardness, shape='Round', layer_index=None, log=True, hit_normal=None):
        """Paint at world position, with proper cross-edge UV mapping"""

        if not self.triangles or not self.layers:
            return False

        # Transform world position to model-local space
        import builtins
        if self.model:
            local_pos = self.model.getRelativePoint(builtins.base.render, world_pos)
        else:
            local_pos = world_pos

        # Convert brush size from pixels to world units
        if self._avg_uv_scale > 0.001:
            world_radius = (size / 2) / (self.texture_size * self._avg_uv_scale)
        else:
            world_radius = size / self.texture_size

        # Helper to compute triangle normal
        def get_normal(v0, v1, v2):
            e1 = Point3(v1.x - v0.x, v1.y - v0.y, v1.z - v0.z)
            e2 = Point3(v2.x - v0.x, v2.y - v0.y, v2.z - v0.z)
            n = Point3(
                e1.y * e2.z - e1.z * e2.y,
                e1.z * e2.x - e1.x * e2.z,
                e1.x * e2.y - e1.y * e2.x
            )
            length = math.sqrt(n.x*n.x + n.y*n.y + n.z*n.z)
            if length > 0.0001:
                return Point3(n.x/length, n.y/length, n.z/length)
            return Point3(0, 0, 1)

        # Convert hit_normal to local space if provided (for constraining to same face)
        local_hit_normal = None
        if hit_normal is not None and self.model:
            from panda3d.core import Vec3
            world_normal = Vec3(hit_normal.x, hit_normal.y, hit_normal.z)
            ln = self.model.getRelativeVector(builtins.base.render, world_normal)
            local_hit_normal = Point3(ln.x, ln.y, ln.z)

        # Find the PRIMARY triangle (closest to brush center, matching face if hit_normal provided)
        primary_tri_idx = -1
        primary_closest = None
        min_dist = float('inf')

        for tri_idx, (v0, v1, v2, uv0, uv1, uv2) in enumerate(self.triangles):
            # If we have a hit_normal, only consider triangles facing same direction
            if local_hit_normal is not None:
                tri_normal = get_normal(v0, v1, v2)
                dot = (local_hit_normal.x * tri_normal.x +
                       local_hit_normal.y * tri_normal.y +
                       local_hit_normal.z * tri_normal.z)
                if dot < 0.5:  # Must be facing same general direction
                    continue

            closest = self._closest_point_on_triangle(local_pos, v0, v1, v2)
            dist = math.sqrt(
                (local_pos.x - closest.x)**2 +
                (local_pos.y - closest.y)**2 +
                (local_pos.z - closest.z)**2
            )
            if dist < min_dist:
                min_dist = dist
                primary_tri_idx = tri_idx
                primary_closest = closest

        if primary_tri_idx < 0:
            return False

        primary_tri = self.triangles[primary_tri_idx]
        v0, v1, v2, uv0, uv1, uv2 = primary_tri
        primary_normal = get_normal(v0, v1, v2)

        # Paint on the primary triangle
        uv = self._point_to_uv(local_pos, v0, v1, v2, uv0, uv1, uv2)
        if uv is None:
            uv = self._point_to_uv(primary_closest, v0, v1, v2, uv0, uv1, uv2)

        painted_any = False
        if uv:
            if log:
                print(f"PRIMARY paint UV=({uv.x:.3f}, {uv.y:.3f})")
            self.paint_at_uv(uv, color, size, opacity, hardness, shape, layer_index)
            painted_any = True

        # Also paint on other triangles on the SAME face within brush radius
        for tri_idx, (tv0, tv1, tv2, tuv0, tuv1, tuv2) in enumerate(self.triangles):
            if tri_idx == primary_tri_idx:
                continue

            tri_normal = get_normal(tv0, tv1, tv2)
            dot = (primary_normal.x * tri_normal.x +
                   primary_normal.y * tri_normal.y +
                   primary_normal.z * tri_normal.z)

            # Only same-face triangles (very similar normal)
            if dot < 0.99:
                continue

            closest = self._closest_point_on_triangle(local_pos, tv0, tv1, tv2)
            dist = math.sqrt(
                (local_pos.x - closest.x)**2 +
                (local_pos.y - closest.y)**2 +
                (local_pos.z - closest.z)**2
            )

            if dist < world_radius:
                tuv = self._point_to_uv(local_pos, tv0, tv1, tv2, tuv0, tuv1, tuv2)
                if tuv is None:
                    tuv = self._point_to_uv(closest, tv0, tv1, tv2, tuv0, tuv1, tuv2)
                if tuv:
                    self.paint_at_uv(tuv, color, size, opacity, hardness, shape, layer_index)
                    painted_any = True

        # Now handle cross-edge painting to adjacent triangles (only if this is a direct hit, not interpolated)
        # Skip cross-edge for interpolated points (when hit_normal is provided but we're inside stroke)
        if not log:
            # This is an interpolated stroke point - skip cross-edge to avoid artifacts
            return painted_any

        # Find which edge of primary triangle the brush might cross
        edges = [
            (v0, v1, uv0, uv1),
            (v1, v2, uv1, uv2),
            (v2, v0, uv2, uv0),
        ]

        def make_edge_key(va, vb):
            p1 = (round(va.x, 4), round(va.y, 4), round(va.z, 4))
            p2 = (round(vb.x, 4), round(vb.y, 4), round(vb.z, 4))
            return tuple(sorted([p1, p2]))

        def point_to_line_dist(p, a, b):
            """Distance from point p to line segment a-b, and parameter t"""
            ab = Point3(b.x - a.x, b.y - a.y, b.z - a.z)
            ap = Point3(p.x - a.x, p.y - a.y, p.z - a.z)
            ab_len_sq = ab.x*ab.x + ab.y*ab.y + ab.z*ab.z
            if ab_len_sq < 0.0001:
                return math.sqrt(ap.x*ap.x + ap.y*ap.y + ap.z*ap.z), 0.0
            t = max(0, min(1, (ap.x*ab.x + ap.y*ab.y + ap.z*ab.z) / ab_len_sq))
            closest = Point3(a.x + t*ab.x, a.y + t*ab.y, a.z + t*ab.z)
            dx, dy, dz = p.x - closest.x, p.y - closest.y, p.z - closest.z
            return math.sqrt(dx*dx + dy*dy + dz*dz), t

        for va, vb, uva, uvb in edges:
            edge_key = make_edge_key(va, vb)

            # Distance from brush center to this edge
            edge_dist, t_along_edge = point_to_line_dist(local_pos, va, vb)

            # If brush overlaps this edge
            if edge_dist < world_radius:
                # Find adjacent triangles on this edge
                adjacent_tris = self.edge_adjacency.get(edge_key, [])

                for adj_info in adjacent_tris:
                    if adj_info['tri_idx'] == primary_tri_idx:
                        continue  # Skip the primary triangle

                    # Check if this is a same-face or different-face triangle
                    adj_tri = adj_info['triangle']
                    adj_v0, adj_v1, adj_v2, adj_uv0, adj_uv1, adj_uv2 = adj_tri
                    adj_normal = get_normal(adj_v0, adj_v1, adj_v2)
                    dot = (primary_normal.x * adj_normal.x +
                           primary_normal.y * adj_normal.y +
                           primary_normal.z * adj_normal.z)

                    # Skip same-face triangles (dot near 1.0)
                    if dot > 0.5:
                        continue

                    # Get the adjacent triangle's edge vertices and UVs
                    adj_v_start = adj_info['v_start']
                    adj_v_end = adj_info['v_end']
                    adj_uv_start = adj_info['uv_start']
                    adj_uv_end = adj_info['uv_end']

                    # Check if edges are in same or reversed direction
                    # Compare va with adj_v_start
                    va_matches_start = (
                        abs(va.x - adj_v_start.x) < 0.001 and
                        abs(va.y - adj_v_start.y) < 0.001 and
                        abs(va.z - adj_v_start.z) < 0.001
                    )

                    # Map t parameter to adjacent edge
                    if va_matches_start:
                        adj_t = t_along_edge
                    else:
                        adj_t = 1.0 - t_along_edge

                    # Compute UV directly from adjacent edge's UV coordinates
                    adj_uv = Vec2(
                        adj_uv_start.x + adj_t * (adj_uv_end.x - adj_uv_start.x),
                        adj_uv_start.y + adj_t * (adj_uv_end.y - adj_uv_start.y)
                    )

                    if log:
                        print(f"  Cross-edge: t={t_along_edge:.2f} adj_t={adj_t:.2f} va_matches={va_matches_start}")
                        print(f"    Primary edge UV: ({uva.x:.3f},{uva.y:.3f})->({uvb.x:.3f},{uvb.y:.3f})")
                        print(f"    Adj edge UV: ({adj_uv_start.x:.3f},{adj_uv_start.y:.3f})->({adj_uv_end.x:.3f},{adj_uv_end.y:.3f})")
                        print(f"    Result UV: ({adj_uv.x:.3f},{adj_uv.y:.3f})")

                    # Calculate how far into the adjacent face the brush extends
                    overlap_dist = world_radius - edge_dist

                    # Paint with reduced size based on overlap
                    overlap_ratio = overlap_dist / world_radius
                    adj_size = size * overlap_ratio
                    if adj_size > 1:
                        self.paint_at_uv(adj_uv, color, adj_size, opacity, hardness, shape, layer_index)
                        painted_any = True

        return painted_any

    def _closest_point_on_triangle(self, p, v0, v1, v2):
        """Find the closest point on a triangle to point p"""
        from panda3d.core import LPoint3f

        # Edge vectors
        edge0 = LPoint3f(v1.x - v0.x, v1.y - v0.y, v1.z - v0.z)
        edge1 = LPoint3f(v2.x - v0.x, v2.y - v0.y, v2.z - v0.z)
        v0p = LPoint3f(v0.x - p.x, v0.y - p.y, v0.z - p.z)

        a = edge0.x*edge0.x + edge0.y*edge0.y + edge0.z*edge0.z
        b = edge0.x*edge1.x + edge0.y*edge1.y + edge0.z*edge1.z
        c = edge1.x*edge1.x + edge1.y*edge1.y + edge1.z*edge1.z
        d = edge0.x*v0p.x + edge0.y*v0p.y + edge0.z*v0p.z
        e = edge1.x*v0p.x + edge1.y*v0p.y + edge1.z*v0p.z

        det = a*c - b*b
        s = b*e - c*d
        t = b*d - a*e

        if det < 0.0001:
            # Degenerate triangle
            return v0

        if s + t <= det:
            if s < 0:
                if t < 0:
                    # Region 4
                    s = max(0, min(1, -d/a)) if a > 0.0001 else 0
                    t = 0
                else:
                    # Region 3
                    s = 0
                    t = max(0, min(1, -e/c)) if c > 0.0001 else 0
            elif t < 0:
                # Region 5
                s = max(0, min(1, -d/a)) if a > 0.0001 else 0
                t = 0
            else:
                # Region 0 (inside triangle)
                s /= det
                t /= det
        else:
            if s < 0:
                # Region 2
                s = 0
                t = max(0, min(1, -e/c)) if c > 0.0001 else 0
            elif t < 0:
                # Region 6
                s = max(0, min(1, -d/a)) if a > 0.0001 else 0
                t = 0
            else:
                # Region 1
                numer = c + e - b - d
                denom = a - 2*b + c
                s = max(0, min(1, numer/denom)) if denom > 0.0001 else 0
                t = 1 - s

        return LPoint3f(
            v0.x + s*edge0.x + t*edge1.x,
            v0.y + s*edge0.y + t*edge1.y,
            v0.z + s*edge0.z + t*edge1.z
        )

    def paint_at_uv(self, uv, color, size, opacity, hardness, shape='Round', layer_index=None):
        """Paint a brush stroke at the given UV coordinates"""
        # Use active layer if not specified
        if layer_index is None:
            layer_index = self.active_layer_index

        if not self.layers:
            return False

        if layer_index < 0 or layer_index >= len(self.layers):
            return False

        img = self.layers[layer_index]['image']

        # Convert UV to pixel coordinates
        px = int(uv.x * self.texture_size) % self.texture_size
        py = int((1.0 - uv.y) * self.texture_size) % self.texture_size

        # Adjust brush size based on UV density for consistent world-space size
        adjusted_size = size
        if self._avg_uv_scale > 0.001 and self._last_uv_scale > 0.001:
            ratio = self._last_uv_scale / self._avg_uv_scale
            adjusted_size = size * ratio

        # Clamp to reasonable range (0.25x to 4x)
        adjusted_size = max(size * 0.25, min(adjusted_size, size * 4))

        # Brush radius in pixels
        radius = max(1, int(adjusted_size / 2))

        pixels_changed = 0

        # Paint brush stamp based on shape
        for dy in range(-radius, radius + 1):
            for dx in range(-radius, radius + 1):
                # Check if pixel is inside brush shape
                inside = False
                falloff = 1.0

                if shape == 'Round' or shape == 'Soft':
                    # Circular brush
                    dist_sq = dx * dx + dy * dy
                    if dist_sq <= radius * radius:
                        inside = True
                        dist = math.sqrt(dist_sq)
                        if radius > 0:
                            t = dist / radius  # 0 at center, 1 at edge
                            if shape == 'Soft':
                                # Soft brush - smooth gaussian-like falloff
                                # Using smoothstep-like curve for very soft edges
                                falloff = 1.0 - (t * t * (3.0 - 2.0 * t))
                            else:
                                # Round brush uses hardness parameter
                                hardness_factor = hardness / 100.0
                                # At hardness=0: very soft, at hardness=100: hard edge
                                falloff = 1.0 - pow(t, 1.0 + (1.0 - hardness_factor) * 4)
                            falloff = max(0.0, min(1.0, falloff))

                elif shape == 'Square':
                    # Square brush - no distance falloff
                    if abs(dx) <= radius and abs(dy) <= radius:
                        inside = True
                        falloff = 1.0

                elif shape == 'Flat':
                    # Flat/line brush - thin horizontal line
                    if abs(dx) <= radius and abs(dy) <= max(1, radius // 4):
                        inside = True
                        falloff = 1.0

                if inside:
                    alpha = (opacity / 100.0) * falloff

                    x = (px + dx) % self.texture_size
                    y = (py + dy) % self.texture_size

                    if alpha > 0.001:  # Lower threshold for softer edges
                        old_r = img.getRed(x, y)
                        old_g = img.getGreen(x, y)
                        old_b = img.getBlue(x, y)
                        old_a = img.getAlpha(x, y)

                        # Use premultiplied alpha storage
                        # src premultiplied: (color * alpha)
                        src_r = color[0] * alpha
                        src_g = color[1] * alpha
                        src_b = color[2] * alpha

                        # Porter-Duff "over" with premultiplied alpha:
                        # out = src + dst * (1 - src_a)
                        new_r = src_r + old_r * (1 - alpha)
                        new_g = src_g + old_g * (1 - alpha)
                        new_b = src_b + old_b * (1 - alpha)
                        new_a = alpha + old_a * (1 - alpha)

                        img.setXel(x, y, new_r, new_g, new_b)
                        img.setAlpha(x, y, new_a)
                        pixels_changed += 1

        if pixels_changed > 0:
            self.needs_update = True
            self._last_paint_loc = (px, py)
        return True

    def flush_paint(self):
        """Update GPU texture for active layer after painting"""
        try:
            if not self.needs_update:
                return

            if not self.layers or not self.model:
                self.needs_update = False
                return

            layer_index = self.active_layer_index
            layer = self.layers[layer_index]
            img = layer['image']

            # Force complete texture recreation
            old_tex = layer['texture']
            new_tex = Texture(f'layer_{layer_index}_updated')
            new_tex.load(img)
            new_tex.setMagfilter(Texture.FTLinear)
            new_tex.setMinfilter(Texture.FTLinear)
            new_tex.setWrapU(Texture.WMClamp)
            new_tex.setWrapV(Texture.WMClamp)
            layer['texture'] = new_tex

            # Re-bind texture to all GeomNodes
            if hasattr(self, '_geom_nodes') and self._geom_nodes:
                for geom_np in self._geom_nodes:
                    geom_np.setShaderInput(f"layer{layer_index}", layer['texture'])

            self.needs_update = False
        except Exception as e:
            print(f"FLUSH EXCEPTION: {e}")
            import traceback
            traceback.print_exc()

    def composite_and_display(self):
        """Not needed with GPU compositing - shader handles it"""
        pass

    def paint_stroke(self, uv_start, uv_end, color, size, opacity, hardness, spacing, shape='Round', layer_index=None):
        """Paint a stroke between two UV points"""
        if uv_start is None or uv_end is None:
            return

        # Calculate distance in UV space
        dx = uv_end.x - uv_start.x
        dy = uv_end.y - uv_start.y
        dist = math.sqrt(dx * dx + dy * dy)

        # If UV jumped too far, it's likely crossing a seam - don't interpolate
        # Just paint at the new point
        max_uv_jump = 0.15  # ~15% of UV space
        if dist > max_uv_jump:
            self.paint_at_uv(uv_end, color, size, opacity, hardness, shape, layer_index)
            return

        if dist < 0.0001:
            self.paint_at_uv(uv_end, color, size, opacity, hardness, shape, layer_index)
            return

        # Spacing in UV space
        step = (spacing / 100.0) * (size / self.texture_size) * 2
        step = max(0.001, step)

        # Paint along stroke
        steps = int(dist / step) + 1
        for i in range(steps + 1):
            t = i / max(1, steps)
            uv = Vec2(
                uv_start.x + dx * t,
                uv_start.y + dy * t
            )
            self.paint_at_uv(uv, color, size, opacity, hardness, shape, layer_index)

    def paint_stroke_world(self, pos_start, pos_end, color, size, opacity, hardness, spacing, shape='Round', layer_index=None, hit_normal=None):
        """Paint a stroke between two world positions, handling edges properly"""
        if pos_start is None or pos_end is None:
            return

        # Calculate distance in world space
        dx = pos_end.x - pos_start.x
        dy = pos_end.y - pos_start.y
        dz = pos_end.z - pos_start.z
        dist = math.sqrt(dx*dx + dy*dy + dz*dz)

        if dist < 0.0001:
            self.paint_at_world_pos(pos_end, color, size, opacity, hardness, shape, layer_index, log=False, hit_normal=hit_normal)
            return

        # Spacing in world space
        # Convert from pixel spacing to world spacing
        if self._avg_uv_scale > 0.001:
            world_spacing = (spacing / 100.0) * (size / (self.texture_size * self._avg_uv_scale))
        else:
            world_spacing = (spacing / 100.0) * 0.1
        world_spacing = max(0.01, world_spacing)

        # Paint along stroke - use hit_normal for all points to constrain to current face
        steps = int(dist / world_spacing) + 1
        from panda3d.core import LPoint3f
        for i in range(steps + 1):
            t = i / max(1, steps)
            pos = LPoint3f(
                pos_start.x + dx * t,
                pos_start.y + dy * t,
                pos_start.z + dz * t
            )
            self.paint_at_world_pos(pos, color, size, opacity, hardness, shape, layer_index, log=False, hit_normal=hit_normal)

    def _update_texture(self):
        """Update the active layer's GPU texture"""
        if self.layers:
            layer = self.layers[self.active_layer_index]
            layer['texture'].load(layer['image'])

    def clear_layer(self, layer_index=None, color=(0.5, 0.5, 0.5)):
        """Clear a layer to a solid color"""
        if layer_index is None:
            layer_index = self.active_layer_index

        if 0 <= layer_index < len(self.layers):
            layer = self.layers[layer_index]
            layer['image'].fill(color[0], color[1], color[2])
            layer['image'].alphaFill(1.0)
            layer['texture'].load(layer['image'])

    def fill_layer(self, color, layer_index=None):
        """Fill entire layer with color (paint bucket tool)"""
        if layer_index is None:
            layer_index = self.active_layer_index

        if not (0 <= layer_index < len(self.layers)):
            return False

        layer = self.layers[layer_index]
        img = layer['image']

        # Fill with premultiplied alpha (color * 1.0 since fill is fully opaque)
        img.fill(color[0], color[1], color[2])
        img.alphaFill(1.0)

        # Update GPU texture
        layer['texture'].clearRamImage()
        layer['texture'].load(img)

        # Re-bind texture to all GeomNodes
        if hasattr(self, '_geom_nodes') and self._geom_nodes:
            for geom_np in self._geom_nodes:
                geom_np.setShaderInput(f"layer{layer_index}", layer['texture'])

        # Save history AFTER fill
        self.save_history("Fill Layer")
        return True