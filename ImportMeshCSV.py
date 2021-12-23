# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

bl_info = {
    "name": "Import CSV File",
    "description": "Import mesh from CSV file.",
    "author": "Nikolay Bulatov",
    "version": (1, 0, 0),
    "blender": (2, 80, 0),
    "location": "File > Import-Export",
    "warning": "",
    "wiki_url": "",
    "category": "Import-Export"
}

import bpy

from bpy.props import (
    BoolProperty,
    FloatProperty,
    IntProperty,
    StringProperty,
    CollectionProperty,
)

from bpy_extras.io_utils import (
    ImportHelper,
    unpack_list,
    orientation_helper,
    axis_conversion,
)

from bpy.types import (
    Operator,
    OperatorFileListElement,
)

#-------------------------------------------------------------------------------


@orientation_helper(axis_forward='Y', axis_up='Z')
class ImportCSV(Operator, ImportHelper):
    bl_idname = "import_mesh.csv"
    bl_label = "Import CSV File"
    bl_description = "Load CSV mesh data"
    bl_options = {'UNDO'}

    filename_ext = ".csv"

    filter_glob: StringProperty(
        default="*.csv",
        options={'HIDDEN'},
    )
    files: CollectionProperty(
        name="File Path",
        type=OperatorFileListElement,
    )
    directory: StringProperty(
        subtype='DIR_PATH'
    )

 
    skip_header: BoolProperty(
        name="Skip Header Row",
        description="",
        default=False
    )

    skip_cols: IntProperty(
        name="Skip Columns",
        description="",
        default=0,
        min=0
    )

    mirror_x: bpy.props.BoolProperty(
        name="Mirror X",
        description="Mirror all the vertices across X axis",
        default=False
    )
                                      
    vertex_order: bpy.props.BoolProperty(
        name="Change Vertex Order",
        description="Reorder vertices in counter-clockwise order",
        default=False
    )

    global_scale: FloatProperty(
        name="Scale",
        soft_min=0.001, soft_max=1000.0,
        min=1e-6, max=1e6,
        default=1.0,
    )

    use_scene_unit: BoolProperty(
        name="Scene Unit",
        description="Apply current scene's unit (as defined by unit scale) to imported data",
        default=False,
    )

    doubles_remove: bpy.props.BoolProperty(
        name="Merge by Distance",
        description="Merge vertices based on their proximity",
        default=True
    )

    doubles_treshold: FloatProperty(
        name="Merge Distance",
        description="Threshold for merging vertices",
        min=1e-4, max=1e0,
        precision=4,
        step=0.01,
        default=0.0001,
    )


    def execute(self, context):
        from mathutils import Matrix

        keywords = self.as_keywords(
            ignore=(
                "axis_forward",
                "axis_up",
                "filter_glob",
                "global_scale",
                "use_scene_unit"
            )
        )

        scene = context.scene

        global_scale = self.global_scale
        if scene.unit_settings.system != 'NONE' and self.use_scene_unit:
            global_scale /= scene.unit_settings.scale_length 

        global_matrix = axis_conversion(
            from_forward=self.axis_forward,
            from_up=self.axis_up,
        ).to_4x4() @ Matrix.Scale(global_scale, 4)

        keywords["global_matrix"] = global_matrix

        if bpy.ops.object.mode_set.poll():
            bpy.ops.object.mode_set(mode='OBJECT')

        read_csv(**keywords)

        return {'FINISHED'}


    def draw(self, context):
        pass


class CSV_PT_import_format(bpy.types.Panel):
    bl_space_type = 'FILE_BROWSER'
    bl_region_type = 'TOOL_PROPS'
    bl_label = "Format"
    bl_parent_id = "FILE_PT_operator"

    @classmethod
    def poll(cls, context):
        sfile = context.space_data
        operator = sfile.active_operator

        return operator.bl_idname == "IMPORT_MESH_OT_csv"

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False  # No animation.

        sfile = context.space_data
        operator = sfile.active_operator

        layout.prop(operator, "skip_header")
        layout.prop(operator, "skip_cols")


class CSV_PT_import_transform(bpy.types.Panel):
    bl_space_type = 'FILE_BROWSER'
    bl_region_type = 'TOOL_PROPS'
    bl_label = "Transform"
    bl_parent_id = "FILE_PT_operator"

    @classmethod
    def poll(cls, context):
        sfile = context.space_data
        operator = sfile.active_operator

        return operator.bl_idname == "IMPORT_MESH_OT_csv"

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False  # No animation.

        sfile = context.space_data
        operator = sfile.active_operator

        layout.prop(operator, "mirror_x")
        layout.prop(operator, "vertex_order")
        layout.prop(operator, "global_scale")
        layout.prop(operator, "use_scene_unit")
        layout.prop(operator, "axis_forward")
        layout.prop(operator, "axis_up")


class CSV_PT_import_doubles(bpy.types.Panel):
    bl_space_type = 'FILE_BROWSER'
    bl_region_type = 'TOOL_PROPS'
    bl_label = "Merge"
    bl_parent_id = "FILE_PT_operator"

    @classmethod
    def poll(cls, context):
        sfile = context.space_data
        operator = sfile.active_operator

        return operator.bl_idname == "IMPORT_MESH_OT_csv"

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False  # No animation.

        sfile = context.space_data
        operator = sfile.active_operator

        layout.prop(operator, "doubles_remove")
        layout.prop(operator, "doubles_treshold")


def mesh_make(vertices, faces, global_matrix, loop_start, loop_total, objectname):
    mesh = bpy.data.meshes.new('name')
    
    num_vertices = vertices.shape[0] // 3
    mesh.vertices.add(num_vertices)
    mesh.vertices.foreach_set("co", vertices)

    num_faces = faces.shape[0]
    mesh.loops.add(num_faces)
    mesh.loops.foreach_set("vertex_index", faces)

    num_loops = loop_start.shape[0]
    mesh.polygons.add(num_loops)
    mesh.polygons.foreach_set("loop_start", loop_start)
    mesh.polygons.foreach_set("loop_total", loop_total)

    mesh.update()
    mesh.validate()

    # Create Object whose Object Data is our new mesh
    obj = bpy.data.objects.new(objectname, mesh)

    # Apply transformation matrix
    obj.matrix_world = global_matrix

    # Add *Object* to the scene, not the mesh
    bpy.context.scene.collection.objects.link(obj)

    # Select the new object and make it active
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj


def mesh_remove_doubles(doubles_treshold):
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.remove_doubles(threshold = doubles_treshold)
    bpy.ops.object.mode_set(mode='OBJECT')


def read_csv(filepath=None, directory=None, files=None, mirror_x=False, vertex_order=True, doubles_remove=False, doubles_treshold=0.0001, skip_header=False, skip_cols=0, global_matrix=None):
    import os
    import csv
    import numpy
    from mathutils import Matrix

    if global_matrix is None:
        global_matrix = Matrix()

    if filepath == None:
        return

    x_mod = 1
    if mirror_x:
        x_mod = -1

    for fn in files:
        filename = os.path.join(directory, fn.name)
        if os.path.exists(filename) == False or os.path.isfile(filename) == False:
            continue

        objectname = bpy.path.display_name(fn.name)

        vertices = []
        faces = []
        loop_start = []
        loop_total = []

        with open(filename) as f:
            f.seek(0)
            csv_reader = csv.reader(f)

            if skip_header:
                header = next(csv_reader)

            vertex_index = 0
            for row in csv_reader:
                try:
                    vertex = [float(row[skip_cols]), float(row[skip_cols + 1]), float(row[skip_cols + 2])]
                except:
                    continue
                
                vertices.append([x_mod * vertex[0], vertex[1], vertex[2]])

                vertex_index += 1
                if vertex_index % 3 == 0:
                    if vertex_order:
                        faces.append([vertex_index - 1, vertex_index - 2, vertex_index - 3])
                    else:
                        faces.append([vertex_index - 3, vertex_index - 2, vertex_index - 1])
                    loop_start.append(vertex_index - 3)

            loop_total = [3] * len(loop_start)

            vertices = numpy.array(unpack_list(vertices), dtype=numpy.float32)
            faces = numpy.array(unpack_list(faces), dtype=numpy.int32)
            loop_start = numpy.array(loop_start, dtype=numpy.int32)
            loop_total = numpy.array(loop_total, dtype=numpy.int32)

            mesh_make(vertices, faces, global_matrix, loop_start, loop_total, objectname)

            if doubles_remove:
                mesh_remove_doubles(doubles_treshold)

#-------------------------------------------------------------------------------

def menu_import(self, context):
    self.layout.operator(ImportCSV.bl_idname, text="CSV File (.csv)")

classes = (
    ImportCSV,
    CSV_PT_import_format,
    CSV_PT_import_transform,
    CSV_PT_import_doubles
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.TOPBAR_MT_file_import.append(menu_import)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    bpy.types.TOPBAR_MT_file_import.remove(menu_import)

if __name__ == "__main__":
    register()
