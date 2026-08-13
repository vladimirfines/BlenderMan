# BlenderMan

**BlenderMan** is *enderMan blender addon's addon.  
It aims at closing biggest *RM* flaw: scene conversion. Manualy replacing every node in every material from Cycles to *RM* is exhausting, specially in complete scenes or assets.

Use **BlenderMan** instead:

- **Convert Material**: Automatically maps Cycles `Principled BSDF` and textures to `PxrDisneyBsdf` and `PxrTexture` for all selected objects.
- **Convert World (HDRI)**: Transforms Cycles World setups into `PxrDomeLight` configurations with a single click.
- **Convert Selected**: convert the nodes you need to RM equivalent.
- **Import Textures**: High-speed batch import of texture files directly as PxrTexture nodes.
- **Non-Destructive**: original Cycles nodes are kept intact and functional, with RenderMan branches created next to them.

## Usage

Once installed, you will find the BlenderMan panel in two locations:

- **Shader Editor Sidebar**: A dedicated "Blenderman" tab containing all conversion tools.
- **3D Viewport Sidebar**: Inside the "RenderMan" tab for quick access to material and world conversion.

## Compatibility

- **Blender**: 4.x
- **RenderMan**: Requires RenderMan *(tested on 27.0)* for Blender plugin to be installed. 

---

## License

This project is licensed under the **GPL-3.0-or-later** License. Developed by Vladimir Fines. 