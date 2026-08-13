# Step 3

## Goal

Build UI panel for BlenderMan sidebar with all conversion operations accessible from a single place.

## Current Architecture

### Core Modules

| Module | Purpose |
|--------|---------|
| `__init__.py` | Blender add-on entry point, registers operators and panel |
| `utils.py` | Shared helpers, node creation, positioning logic |
| `convert_material.py` | PBR material → PxrDisney conversion |
| `convert_world.py` | HDRI → PxrDomeLight object conversion |
| `convert_selected_nodes.py` | Selected shader nodes → RenderMan nodes |
| `import_textures.py` | Image files → PxrTexture nodes |

### Key Technical Solutions

**Node Type Resolution:**
```python
# Use __BL_NODES_MAP__ to get actual Blender node class names
import RenderManForBlender.rman_bl_nodes as rman_bl_nodes
mapped = rman_bl_nodes.__BL_NODES_MAP__.get("PxrDisneyBsdf")
```

**PxrDisney Socket Mapping:**
| Blender Input | RenderMan Input |
|---------------|-----------------|
| Base Color | baseColor |
| Roughness | roughness |
| Metallic | metallic |
| Emission Color | emitColor |
| Normal | bumpNormal |

**Node Positioning:**
```python
NODE_HEIGHTS = {
    "PxrTexture": 350,
    "PxrNormalMap": 350,
    "PxrBump": 350,
    "PxrDisneyBsdf": 500,
    "RendermanOutputNode": 500,
    "PxrDisplace": 350,
    "PxrDomeLight": 500,
}
NODE_GAP = 10
NODE_START_X = 1000
```

**World HDRI → PxrDomeLight:**
- Uses `bpy.ops.object.rman_add_light(rman_light_name="PxrDomeLight")`
- Finds created light object in `bpy.data.objects`
- Sets `lightColorMap` on PxrDomeLight node in light's node tree

### Test Results

All unit tests pass (14 passed, 1 skipped for bpy-dependent test).

## Work Completed So Far

1. **convert_material.py** - Converts PBR materials to PxrDisneyBsdf with proper socket mapping, creates PxrTexture nodes for linked images, positions nodes with height-aware staggering
2. **convert_world.py** - Creates PxrDomeLight object via `rman_add_light` operator, sets texture path
3. **convert_selected_nodes.py** - Handles Image, NormalMap, Bump, Environment nodes
4. **import_textures.py** - Imports multiple images as PxrTexture nodes
5. **utils.py** - Added positioning helpers, node heights, NODE_START_X constant

## Next Steps

1. Create UI panel in sidebar
2. Add buttons for each operation
3. Wire operators to panel buttons
4. Test in Blender