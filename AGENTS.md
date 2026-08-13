# BlenderMan - AI Agent Guide

BlenderMan is a Blender extension that automates the conversion of Cycles PBR shader materials into RenderMan-ready nodes. It acts as a "Node Wrangler", but for the RenderMan workflow.

## Architecture & Principles

- **Thin Wrappers**: Operators (`convert_material.py`, etc.) and UI (`__init__.py`) are minimal. All logic resides in `utils.py`.
- **Import Safety**: The codebase must remain importable outside of Blender. Use `try: import bpy` and the `bpy is None` check throughout.
- **Additivity**: Never delete Cycles nodes. Always create RenderMan branches *below* the existing setup.
- **Centralized Mapping**: Node and socket transformations are governed by `NODE_TYPE_MAP` and `SOCKET_NAME_MAP` in `utils.py`.

## Core Logic (utils.py)

- `convert_material_nodes(material)`: The entry point for material conversion. Traces the active `ShaderNodeOutputMaterial`.
- `trace_upstream_socket(socket)`: Recursively follows links through `ShaderNodeMixShader` and `ShaderNodeAddShader` to find the real PBR input.
- `RenderManNodeFactory`: A helper to create nodes with deterministic offsets and set their properties safely.
- `DEFAULT_COLUMN_GAP` & `DEFAULT_ROW_GAP`: Used for node layout to prevent overlapping.

## Testing and modifying

When modifying this plugin:
1. Ensure `utils.py` remains the source of truth for logic.
2. Maintain compatibility with Blender's new extension system (`blender_manifest.toml`).
3. Update tests in `tests/` for any new utility functions and run existing ones:
   - **Utility tests**: Located in `tests/test_utils.py`.
   - **Mocks**: `tests/mock_bpy.py` provides a lightweight Blender API mock for CI/CD or local non-Blender testing.
   - **Blender Testing**: Run the add-on within Blender 4.2+ with the RenderMan plugin enabled.
--- 
**Developer:** Vladimir Fines