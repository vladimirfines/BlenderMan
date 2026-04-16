# Step 1

## Goal

Step 1 from the MVP spec was to create `utils.py` first and use it as the shared foundation for the rest of the add-on. The target for this step was not a usable Blender UI yet, but a stable utility layer that can discover nodes, trace links, map Blender nodes to RenderMan nodes, and support later operators.

## Work completed

Created [utils.py](</Users/vladimiruzkiy/Yandex.Disk.localized/My files/MAIN FOLDER/PROGRAMMING/BlenderMan/utils.py>) with:

- centralized `NODE_TYPE_MAP` and `SOCKET_NAME_MAP`
- debug logger setup
- helpers to enable nodes and collect unique materials
- helpers to find nodes by type and resolve active material output
- socket lookup and upstream socket tracing helpers
- input-chain traversal for linked shader inputs
- RenderMan node factory helper
- colorspace classification helper for color vs data inputs
- deterministic branch layout helpers
- simple report helpers
- fake node-tree classes for non-Blender local testing

Updated [__init__.py](</Users/vladimiruzkiy/Yandex.Disk.localized/My files/MAIN FOLDER/PROGRAMMING/BlenderMan/__init__.py>) so the add-on entry is import-safe outside Blender and already contains minimal `bl_info`, `register()`, and `unregister()` scaffolding.

Added [tests/test_utils.py](</Users/vladimiruzkiy/Yandex.Disk.localized/My files/MAIN FOLDER/PROGRAMMING/BlenderMan/tests/test_utils.py>) to validate the pure-Python parts of the utilities layer without depending on Blender.

## What this step does not include

- no operators yet
- no sidebar panel yet
- no actual Cycles-to-RenderMan conversion pass yet
- no world/HDRI conversion yet
- no file-browser texture import yet

This is intentional and matches the development order in the main spec.

## Local testing setup

The following checks were run in the repo outside Blender:

```bash
python3 -m unittest discover -s tests -p 'test_*.py'
python3 -m py_compile __init__.py utils.py tests/test_utils.py
```

These tests cover:

- unique material collection
- Principled detection through output links
- upstream input-chain tracing
- RenderMan node creation through the mapping table
- deterministic layout positions
- data colorspace assignment for texture inputs

## Blender smoke test setup

The add-on was installed successfully in Blender and validated with a manual smoke test.

Important detail:

- `utils` is not a global top-level module inside Blender
- it must be imported through the add-on package, for example `import BlenderMan.utils as utils`

Smoke test script used in Blender:

```python
import bpy
import BlenderMan.utils as utils

mat = bpy.data.materials.new("BM_Test")
mat.use_nodes = True

tree = mat.node_tree
principled = utils.find_linked_principled(tree)
output = utils.find_material_output(tree)

assert principled is not None, "No Principled node found"
assert output is not None, "No Material Output node found"
assert utils.map_rm_node_type("ShaderNodeTexImage") == "PxrTexture"
assert utils.map_rm_socket_name("Roughness") == "specularRoughness"

bpy.context.window_manager.popup_menu(
    lambda self, ctx: self.layout.label(text="BlenderMan utils smoke test passed"),
    title="BlenderMan",
    icon='INFO',
)
```

Observed result:

- add-on installed without registration errors
- Blender smoke test passed

## Notes for next step

Step 2 should build thin operators on top of `utils.py`. The current utilities are structured so operator modules can mostly orchestrate context selection, reporting, and scenario-specific behavior while shared graph logic remains centralized.
