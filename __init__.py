"""BlenderMan add-on entry point.

Step 1 of the MVP keeps registration intentionally light while the shared
utility layer is built and tested.
"""

from __future__ import annotations

try:
    import bpy  # type: ignore
except ImportError:  # pragma: no cover - Blender-only import
    bpy = None


bl_info = {
    "name": "BlenderMan",
    "author": "OpenAI Codex",
    "version": (0, 1, 0),
    "blender": (4, 3, 0),
    "location": "Shader Editor > Sidebar > RenderMan",
    "description": "Converts common Cycles PBR setups into RenderMan-ready node branches.",
    "category": "Node",
}


CLASSES: tuple[type, ...] = ()


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
