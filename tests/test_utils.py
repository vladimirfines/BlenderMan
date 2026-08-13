from __future__ import annotations

import unittest
from types import SimpleNamespace

try:
    import bpy  # type: ignore
except ImportError:
    bpy = None

import convert_material
import convert_selected_nodes
import convert_world
import import_textures
import utils
from tests import mock_bpy


class UtilsTests(unittest.TestCase):
    def test_collect_unique_materials_deduplicates_instances(self) -> None:
        material = SimpleNamespace(name="Mat")
        obj_a = SimpleNamespace(material_slots=[SimpleNamespace(material=material)])
        obj_b = SimpleNamespace(material_slots=[SimpleNamespace(material=material)])

        materials = utils.collect_unique_materials([obj_a, obj_b])

        self.assertEqual(materials, [material])

    def test_find_linked_principled_prefers_output_chain(self) -> None:
        material = mock_bpy.build_fake_material_tree()

        principled = utils.find_linked_principled(material.node_tree)

        self.assertIsNotNone(principled)
        self.assertEqual(principled.bl_idname, "ShaderNodeBsdfPrincipled")

    def test_trace_input_chain_walks_upstream_nodes(self) -> None:
        material = mock_bpy.build_fake_material_tree()
        principled = utils.find_linked_principled(material.node_tree)

        chain = utils.trace_input_chain(principled.inputs["Base Color"])

        self.assertEqual([node.bl_idname for node in chain], ["ShaderNodeTexImage"])

    def test_create_renderman_node_uses_mapping_table(self) -> None:
        node_tree = mock_bpy.FakeNodeTree()
        source_node = mock_bpy.FakeNode(
            "ShaderNodeTexImage", name="Albedo", outputs=("Color",)
        )

        node = utils.create_renderman_node(node_tree, blender_node=source_node)

        self.assertEqual(node.bl_idname, "PxrTexture")
        self.assertEqual(node.name, "RM Albedo")

    def test_layout_renderman_branch_places_columns_deterministically(self) -> None:
        node_tree = mock_bpy.FakeNodeTree()
        tex_a = node_tree.nodes.new("PxrTexture")
        tex_b = node_tree.nodes.new("PxrTexture")
        utility = node_tree.nodes.new("PxrNormalMap")
        shader = node_tree.nodes.new("PxrDisneyBsdf")
        output = node_tree.nodes.new("RendermanOutputNode")

        utils.layout_renderman_branch(
            [tex_a, tex_b], [utility], shader, output, origin=(10, 20)
        )

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
        material = mock_bpy.build_fake_material_tree()
        image = utils.find_first_node_by_type(material.node_tree, "ShaderNodeTexImage")
        image.image = SimpleNamespace(filepath="/textures/albedo.png")

        report = utils.convert_principled_material(material)

        rm_shader = utils.find_first_node_by_type(material.node_tree, "PxrDisneyBsdf")
        rm_output = utils.find_first_node_by_type(
            material.node_tree, "RendermanOutputNode"
        )
        rm_texture = utils.find_first_node_by_type(material.node_tree, "PxrTexture")
        self.assertIsNotNone(rm_shader)
        self.assertIsNotNone(rm_output)
        self.assertIsNotNone(rm_texture)
        self.assertEqual(rm_texture.filename, "/textures/albedo.png")
        self.assertTrue(any(entry.startswith("INFO:") for entry in report))

    def test_convert_selected_nodes_duplicates_supported_selection(self) -> None:
        node_tree = mock_bpy.FakeNodeTree()
        image = node_tree.nodes.new("ShaderNodeTexImage")
        image.name = "Selected Texture"
        image.image = SimpleNamespace(filepath="/textures/roughness.png")
        image.select = True

        context = SimpleNamespace(
            space_data=SimpleNamespace(node_tree=node_tree), selected_nodes=[image]
        )

        report = convert_selected_nodes.convert_context_selected_nodes(context)

        rm_nodes = utils.find_nodes_by_type(node_tree, "PxrTexture")
        self.assertEqual(len(rm_nodes), 1)
        self.assertEqual(rm_nodes[0].filename, "/textures/roughness.png")
        self.assertTrue(any("Converted 1 selected node" in entry for entry in report))

    def test_convert_context_materials_uses_active_object(self) -> None:
        material = mock_bpy.build_fake_material_tree()
        image = utils.find_first_node_by_type(material.node_tree, "ShaderNodeTexImage")
        image.image = SimpleNamespace(filepath="/textures/basecolor.png")
        active_object = SimpleNamespace(
            material_slots=[SimpleNamespace(material=material)],
            active_material=material,
        )
        context = SimpleNamespace(selected_objects=[], active_object=active_object)

        report = convert_material.convert_context_materials(context)

        self.assertTrue(any("RenderMan material branch" in entry for entry in report))

    def test_convert_world_hdri_creates_dome_light(self) -> None:
        world = mock_bpy.build_fake_world_tree()
        context = SimpleNamespace(
            scene=SimpleNamespace(world=world),
            space_data=SimpleNamespace(node_tree=world.node_tree),
        )

        if bpy is None:
            self.skipTest("bpy not available")

        report = convert_world.convert_context_world(context)

        self.assertTrue(len(report) > 0)

    def test_import_textures_filters_non_images(self) -> None:
        node_tree = mock_bpy.FakeNodeTree()
        operator = SimpleNamespace(
            directory="/maps",
            files=[
                SimpleNamespace(name="diffuse.png"),
                SimpleNamespace(name="notes.txt"),
            ],
        )
        context = SimpleNamespace(space_data=SimpleNamespace(node_tree=node_tree))

        report = import_textures.import_context_textures(context, operator)

        rm_nodes = utils.find_nodes_by_type(node_tree, "PxrTexture")
        self.assertEqual(len(rm_nodes), 1)
        self.assertEqual(rm_nodes[0].filename, "/maps/diffuse.png")
        self.assertTrue(any("Skipped non-image file" in entry for entry in report))

    def test_context_has_convertible_materials_uses_active_object(self) -> None:
        material = SimpleNamespace(name="Mat")
        active_object = SimpleNamespace(
            material_slots=[SimpleNamespace(material=material)]
        )
        context = SimpleNamespace(selected_objects=[], active_object=active_object)

        self.assertTrue(utils.context_has_convertible_materials(context))

    def test_convert_material_reports_missing_renderman_nodes(self) -> None:
        material = mock_bpy.build_fake_material_tree()
        original_new = material.node_tree.nodes.new

        def failing_new(bl_idname: str):
            if bl_idname == "PxrDisneyBsdf":
                raise RuntimeError("undefined")
            return original_new(bl_idname)

        material.node_tree.nodes.new = failing_new
        report = utils.convert_principled_material(material)

        self.assertTrue(
            any(
                "RenderMan node type PxrDisneyBsdf is unavailable" in entry
                for entry in report
            )
        )

    def test_convert_context_materials_uses_active_object_when_nothing_selected(
        self,
    ) -> None:
        material = mock_bpy.build_fake_material_tree()
        active_object = SimpleNamespace(
            material_slots=[SimpleNamespace(material=material)]
        )
        context = SimpleNamespace(selected_objects=[], active_object=active_object)

        report = convert_material.convert_context_materials(context)

        self.assertTrue(report)

    def test_context_has_world_checks_scene_world(self) -> None:
        context = SimpleNamespace(scene=SimpleNamespace(world=object()))

        self.assertTrue(utils.context_has_world(context))

    def test_convert_materials_plural_helper(self) -> None:
        mat_a = mock_bpy.build_fake_material_tree()
        mat_b = mock_bpy.build_fake_material_tree()
        mat_a.name = "MatA"
        mat_b.name = "MatB"

        report = utils.convert_materials([mat_a, mat_b])

        self.assertEqual(sum(1 for entry in report if "created RenderMan material branch" in entry), 2)


if __name__ == "__main__":
    unittest.main()
