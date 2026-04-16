"""Material conversion operator for BlenderMan."""

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


def convert_context_materials(context: Any) -> list[str]:
    report = utils.make_report()
    materials = utils.collect_unique_materials(utils.get_context_objects(context))
    if not materials:
        utils.report_error(report, "No materials found on selected objects")
        return report

    for material in materials:
        utils.convert_principled_material(material, report)
    return report


if bpy is not None:
    class BLENDERMAN_OT_convert_material(bpy.types.Operator):
        bl_idname = "blenderman.convert_material"
        bl_label = "Convert PBR Material"
        bl_options = {"REGISTER", "UNDO"}

        @classmethod
        def poll(cls, context: Any) -> bool:
            return utils.context_has_convertible_materials(context)

        def execute(self, context: Any) -> set[str]:
            report = convert_context_materials(context)
            if utils.report_has_errors(report) and not utils.report_has_info(report):
                self.report({"ERROR"}, utils.summarize_report(report))
                return {"CANCELLED"}
            self.report({"INFO"}, utils.summarize_report(report))
            return {"FINISHED"}
else:
    class BLENDERMAN_OT_convert_material:  # pragma: no cover - import-safe fallback
        pass
