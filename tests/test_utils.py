from __future__ import annotations

import unittest
from types import SimpleNamespace

import utils


class UtilsTests(unittest.TestCase):
    def test_collect_unique_materials_deduplicates_instances(self) -> None:
        material = SimpleNamespace(name="Mat")
        obj_a = SimpleNamespace(material_slots=[SimpleNamespace(material=material)])
        obj_b = SimpleNamespace(material_slots=[SimpleNamespace(material=material)])

        materials = utils.collect_unique_materials([obj_a, obj_b])

        self.assertEqual(materials, [material])

    def test_find_linked_principled_prefers_output_chain(self) -> None:
        material = utils.build_fake_material_tree()

        principled = utils.find_linked_principled(material.node_tree)

        self.assertIsNotNone(principled)
        self.assertEqual(principled.bl_idname, "ShaderNodeBsdfPrincipled")

    def test_trace_input_chain_walks_upstream_nodes(self) -> None:
        material = utils.build_fake_material_tree()
        principled = utils.find_linked_principled(material.node_tree)

        chain = utils.trace_input_chain(principled.inputs["Base Color"])

        self.assertEqual([node.bl_idname for node in chain], ["ShaderNodeTexImage"])

    def test_create_renderman_node_uses_mapping_table(self) -> None:
        node_tree = utils.FakeNodeTree()
        source_node = utils.FakeNode("ShaderNodeTexImage", name="Albedo", outputs=("Color",))

        node = utils.create_renderman_node(node_tree, blender_node=source_node)

        self.assertEqual(node.bl_idname, "PxrTexture")
        self.assertEqual(node.name, "RM Albedo")

    def test_layout_renderman_branch_places_columns_deterministically(self) -> None:
        node_tree = utils.FakeNodeTree()
        tex_a = node_tree.nodes.new("PxrTexture")
        tex_b = node_tree.nodes.new("PxrTexture")
        utility = node_tree.nodes.new("PxrNormalMap")
        shader = node_tree.nodes.new("PxrSurface")
        output = node_tree.nodes.new("RendermanOutputNode")

        utils.layout_renderman_branch([tex_a, tex_b], [utility], shader, output, origin=(10, 20))

        self.assertEqual(tex_a.location, (10, 20))
        self.assertEqual(tex_b.location, (10, -120))
        self.assertEqual(utility.location, (270, 20))
        self.assertEqual(shader.location, (530, 20))
        self.assertEqual(output.location, (790, 20))

    def test_set_texture_colorspace_marks_data_inputs(self) -> None:
        texture = SimpleNamespace(filename_colorspace="srgb")

        utils.set_texture_colorspace(texture, "Roughness")

        self.assertEqual(texture.filename_colorspace, "data")


if __name__ == "__main__":
    unittest.main()
