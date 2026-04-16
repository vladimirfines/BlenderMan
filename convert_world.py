"""World/HDRI conversion operator for BlenderMan."""

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


def convert_context_world(context: Any) -> list[str]:
    report = utils.make_report()
    world = utils.get_active_world(context)
    return utils.convert_world_hdri(world, report)


if bpy is not None:
    class BLENDERMAN_OT_convert_world(bpy.types.Operator):
        bl_idname = "blenderman.convert_world"
        bl_label = "Convert HDRI Map"
        bl_options = {"REGISTER", "UNDO"}

        @classmethod
        def poll(cls, context: Any) -> bool:
            return utils.context_has_world(context)

        def execute(self, context: Any) -> set[str]:
            report = convert_context_world(context)
            if utils.report_has_errors(report) and not utils.report_has_info(report):
                self.report({"ERROR"}, utils.summarize_report(report))
                return {"CANCELLED"}
            self.report({"INFO"}, utils.summarize_report(report))
            return {"FINISHED"}
else:
    class BLENDERMAN_OT_convert_world:  # pragma: no cover - import-safe fallback
        pass
