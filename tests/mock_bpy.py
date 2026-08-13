"""Mock Blender objects for local tests."""

from __future__ import annotations

from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Any, Iterator, Optional, Sequence


@dataclass
class FakeSocket:
    name: str
    node: Any | None = None
    links: list[Any] = field(default_factory=list)

    @property
    def default_value(self) -> Any:
        return getattr(self, "_default_value", (0.0, 0.0, 0.0, 1.0))

    @default_value.setter
    def default_value(self, value: Any) -> None:
        self._default_value = value


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
        **extra_attrs: Any,
    ) -> None:
        self.bl_idname = bl_idname
        self.name = name or bl_idname
        self.label = self.name
        self.inputs = FakeSocketMap(
            {socket_name: FakeSocket(socket_name, self) for socket_name in inputs or ()}
        )
        self.outputs = FakeSocketMap(
            {
                socket_name: FakeSocket(socket_name, self)
                for socket_name in outputs or ()
            }
        )
        self.location = (0.0, 0.0)
        self.dimensions = (160.0, 100.0)
        self.is_active_output = True
        self.target = "ALL"
        self.select = False
        for key, value in extra_attrs.items():
            setattr(self, key, value)


class FakeNodeCollection(list):
    def new(self, bl_idname: str) -> FakeNode:
        default_sockets = {
            "ShaderNodeTexImage": ((), ("Color", "Alpha")),
            "ShaderNodeTexEnvironment": ((), ("Color",)),
            "ShaderNodeBackground": (("Color", "Strength"), ("Background",)),
            "ShaderNodeMapping": (
                ("Vector", "Location", "Rotation", "Scale"),
                ("Vector",),
            ),
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
            "PxrDisneyBsdf": (
                (
                    "baseColor",
                    "roughness",
                    "metallic",
                    "specular",
                    "specularPedestal",
                    "roughnessAnisotropy",
                    "roughnessAzimuth",
                    "metallic",
                    "emission",
                    "emissionColor",
                    "subsurface",
                    "subsurfaceColor",
                    "subsurfaceScale",
                    "cutoutOpacity",
                    "bumpNormal",
                    "enableSubsurface",
                ),
                ("bxdf_out",),
            ),
            "RendermanOutputNode": (("bxdf_in", "displace_in"), ()),
            "PxrDisplace": (("dispScalar",), ("displace_out",)),
            "PxrDomeLight": ((), ()),
        }
        inputs, outputs = default_sockets.get(bl_idname, ((), ()))
        extra = {}
        if bl_idname == "PxrDomeLight":
            extra = {"lightColorMap": "", "lightRotation": (0.0, 0.0, 0.0)}
        node = FakeNode(bl_idname, inputs=inputs, outputs=outputs, **extra)
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
