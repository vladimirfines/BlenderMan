"""Texture import operator for BlenderMan."""

from __future__ import annotations

import os
from typing import Any

try:
    import bpy  # type: ignore
    from bpy.props import CollectionProperty, StringProperty  # type: ignore
    from bpy_extras.io_utils import ImportHelper  # type: ignore
except ImportError:  # pragma: no cover - Blender-only import
    bpy = None
    CollectionProperty = None
    StringProperty = None
    ImportHelper = object

try:
    from . import utils
except ImportError:  # pragma: no cover - local tests import as top-level module
    import utils  # type: ignore


def _collect_import_paths(operator: Any) -> list[str]:
    directory = getattr(operator, "directory", "") or ""
    files = getattr(operator, "files", ()) or ()
    if files:
        return [
            os.path.join(directory, entry.name)
            for entry in files
            if getattr(entry, "name", "")
        ]
    filepath = getattr(operator, "filepath", "")
    return [filepath] if filepath else []


def import_context_textures(context: Any, operator: Any) -> list[str]:
    """Orchestrate texture import for the current context."""
    utils.ensure_renderman_engine(context)
    node_tree = utils.get_shader_node_tree_from_context(context)
    if node_tree is None:
        return ["ERROR: No active shader node tree found"]

    filepaths = _collect_import_paths(operator)
    return utils.import_textures_as_renderman(node_tree, filepaths)


if bpy is not None:

    class BLENDERMAN_OT_import_textures(bpy.types.Operator, ImportHelper):
        bl_idname = "blenderman.import_textures"
        bl_label = "Import Images as RenderMan Textures"
        bl_options = {"REGISTER", "UNDO"}

        filter_glob: StringProperty(
            default="*.bmp;*.dds;*.exr;*.hdr;*.jpeg;*.jpg;*.png;*.tga;*.tif;*.tiff",
            options={"HIDDEN"},
        )
        files: CollectionProperty(type=bpy.types.OperatorFileListElement)
        directory: StringProperty(subtype="DIR_PATH")

        @classmethod
        def poll(cls, context: Any) -> bool:
            return utils.get_shader_node_tree_from_context(context) is not None

        def execute(self, context: Any) -> set[str]:
            report = import_context_textures(context, self)
            if utils.report_has_errors(report) and not utils.report_has_info(report):
                self.report({"ERROR"}, utils.summarize_report(report))
                return {"CANCELLED"}
            self.report({"INFO"}, utils.summarize_report(report))
            return {"FINISHED"}
else:

    class BLENDERMAN_OT_import_textures:  # pragma: no cover - import-safe fallback
        pass
