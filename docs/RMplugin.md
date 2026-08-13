# RenderMan Blender Plugin - Material System

## Overview

The RenderMan plugin uses a dynamic node registration system. Nodes are NOT hardcoded - they're loaded from `.args` files when the plugin initializes, but ONLY when the render engine is set to `PRMAN_RENDER`.

## Node Registration

### `__BL_NODES_MAP__` Dictionary

Located in `rman_bl_nodes/__init__.py`:
```python
__BL_NODES_MAP__ = dict()  # Maps shader names to Blender node class names
__RMAN_NODE_TYPES__ = dict()  # Maps class name to node type class
```

### Registration Process

1. **Shader Discovery** walks directories:
   - `$RMANTREE/lib/shaders`
   - `$RMANTREE/lib/plugins/Args`
   - `{addon_path}/Args`

2. **Node Generation** - `generate_node_type()` creates Blender node classes dynamically

3. **Registration** - `__BL_NODES_MAP__[shader_name] = class_name`

Example mappings:
- `PxrSurface` → `PxrSurfaceBxdfNode`
- `LamaDiffuse` → `LamaDiffusePatternNode`
- `PxrTexture` → `PxrTexturePatternNode`

## Key Node Types

### PxrBlenderPrincipledInputs
- **Type**: Pattern Node (not bxdf!)
- **Purpose**: Extracts Blender Principled BSDF parameters
- **Role**: Bridge during conversion ONLY
- **Outputs**: `out_baseColor`, `out_roughness`, `out_normal`, etc.

### Lama Nodes (Lightweight Material System)
- `LamaDiffuse` - Diffuse component
- `LamaSSS` - Subsurface scattering
- `LamaSheen` - Sheen component
- `LamaConductor` - Metallic/reflection
- `LamaDielectric` - Glass/transmission
- `LamaEmission` - Emission
- `LamaMix` - Combines components

### PxrSurface
- **Type**: Bxdf Node (final material output)
- **Purpose**: Complete standalone shader
- **Output**: `bxdf_out` (connects to output)

## Conversion Flow

### `rman_convert_cycles_shader` Operator
Location: `rman_operators/rman_operators_nodetree.py`

1. Creates `RendermanOutputNode`
2. Calls `rman_cycles_convert.convert_cycles_nodetree()`
3. Creates `PxrBlenderPrincipledInputs` to extract BSDF parameters
4. Builds network of Lama nodes:
   ```
   PxrBlenderPrincipledInputs
       ├── LamaDiffuse → LamaMix
       ├── LamaSSS → LamaMix
       ├── LamaSheen → LamaAdd
       ├── LamaConductor → LamaAdd
       ├── LamaDielectric → LamaAdd
       └── LamaEmission → LamaMix
   ```
5. Final output: `LamaSurface` or fallback to `PxrDisneyBsdf`

## Common Errors

### "Subsurface" KeyError
**Cause**: `PxrBlenderPrincipledInputs` node has different inputs than expected by `convert_principled_bsdf_to_lama()`. The function tries to access `inputs['Subsurface']` but the node might not have that socket (different plugin version or incomplete registration).

### "Node type undefined"
**Cause**: Trying to create node with `node_tree.nodes.new("PxrSurface")` directly without going through `__BL_NODES_MAP__`. The node type isn't registered in Blender until the plugin fully initializes.

### Solution Patterns

1. **Always use `__BL_NODES_MAP__`**:
```python
from rman_bl_nodes import __BL_NODES_MAP__
node_name = __BL_NODES_MAP__.get('LamaDiffuse')
node = nt.nodes.new(node_name)
```

2. **Ensure render engine is set**:
```python
bpy.context.scene.render.engine = 'PRMAN_RENDER'
```

3. **Check registration**:
```python
from rman_bl_nodes import __BL_NODES_MAP__
print("Registered nodes:", list(__BL_NODES_MAP__.keys()))
```

## Programmatic Node Creation

### Using __BL_NODES_MAP__
```python
import bpy
from rman_bl_nodes import __BL_NODES_MAP__

# Get node class name
node_name = __BL_NODES_MAP__.get('LamaDiffuse')
if node_name:
    node = nt.nodes.new(node_name)
```

### Using rfb_api (High-level)
```python
from rfb_api import create_bxdf

material, bxdf = create_bxdf('LamaDiffuse')
```

## Notes

- RenderMan nodes are ONLY available when `render.engine = 'PRMAN_RENDER'`
- The category poll functions check: `rd.engine != 'PRMAN_RENDER'`
- PxrBlenderPrincipledInputs is a temporary conversion node - it shouldn't exist in final materials
- The builtin converter has bugs (KeyError on Subsurface) - consider manual conversion using Lama nodes directly