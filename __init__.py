"""BlenderMan add-on entry point.
"""

from __future__ import annotations

from typing import Any

try:
    import bpy  # type: ignore
except ImportError:  # pragma: no cover - Blender-only import
    bpy = None

try:
    from . import utils
    from .convert_material import BLENDERMAN_OT_convert_material
    from .convert_selected_nodes import BLENDERMAN_OT_convert_selected_nodes
    from .convert_world import BLENDERMAN_OT_convert_world
    from .import_textures import BLENDERMAN_OT_import_textures
except ImportError:  # pragma: no cover - import-safe local fallback
    import utils  # type: ignore
    from convert_material import BLENDERMAN_OT_convert_material  # type: ignore
    from convert_selected_nodes import BLENDERMAN_OT_convert_selected_nodes  # type: ignore
    from convert_world import BLENDERMAN_OT_convert_world  # type: ignore
    from import_textures import BLENDERMAN_OT_import_textures  # type: ignore


if bpy is not None:

    class BLENDERMAN_PT_main_panel(bpy.types.Panel):
        """Side-panel UI for the BlenderMan toolset in the Shader Editor."""

        bl_label = "BlenderMan"
        bl_idname = "BLENDERMAN_PT_main_panel"
        bl_space_type = "NODE_EDITOR"
        bl_region_type = "UI"
        bl_category = "Blenderman"

        @classmethod
        def poll(cls, context: Any) -> bool:
            """Only show the panel in the Shader Editor."""
            if context.area.type != "NODE_EDITOR":
                return False
            # Check if it's a shader node tree
            return getattr(context.space_data, "tree_type", "") == "ShaderNodeTree"

        def draw(self, context: Any) -> None:
            """Draw the four distinct MVP buttons."""
            layout = self.layout
            col = layout.column(align=True)

            col.operator("blenderman.convert_material")
            col.operator("blenderman.convert_world")
            col.operator("blenderman.convert_selected_nodes")
            col.operator("blenderman.import_textures")

    class BLENDERMAN_PT_viewport_panel(bpy.types.Panel):
        """Side-panel UI for the BlenderMan toolset in the 3D Viewport."""

        bl_label = "BlenderMan"
        bl_idname = "BLENDERMAN_PT_viewport_panel"
        bl_space_type = "VIEW_3D"
        bl_region_type = "UI"
        bl_category = "Renderman"
        bl_order = 0  # Try to be first

        def draw(self, context: Any) -> None:
            """Draw relevant operators."""
            layout = self.layout
            col = layout.column(align=True)

            col.operator("blenderman.convert_material")
            col.operator("blenderman.convert_world")


CLASSES: tuple[type, ...] = (
    BLENDERMAN_OT_convert_material,
    BLENDERMAN_OT_convert_world,
    BLENDERMAN_OT_convert_selected_nodes,
    BLENDERMAN_OT_import_textures,
)
if bpy is not None:
    CLASSES += (BLENDERMAN_PT_main_panel, BLENDERMAN_PT_viewport_panel)


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
