"""BlenderMan add-on entry point.

Step 1 of the MVP keeps registration intentionally light while the shared
utility layer is built and tested.
"""

from __future__ import annotations

try:
    import bpy  # type: ignore
except ImportError:  # pragma: no cover - Blender-only import
    bpy = None

try:
    from .convert_material import BLENDERMAN_OT_convert_material
    from .convert_selected_nodes import BLENDERMAN_OT_convert_selected_nodes
    from .convert_world import BLENDERMAN_OT_convert_world
    from .import_textures import BLENDERMAN_OT_import_textures
except ImportError:  # pragma: no cover - import-safe local fallback
    from convert_material import BLENDERMAN_OT_convert_material  # type: ignore
    from convert_selected_nodes import BLENDERMAN_OT_convert_selected_nodes  # type: ignore
    from convert_world import BLENDERMAN_OT_convert_world  # type: ignore
    from import_textures import BLENDERMAN_OT_import_textures  # type: ignore


bl_info = {
    "name": "BlenderMan",
    "author": "OpenAI Codex",
    "version": (0, 1, 0),
    "blender": (4, 3, 0),
    "location": "Shader Editor > Sidebar > RenderMan",
    "description": "Converts common Cycles PBR setups into RenderMan-ready node branches.",
    "category": "Node",
}


CLASSES: tuple[type, ...] = (
    BLENDERMAN_OT_convert_material,
    BLENDERMAN_OT_convert_world,
    BLENDERMAN_OT_convert_selected_nodes,
    BLENDERMAN_OT_import_textures,
)


def register() -> None:
    """Register add-on classes when Blender imports the add-on."""
    if bpy is None:
        return
    for cls in CLASSES:
        bpy.utils.register_class(cls)


def unregister() -> None:
    """Unregister add-on classes in reverse order."""
    if bpy is None:
        return
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)
