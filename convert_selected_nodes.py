"""Selected-node conversion operator for BlenderMan."""

from __future__ import annotations

from typing import Any

try:
    import bpy  # type: ignore
except ImportError:  # pragma: no cover - Blender-only import
    bpy = None

try:
    from . import utils
except ImportError:  # pragma: no cover - local tests import as top-level module
    import utils  # type: ignore


def convert_context_selected_nodes(context: Any) -> list[str]:
    report = utils.make_report()
    node_tree = utils.get_shader_node_tree_from_context(context)
    if node_tree is None:
        utils.report_error(report, "No active shader node tree found")
        return report
    selected_nodes = utils.get_selected_shader_nodes(context)
    return utils.convert_selected_nodes(node_tree, selected_nodes, report)


if bpy is not None:
    class BLENDERMAN_OT_convert_selected_nodes(bpy.types.Operator):
        bl_idname = "blenderman.convert_selected_nodes"
        bl_label = "Convert Selected Nodes"
        bl_options = {"REGISTER", "UNDO"}

        @classmethod
        def poll(cls, context: Any) -> bool:
            return utils.get_shader_node_tree_from_context(context) is not None

        def execute(self, context: Any) -> set[str]:
            report = convert_context_selected_nodes(context)
            self.report({"INFO"}, utils.summarize_report(report))
            return {"FINISHED"}
else:
    class BLENDERMAN_OT_convert_selected_nodes:  # pragma: no cover - import-safe fallback
        pass
