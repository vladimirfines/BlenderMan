from __future__ import annotations

import unittest
from types import SimpleNamespace

import convert_material
import convert_selected_nodes
import convert_world
import import_textures
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

    def test_convert_principled_material_creates_rendererman_branch(self) -> None:
        material = utils.build_fake_material_tree()
        image = utils.find_first_node_by_type(material.node_tree, "ShaderNodeTexImage")
        image.image = SimpleNamespace(filepath="/textures/albedo.png")

        report = utils.convert_principled_material(material)

        rm_shader = utils.find_first_node_by_type(material.node_tree, "PxrSurface")
        rm_output = utils.find_first_node_by_type(material.node_tree, "RendermanOutputNode")
        rm_texture = utils.find_first_node_by_type(material.node_tree, "PxrTexture")
        self.assertIsNotNone(rm_shader)
        self.assertIsNotNone(rm_output)
        self.assertIsNotNone(rm_texture)
        self.assertEqual(rm_texture.filename, "/textures/albedo.png")
        self.assertTrue(any(entry.startswith("INFO:") for entry in report))

    def test_convert_selected_nodes_duplicates_supported_selection(self) -> None:
        node_tree = utils.FakeNodeTree()
        image = node_tree.nodes.new("ShaderNodeTexImage")
        image.name = "Selected Texture"
        image.image = SimpleNamespace(filepath="/textures/roughness.png")
        image.select = True

        context = SimpleNamespace(space_data=SimpleNamespace(node_tree=node_tree), selected_nodes=[image])

        report = convert_selected_nodes.convert_context_selected_nodes(context)

        rm_nodes = utils.find_nodes_by_type(node_tree, "PxrTexture")
        self.assertEqual(len(rm_nodes), 1)
        self.assertEqual(rm_nodes[0].filename, "/textures/roughness.png")
        self.assertTrue(any("Converted 1 selected node" in entry for entry in report))

    def test_convert_context_materials_uses_selected_objects(self) -> None:
        material = utils.build_fake_material_tree()
        image = utils.find_first_node_by_type(material.node_tree, "ShaderNodeTexImage")
        image.image = SimpleNamespace(filepath="/textures/basecolor.png")
        obj = SimpleNamespace(material_slots=[SimpleNamespace(material=material)])
        context = SimpleNamespace(selected_objects=[obj], space_data=SimpleNamespace(node_tree=material.node_tree))

        report = convert_material.convert_context_materials(context)

        self.assertTrue(any("created RenderMan material branch" in entry for entry in report))

    def test_convert_world_hdri_creates_dome_light(self) -> None:
        world = utils.build_fake_world_tree()
        context = SimpleNamespace(scene=SimpleNamespace(world=world), space_data=SimpleNamespace(node_tree=world.node_tree))

        report = convert_world.convert_context_world(context)

        dome = utils.find_first_node_by_type(world.node_tree, "PxrDomeLight")
        self.assertIsNotNone(dome)
        self.assertEqual(dome.lightColorMap, "/tmp/sky.hdr")
        self.assertEqual(dome.lightRotation, (0.0, 0.5, 1.0))
        self.assertTrue(any("dome light" in entry for entry in report))

    def test_import_textures_filters_non_images(self) -> None:
        node_tree = utils.FakeNodeTree()
        operator = SimpleNamespace(
            directory="/maps",
            files=[SimpleNamespace(name="diffuse.png"), SimpleNamespace(name="notes.txt")],
        )
        context = SimpleNamespace(space_data=SimpleNamespace(node_tree=node_tree))

        report = import_textures.import_context_textures(context, operator)

        rm_nodes = utils.find_nodes_by_type(node_tree, "PxrTexture")
        self.assertEqual(len(rm_nodes), 1)
        self.assertEqual(rm_nodes[0].filename, "/maps/diffuse.png")
        self.assertTrue(any("Skipped non-image file" in entry for entry in report))


if __name__ == "__main__":
    unittest.main()
