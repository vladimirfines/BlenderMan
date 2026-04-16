"""Shared helpers for the BlenderMan add-on.

The module is import-safe outside Blender so the pure graph logic can be tested
locally. Functions that need a live Blender/Renderman environment fail with a
clear error when the required node types are unavailable.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Any, Iterable, Iterator, Optional, Sequence

try:
    import bpy  # type: ignore
except ImportError:  # pragma: no cover - Blender-only import
    bpy = None


LOGGER_NAME = "Blenderman"
DEFAULT_COLUMN_GAP = 260
DEFAULT_ROW_GAP = 140

NODE_TYPE_MAP = {
    "ShaderNodeTexImage": "PxrTexture",
    "ShaderNodeNormalMap": "PxrNormalMap",
    "ShaderNodeBump": "PxrBump",
    "ShaderNodeDisplacement": "PxrDisplace",
    "ShaderNodeBsdfPrincipled": "PxrSurface",
    "ShaderNodeOutputMaterial": "RendermanOutputNode",
}

SOCKET_NAME_MAP = {
    "Base Color": "diffuseColor",
    "Subsurface": "subsurfaceGain",
    "Subsurface Radius": "subsurfaceRadius",
    "Metallic": "specularFaceColor",
    "Specular IOR Level": "specularIor",
    "Roughness": "specularRoughness",
    "Emission Color": "emitColor",
    "Emission Strength": "emitGain",
    "Alpha": "presence",
    "Normal": "bumpNormal",
    "Height": "inputBump",
    "Displacement": "dispScalar",
}

COLOR_INPUT_NAMES = {
    "Base Color",
    "Emission Color",
}

DATA_INPUT_NAMES = {
    "Alpha",
    "Height",
    "Metallic",
    "Normal",
    "Roughness",
    "Specular IOR Level",
    "Subsurface",
    "Subsurface Radius",
}

IMAGE_EXTENSIONS = {
    ".bmp",
    ".dds",
    ".exr",
    ".hdr",
    ".jpeg",
    ".jpg",
    ".png",
    ".tga",
    ".tif",
    ".tiff",
}


def get_logger(name: str = LOGGER_NAME) -> logging.Logger:
    """Return a configured module logger."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("[%(name)s] %(levelname)s: %(message)s"))
        logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    logger.propagate = False
    return logger


logger = get_logger()


class RendermanNodeError(RuntimeError):
    """Raised when a required RenderMan node type is unavailable."""


def log_debug(message: str, *args: Any) -> None:
    logger.debug(message, *args)


def classify_input_socket(socket_name: str) -> str:
    """Classify a Principled input as either color or data."""
    if socket_name in COLOR_INPUT_NAMES:
        return "color"
    return "data"


def map_rm_node_type(blender_node_type: str) -> Optional[str]:
    return NODE_TYPE_MAP.get(blender_node_type)


def map_rm_socket_name(socket_name: str) -> Optional[str]:
    return SOCKET_NAME_MAP.get(socket_name)


def ensure_nodes_enabled(owner: Any) -> Any:
    """Enable nodes on a material/world-like owner and return its node tree."""
    if getattr(owner, "use_nodes", False) is False:
        log_debug("Enabling nodes for %s", getattr(owner, "name", owner))
        owner.use_nodes = True
    node_tree = getattr(owner, "node_tree", None)
    if node_tree is None:
        raise ValueError(f"{owner!r} does not expose a node_tree")
    return node_tree


def is_supported_image_file(filepath: str) -> bool:
    return os.path.splitext(filepath)[1].lower() in IMAGE_EXTENSIONS


def iter_material_slots(objects: Iterable[Any]) -> Iterator[Any]:
    for obj in objects:
        for slot in getattr(obj, "material_slots", ()) or ():
            material = getattr(slot, "material", None)
            if material is not None:
                yield material


def collect_unique_materials(objects: Iterable[Any]) -> list[Any]:
    """Collect unique material datablocks from objects with material slots."""
    unique_by_id: dict[int, Any] = {}
    for material in iter_material_slots(objects):
        unique_by_id.setdefault(id(material), material)
    materials = list(unique_by_id.values())
    log_debug("Collected %d unique materials", len(materials))
    return materials


def get_context_objects(context: Any) -> list[Any]:
    selected_objects = list(getattr(context, "selected_objects", ()) or ())
    if selected_objects:
        return selected_objects
    active_object = getattr(context, "active_object", None)
    return [active_object] if active_object is not None else []


def context_has_convertible_materials(context: Any) -> bool:
    return bool(collect_unique_materials(get_context_objects(context)))


def context_has_world(context: Any) -> bool:
    return get_active_world(context) is not None


def find_nodes_by_type(node_tree: Any, bl_idname: str) -> list[Any]:
    return [node for node in getattr(node_tree, "nodes", ()) if getattr(node, "bl_idname", None) == bl_idname]


def find_first_node_by_type(node_tree: Any, bl_idname: str) -> Optional[Any]:
    for node in getattr(node_tree, "nodes", ()):
        if getattr(node, "bl_idname", None) == bl_idname:
            return node
    return None


def find_material_output(node_tree: Any, target: str = "ALL") -> Optional[Any]:
    for node in find_nodes_by_type(node_tree, "ShaderNodeOutputMaterial"):
        if getattr(node, "is_active_output", True) and target in {"ALL", getattr(node, "target", "ALL")}:
            return node
    outputs = find_nodes_by_type(node_tree, "ShaderNodeOutputMaterial")
    return outputs[0] if outputs else None


def find_world_output(node_tree: Any) -> Optional[Any]:
    return find_first_node_by_type(node_tree, "ShaderNodeOutputWorld")


def find_environment_texture(node_tree: Any) -> Optional[Any]:
    background = find_first_node_by_type(node_tree, "ShaderNodeBackground")
    if background is not None:
        color_socket = get_input_socket(background, "Color")
        source = trace_socket_source(color_socket) if color_socket is not None else None
        if source and getattr(source[0], "bl_idname", None) == "ShaderNodeTexEnvironment":
            return source[0]
    return find_first_node_by_type(node_tree, "ShaderNodeTexEnvironment")


def get_input_socket(node: Any, socket_name: str) -> Optional[Any]:
    inputs = getattr(node, "inputs", None)
    if inputs is None:
        return None
    if hasattr(inputs, "get"):
        return inputs.get(socket_name)
    for socket in inputs:
        if getattr(socket, "name", None) == socket_name:
            return socket
    return None


def get_output_socket(node: Any, socket_name: str) -> Optional[Any]:
    outputs = getattr(node, "outputs", None)
    if outputs is None:
        return None
    if hasattr(outputs, "get"):
        return outputs.get(socket_name)
    for socket in outputs:
        if getattr(socket, "name", None) == socket_name:
            return socket
    return None


def get_primary_link(socket: Any) -> Optional[Any]:
    links = list(getattr(socket, "links", ()) or ())
    return links[0] if links else None


def trace_socket_source(socket: Any) -> Optional[tuple[Any, Any]]:
    """Return the upstream node/socket pair for a linked input socket."""
    link = get_primary_link(socket)
    if link is None:
        return None
    return getattr(link, "from_node", None), getattr(link, "from_socket", None)


def get_linked_input_sockets(node: Any) -> list[Any]:
    inputs = getattr(node, "inputs", ())
    if hasattr(inputs, "values"):
        sockets = list(inputs.values())
    else:
        sockets = list(inputs)
    return [socket for socket in sockets if getattr(socket, "links", None)]


def trace_input_chain(socket: Any, max_depth: int = 32) -> list[Any]:
    """Walk upstream through first links and return the visited nodes."""
    chain: list[Any] = []
    current_socket = socket
    steps = 0
    while current_socket is not None and steps < max_depth:
        source = trace_socket_source(current_socket)
        if source is None:
            break
        source_node, source_socket = source
        if source_node is None:
            break
        chain.append(source_node)
        linked_inputs = get_linked_input_sockets(source_node)
        current_socket = linked_inputs[0] if linked_inputs else None
        steps += 1
    return chain


def find_linked_principled(node_tree: Any) -> Optional[Any]:
    """Prefer the Principled BSDF connected to the active material output."""
    output = find_material_output(node_tree)
    if output is not None:
        surface_socket = get_input_socket(output, "Surface")
        source = trace_socket_source(surface_socket) if surface_socket else None
        if source and getattr(source[0], "bl_idname", None) == "ShaderNodeBsdfPrincipled":
            return source[0]
    return find_first_node_by_type(node_tree, "ShaderNodeBsdfPrincipled")


def create_renderman_node(
    node_tree: Any,
    blender_node: Optional[Any] = None,
    rm_node_type: Optional[str] = None,
    name_prefix: str = "RM",
) -> Any:
    """Create a RenderMan node from an explicit type or a Blender node mapping."""
    source_type = getattr(blender_node, "bl_idname", None) if blender_node is not None else None
    resolved_type = rm_node_type or map_rm_node_type(source_type or "")
    if not resolved_type:
        raise ValueError(f"Unsupported Blender node type: {source_type!r}")

    log_debug("Creating RenderMan node %s from %s", resolved_type, source_type or resolved_type)
    try:
        node = node_tree.nodes.new(resolved_type)
    except RuntimeError as exc:
        raise RendermanNodeError(
            f"RenderMan node type {resolved_type} is unavailable. Ensure the RenderMan add-on is enabled and exposes this node."
        ) from exc
    source_name = getattr(blender_node, "name", resolved_type)
    node.name = f"{name_prefix} {source_name}"
    node.label = node.name
    return node


def set_texture_colorspace(texture_node: Any, input_name: str) -> None:
    """Apply the RenderMan data-vs-color colorspace hint when supported."""
    classification = classify_input_socket(input_name)
    if hasattr(texture_node, "filename_colorspace"):
        texture_node.filename_colorspace = "data" if classification == "data" else "srgb"


def link_sockets(node_tree: Any, from_socket: Any, to_socket: Any) -> Any:
    if from_socket is None or to_socket is None:
        raise ValueError("Both from_socket and to_socket are required")
    return node_tree.links.new(from_socket, to_socket)


def set_attr_if_present(target: Any, attr_name: str, value: Any) -> bool:
    if hasattr(target, attr_name):
        setattr(target, attr_name, value)
        return True
    try:
        setattr(target, attr_name, value)
    except (AttributeError, TypeError):
        return False
    else:
        return True


def set_first_supported_attr(target: Any, attr_names: Sequence[str], value: Any) -> Optional[str]:
    for attr_name in attr_names:
        if set_attr_if_present(target, attr_name, value):
            return attr_name
    return None


def copy_image_path(source_node: Any, target_node: Any) -> Optional[str]:
    image = getattr(source_node, "image", None)
    image_path = getattr(image, "filepath", None) if image is not None else None
    image_path = image_path or getattr(source_node, "filepath", None)
    if not image_path:
        return None
    set_first_supported_attr(target_node, ("filename", "lightColorMap", "filepath"), image_path)
    return image_path


def copy_default_value(source_socket: Any, target_socket: Any) -> bool:
    if source_socket is None or target_socket is None:
        return False
    if not hasattr(source_socket, "default_value") or not hasattr(target_socket, "default_value"):
        return False
    target_socket.default_value = source_socket.default_value
    return True


def _coerce_location(location: Any) -> tuple[float, float]:
    if location is None:
        return (0.0, 0.0)
    if hasattr(location, "x") and hasattr(location, "y"):
        return (float(location.x), float(location.y))
    if isinstance(location, (tuple, list)) and len(location) >= 2:
        return (float(location[0]), float(location[1]))
    return (0.0, 0.0)


def place_relative(node: Any, source_node: Any, x_offset: float = 320.0, y_offset: float = 0.0) -> None:
    source_x, source_y = _coerce_location(getattr(source_node, "location", None))
    node.location = (source_x + x_offset, source_y + y_offset)


def _append_report(report: list[str], level: str, message: str) -> str:
    entry = f"{level}: {message}"
    report.append(entry)
    log_debug("%s", entry)
    return entry


def report_info(report: list[str], message: str) -> str:
    return _append_report(report, "INFO", message)


def report_error(report: list[str], message: str) -> str:
    return _append_report(report, "ERROR", message)


def summarize_report(report: Sequence[str]) -> str:
    errors = sum(1 for entry in report if entry.startswith("ERROR:"))
    infos = sum(1 for entry in report if entry.startswith("INFO:"))
    if not report:
        return "No changes made."
    if errors and infos:
        return f"{infos} actions completed, {errors} issues reported."
    if errors:
        return f"{errors} issues reported."
    return f"{infos or len(report)} actions completed."


def report_has_errors(report: Sequence[str]) -> bool:
    return any(entry.startswith("ERROR:") for entry in report)


def report_has_info(report: Sequence[str]) -> bool:
    return any(entry.startswith("INFO:") for entry in report)


def get_selected_shader_nodes(context: Any) -> list[Any]:
    selected_nodes = getattr(context, "selected_nodes", None)
    if selected_nodes is not None:
        return list(selected_nodes)
    space_data = getattr(context, "space_data", None)
    node_tree = getattr(space_data, "node_tree", None)
    if node_tree is None:
        return []
    return [node for node in getattr(node_tree, "nodes", ()) if getattr(node, "select", False)]


def get_shader_node_tree_from_context(context: Any) -> Optional[Any]:
    space_data = getattr(context, "space_data", None)
    return getattr(space_data, "node_tree", None)


def get_active_world(context: Any) -> Any:
    scene = getattr(context, "scene", None)
    return getattr(scene, "world", None)


def _get_socket_default_or_value(socket: Any) -> Any:
    if socket is None:
        return None
    if hasattr(socket, "default_value"):
        return socket.default_value
    return None


def _copy_principled_defaults(principled: Any, rm_shader: Any) -> None:
    for source_name, target_name in SOCKET_NAME_MAP.items():
        source_socket = get_input_socket(principled, source_name)
        target_socket = get_input_socket(rm_shader, target_name)
        if not copy_default_value(source_socket, target_socket):
            value = _get_socket_default_or_value(source_socket)
            if value is not None:
                set_attr_if_present(rm_shader, target_name, value)


def _link_if_sockets_exist(node_tree: Any, from_node: Any, from_name: str, to_node: Any, to_name: str) -> bool:
    from_socket = get_output_socket(from_node, from_name)
    to_socket = get_input_socket(to_node, to_name)
    if from_socket is None or to_socket is None:
        return False
    link_sockets(node_tree, from_socket, to_socket)
    return True


def _convert_image_source(
    node_tree: Any,
    source_node: Any,
    target_node: Any,
    target_input_name: str,
    report: list[str],
    texture_nodes: list[Any],
) -> bool:
    try:
        rm_texture = create_renderman_node(node_tree, blender_node=source_node)
    except RendermanNodeError as exc:
        report_error(report, str(exc))
        return False
    copy_image_path(source_node, rm_texture)
    set_texture_colorspace(rm_texture, target_input_name)
    place_relative(rm_texture, source_node, x_offset=320.0)
    linked = _link_if_sockets_exist(node_tree, rm_texture, "resultRGB", target_node, target_input_name)
    if not linked:
        linked = _link_if_sockets_exist(node_tree, rm_texture, "resultA", target_node, target_input_name)
    texture_nodes.append(rm_texture)
    if not linked:
        report_error(report, f"Could not wire RenderMan texture into {target_input_name}")
        return False
    return True


def _convert_normal_source(
    node_tree: Any,
    source_node: Any,
    target_node: Any,
    report: list[str],
    texture_nodes: list[Any],
    utility_nodes: list[Any],
) -> bool:
    if getattr(source_node, "bl_idname", None) == "ShaderNodeNormalMap":
        try:
            rm_normal = create_renderman_node(node_tree, blender_node=source_node)
        except RendermanNodeError as exc:
            report_error(report, str(exc))
            return False
        color_socket = get_input_socket(source_node, "Color")
        color_source = trace_socket_source(color_socket) if color_socket is not None else None
        if color_source and getattr(color_source[0], "bl_idname", None) == "ShaderNodeTexImage":
            try:
                rm_texture = create_renderman_node(node_tree, blender_node=color_source[0])
            except RendermanNodeError as exc:
                report_error(report, str(exc))
                return False
            copy_image_path(color_source[0], rm_texture)
            set_texture_colorspace(rm_texture, "Normal")
            _link_if_sockets_exist(node_tree, rm_texture, "resultRGB", rm_normal, "inputRGB")
            texture_nodes.append(rm_texture)
            place_relative(rm_texture, color_source[0], x_offset=320.0)
        place_relative(rm_normal, source_node, x_offset=320.0)
        utility_nodes.append(rm_normal)
        if not _link_if_sockets_exist(node_tree, rm_normal, "resultN", target_node, "bumpNormal"):
            report_error(report, "Could not wire RenderMan normal map into bumpNormal")
            return False
        return True

    if getattr(source_node, "bl_idname", None) == "ShaderNodeBump":
        try:
            rm_bump = create_renderman_node(node_tree, blender_node=source_node)
        except RendermanNodeError as exc:
            report_error(report, str(exc))
            return False
        height_socket = get_input_socket(source_node, "Height")
        height_source = trace_socket_source(height_socket) if height_socket is not None else None
        if height_source and getattr(height_source[0], "bl_idname", None) == "ShaderNodeTexImage":
            try:
                rm_texture = create_renderman_node(node_tree, blender_node=height_source[0])
            except RendermanNodeError as exc:
                report_error(report, str(exc))
                return False
            copy_image_path(height_source[0], rm_texture)
            set_texture_colorspace(rm_texture, "Height")
            _link_if_sockets_exist(node_tree, rm_texture, "resultA", rm_bump, "inputBump")
            texture_nodes.append(rm_texture)
            place_relative(rm_texture, height_source[0], x_offset=320.0)
        place_relative(rm_bump, source_node, x_offset=320.0)
        utility_nodes.append(rm_bump)
        if not _link_if_sockets_exist(node_tree, rm_bump, "resultN", target_node, "bumpNormal"):
            report_error(report, "Could not wire RenderMan bump node into bumpNormal")
            return False
        return True

    report_unsupported(report, f"Unsupported normal source node: {getattr(source_node, 'bl_idname', 'unknown')}")
    return False


def convert_principled_material(material: Any, report: Optional[list[str]] = None) -> list[str]:
    if report is None:
        report = make_report()
    node_tree = ensure_nodes_enabled(material)
    principled = find_linked_principled(node_tree)
    if principled is None:
        report_error(report, f"{getattr(material, 'name', 'Material')}: no Principled BSDF found")
        return report

    try:
        rm_shader = create_renderman_node(node_tree, blender_node=principled)
        rm_output = create_renderman_node(node_tree, rm_node_type="RendermanOutputNode", name_prefix="RM")
    except RendermanNodeError as exc:
        report_error(report, f"{getattr(material, 'name', 'Material')}: {exc}")
        return report
    _copy_principled_defaults(principled, rm_shader)
    _link_if_sockets_exist(node_tree, rm_shader, "bxdf_out", rm_output, "bxdf_in")

    texture_nodes: list[Any] = []
    utility_nodes: list[Any] = []
    handled_inputs = ("Base Color", "Roughness", "Metallic")

    for input_name in handled_inputs:
        source_socket = get_input_socket(principled, input_name)
        source = trace_socket_source(source_socket) if source_socket is not None else None
        if source is None:
            continue
        source_node, _ = source
        if getattr(source_node, "bl_idname", None) != "ShaderNodeTexImage":
            report_unsupported(report, f"{getattr(material, 'name', 'Material')}: unsupported source for {input_name}")
            continue
        target_input = map_rm_socket_name(input_name)
        if target_input is None:
            continue
        _convert_image_source(node_tree, source_node, rm_shader, target_input, report, texture_nodes)

    normal_socket = get_input_socket(principled, "Normal")
    normal_source = trace_socket_source(normal_socket) if normal_socket is not None else None
    if normal_source is not None:
        _convert_normal_source(node_tree, normal_source[0], rm_shader, report, texture_nodes, utility_nodes)

    origin_x, origin_y = _coerce_location(getattr(principled, "location", None))
    layout_renderman_branch(
        texture_nodes,
        utility_nodes,
        rm_shader,
        rm_output,
        origin=(origin_x, origin_y - 360.0),
    )
    report_info(report, f"{getattr(material, 'name', 'Material')}: created RenderMan material branch")
    return report


def convert_selected_nodes(
    node_tree: Any,
    selected_nodes: Sequence[Any],
    report: Optional[list[str]] = None,
) -> list[str]:
    if report is None:
        report = make_report()
    converted = 0
    for source_node in selected_nodes:
        if map_rm_node_type(getattr(source_node, "bl_idname", "")) is None:
            report_unsupported(report, f"Selected node not supported: {getattr(source_node, 'name', source_node)}")
            continue
        try:
            rm_node = create_renderman_node(node_tree, blender_node=source_node)
        except RendermanNodeError as exc:
            report_error(report, str(exc))
            continue
        copy_image_path(source_node, rm_node)
        if getattr(source_node, "bl_idname", None) == "ShaderNodeTexImage":
            set_texture_colorspace(rm_node, "Base Color")
        place_relative(rm_node, source_node, x_offset=320.0)
        converted += 1
    if converted == 0:
        report_error(report, "No supported selected nodes were converted")
        return report
    report_info(report, f"Converted {converted} selected node(s) into RenderMan nodes")
    return report


def convert_world_hdri(world: Any, report: Optional[list[str]] = None) -> list[str]:
    if report is None:
        report = make_report()
    if world is None:
        report_error(report, "Scene has no world to convert")
        return report

    node_tree = ensure_nodes_enabled(world)
    environment = find_environment_texture(node_tree)
    if environment is None:
        report_error(report, f"{getattr(world, 'name', 'World')}: no environment texture found")
        return report

    try:
        dome = create_renderman_node(node_tree, rm_node_type="PxrDomeLight", name_prefix="RM")
    except RendermanNodeError as exc:
        report_error(report, f"{getattr(world, 'name', 'World')}: {exc}")
        return report
    image_path = copy_image_path(environment, dome)
    if image_path:
        set_first_supported_attr(dome, ("lightColorMap", "filename", "filepath"), image_path)
    mapping = find_first_node_by_type(node_tree, "ShaderNodeMapping")
    rotation = None
    if mapping is not None:
        rotation_socket = get_input_socket(mapping, "Rotation")
        rotation = _get_socket_default_or_value(rotation_socket)
    if rotation is not None:
        set_first_supported_attr(dome, ("lightRotation", "orientation", "rotation"), rotation)
    place_relative(dome, environment, x_offset=420.0)
    if image_path:
        report_info(report, f"{getattr(world, 'name', 'World')}: created RenderMan dome light for {image_path}")
    else:
        report_info(report, f"{getattr(world, 'name', 'World')}: created RenderMan dome light")
    return report


def import_textures_as_renderman(
    node_tree: Any,
    filepaths: Sequence[str],
    report: Optional[list[str]] = None,
) -> list[str]:
    if report is None:
        report = make_report()
    imported_nodes: list[Any] = []
    for filepath in filepaths:
        if not is_supported_image_file(filepath):
            report_error(report, f"Skipped non-image file: {filepath}")
            continue
        try:
            texture = create_renderman_node(node_tree, rm_node_type="PxrTexture", name_prefix="RM")
        except RendermanNodeError as exc:
            report_error(report, str(exc))
            break
        set_first_supported_attr(texture, ("filename", "filepath"), filepath)
        imported_nodes.append(texture)
    if not imported_nodes:
        report_error(report, "No images were imported as RenderMan textures")
        return report
    layout_renderman_branch(imported_nodes, [], None, None, origin=(0.0, 0.0))
    report_info(report, f"Imported {len(imported_nodes)} image(s) as RenderMan textures")
    return report


def _node_height(node: Any, default: float = 100.0) -> float:
    dimensions = getattr(node, "dimensions", None)
    if dimensions and len(dimensions) > 1:
        return float(dimensions[1]) or default
    return float(getattr(node, "height", default) or default)


def place_column(nodes: Sequence[Any], x: float, y_start: float, y_step: float = DEFAULT_ROW_GAP) -> None:
    y = y_start
    for node in nodes:
        node.location = (x, y)
        y -= max(y_step, _node_height(node) + 20)


def layout_renderman_branch(
    texture_nodes: Sequence[Any],
    utility_nodes: Sequence[Any],
    shader_node: Optional[Any],
    output_node: Optional[Any],
    origin: tuple[float, float] = (0.0, 0.0),
    column_gap: float = DEFAULT_COLUMN_GAP,
    row_gap: float = DEFAULT_ROW_GAP,
) -> None:
    """Lay out the additive RenderMan branch in deterministic columns."""
    origin_x, origin_y = origin
    place_column(texture_nodes, origin_x, origin_y, row_gap)
    place_column(utility_nodes, origin_x + column_gap, origin_y, row_gap)
    if shader_node is not None:
        shader_node.location = (origin_x + (column_gap * 2), origin_y)
    if output_node is not None:
        output_node.location = (origin_x + (column_gap * 3), origin_y)


def report_unsupported(report: list[str], message: str) -> None:
    report.append(message)
    log_debug("Unsupported: %s", message)


def make_report() -> list[str]:
    return []


@dataclass
class FakeSocket:
    name: str
    node: Any | None = None
    links: list[Any] = field(default_factory=list)


@dataclass
class FakeLink:
    from_socket: FakeSocket
    to_socket: FakeSocket

    @property
    def from_node(self) -> Any | None:
        return self.from_socket.node

    @property
    def to_node(self) -> Any | None:
        return self.to_socket.node


class FakeSocketMap(dict):
    def __iter__(self) -> Iterator[FakeSocket]:
        return iter(self.values())


class FakeNode:
    def __init__(
        self,
        bl_idname: str,
        name: Optional[str] = None,
        inputs: Optional[Sequence[str]] = None,
        outputs: Optional[Sequence[str]] = None,
    ) -> None:
        self.bl_idname = bl_idname
        self.name = name or bl_idname
        self.label = self.name
        self.inputs = FakeSocketMap({socket_name: FakeSocket(socket_name, self) for socket_name in inputs or ()})
        self.outputs = FakeSocketMap({socket_name: FakeSocket(socket_name, self) for socket_name in outputs or ()})
        self.location = (0.0, 0.0)
        self.dimensions = (160.0, 100.0)
        self.is_active_output = True
        self.target = "ALL"


class FakeNodeCollection(list):
    def new(self, bl_idname: str) -> FakeNode:
        default_sockets = {
            "ShaderNodeTexImage": ((), ("Color", "Alpha")),
            "ShaderNodeTexEnvironment": ((), ("Color",)),
            "ShaderNodeBackground": (("Color", "Strength"), ("Background",)),
            "ShaderNodeMapping": (("Vector", "Location", "Rotation", "Scale"), ("Vector",)),
            "ShaderNodeNormalMap": (("Color",), ("Normal",)),
            "ShaderNodeBump": (("Height", "Normal"), ("Normal",)),
            "ShaderNodeBsdfPrincipled": (
                ("Base Color", "Roughness", "Metallic", "Normal"),
                ("BSDF",),
            ),
            "ShaderNodeOutputMaterial": (("Surface", "Displacement"), ()),
            "ShaderNodeOutputWorld": (("Surface",), ()),
            "PxrTexture": ((), ("resultRGB", "resultA")),
            "PxrNormalMap": (("inputRGB",), ("resultN",)),
            "PxrBump": (("inputBump", "inputN"), ("resultN",)),
            "PxrSurface": (
                ("diffuseColor", "specularRoughness", "specularFaceColor", "bumpNormal"),
                ("bxdf_out",),
            ),
            "RendermanOutputNode": (("bxdf_in", "displace_in"), ()),
            "PxrDisplace": (("dispScalar",), ("displace_out",)),
            "PxrDomeLight": ((), ()),
        }
        inputs, outputs = default_sockets.get(bl_idname, ((), ()))
        node = FakeNode(bl_idname, inputs=inputs, outputs=outputs)
        self.append(node)
        return node


class FakeLinkCollection(list):
    def new(self, from_socket: FakeSocket, to_socket: FakeSocket) -> FakeLink:
        link = FakeLink(from_socket=from_socket, to_socket=to_socket)
        self.append(link)
        from_socket.links.append(link)
        to_socket.links.append(link)
        return link


class FakeNodeTree:
    def __init__(self) -> None:
        self.nodes = FakeNodeCollection()
        self.links = FakeLinkCollection()


def build_fake_material_tree() -> SimpleNamespace:
    """Create a Node Wrangler-like test graph for local tests."""
    node_tree = FakeNodeTree()
    image = node_tree.nodes.new("ShaderNodeTexImage")
    image.name = "Base Color"
    principled = node_tree.nodes.new("ShaderNodeBsdfPrincipled")
    output = node_tree.nodes.new("ShaderNodeOutputMaterial")
    node_tree.links.new(image.outputs["Color"], principled.inputs["Base Color"])
    node_tree.links.new(principled.outputs["BSDF"], output.inputs["Surface"])
    return SimpleNamespace(use_nodes=True, node_tree=node_tree, name="TestMaterial")


def build_fake_world_tree() -> SimpleNamespace:
    node_tree = FakeNodeTree()
    environment = node_tree.nodes.new("ShaderNodeTexEnvironment")
    environment.image = SimpleNamespace(filepath="/tmp/sky.hdr")
    background = node_tree.nodes.new("ShaderNodeBackground")
    output = node_tree.nodes.new("ShaderNodeOutputWorld")
    mapping = node_tree.nodes.new("ShaderNodeMapping")
    mapping.inputs["Rotation"].default_value = (0.0, 0.5, 1.0)
    node_tree.links.new(environment.outputs["Color"], background.inputs["Color"])
    node_tree.links.new(background.outputs["Background"], output.inputs["Surface"])
    return SimpleNamespace(use_nodes=True, node_tree=node_tree, name="TestWorld")
