"""Shared helpers for the BlenderMan add-on.

The module is import-safe outside Blender so the pure graph logic can be tested
locally. Functions that need a live Blender/Renderman environment fail with a
clear error when the required node types are unavailable.
"""

from __future__ import annotations

import logging
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
    node = node_tree.nodes.new(resolved_type)
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
            "ShaderNodeNormalMap": (("Color",), ("Normal",)),
            "ShaderNodeBump": (("Height", "Normal"), ("Normal",)),
            "ShaderNodeBsdfPrincipled": (
                ("Base Color", "Roughness", "Metallic", "Normal"),
                ("BSDF",),
            ),
            "ShaderNodeOutputMaterial": (("Surface", "Displacement"), ()),
            "PxrTexture": ((), ("resultRGB", "resultA")),
            "PxrNormalMap": (("inputRGB",), ("resultN",)),
            "PxrBump": (("inputBump", "inputN"), ("resultN",)),
            "PxrSurface": (
                ("diffuseColor", "specularRoughness", "specularFaceColor", "bumpNormal"),
                ("bxdf_out",),
            ),
            "RendermanOutputNode": (("bxdf_in", "displace_in"), ()),
            "PxrDisplace": (("dispScalar",), ("displace_out",)),
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
