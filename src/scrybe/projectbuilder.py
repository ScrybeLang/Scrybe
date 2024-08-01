from ScratchGen import Project
from ScratchGen.constants import *
from .scriptbuilder import ScriptBuilder
from .logger import debug, info, warn, error

import glob
import os

class ProjectBuilder:
    def __init__(self, directory_name):
        self.project = Project()
        self.filename = f"{directory_name}.sb3"

        # Broadcasts: {
        #     <broadcast name>: {
        #         "broadcast": <broadcast object>,
        #         "variable":  <broadcast message object>
        #     }
        # }
        self.broadcasts = {}
        # Variables: {
        #     "global": {
        #         <variable name>: {                    \
        #             "type":   <"variable" or "list">, | Single variable schema
        #             "object": <variable object>       |
        #         }                                     /
        #     },
        #     "local": {
        #         "stage":   {<variable schemas>},
        #         "sprites": {<variable schemas>}
        #     }
        # }
        self.variables = {
            "global": {},
            "local": {
                "stage":   {},
                "sprites": {}
            }
        }
        # Scripts: {
        #     "stage": <list of AST statements>,
        #     "sprites": {
        #         <sprite name>: <list of AST statements>
        #     }
        # }
        self.scripts = {
            "stage":   [],
            "sprites": {}
        }
        # Sprites: {
        #     <sprite name>: <sprite object>
        # }
        self.sprites = {}

    def apply_setup(self, setup_ast):
        file_declaration = setup_ast["file declaration"] or {}
        current_folder = os.path.basename(os.getcwd())
        self.filename = file_declaration.get("filename", current_folder + ".sb3")

        # Add global variables
        for variable in setup_ast["variables"]:
            self.add_variable(
                f"g_{variable["name"]}",
                variable["value"]
            )

    # `variable_name` should already be scope formatted
    def add_variable(self, variable_name, variable_value, target=None):
        target = target or self.project.stage

        is_list = isinstance(variable_value, list)
        function = target.createList if is_list else target.createVariable
        variable_object = function(variable_name, variable_value)
        dictionary_entry = {
            "type":   "list" if is_list else "variable",
            "object": variable_object
        }

        if variable_name.startswith("g_") or variable_name.startswith("br_"):
            self.variables["global"][variable_name] = dictionary_entry
            debug(f'    Created global variable "{variable_name}" ')
        else:
            if target._is_stage:
                self.variables["local"]["stage"][variable_name] = dictionary_entry
            else:
                self.variables["local"]["sprites"][target.name][variable_name] = dictionary_entry
            debug(f'    Created local variable "{variable_name}" ')

        return dictionary_entry

    def get_broadcast(self, broadcast_name):
        if broadcast_name not in self.broadcasts:
            variable_object = self.add_variable(f"br_{broadcast_name}", "")["object"]
            broadcast_object = self.project.createBroadcast(broadcast_name)

            self.broadcasts[broadcast_name] = {
                "broadcast": broadcast_object,
                "variable":  variable_object
            }
            debug(f'    Created new broadcast "{broadcast_name}"')

        return self.broadcasts[broadcast_name]

    def add_stage(self, stage_ast):
        declarations = stage_ast["declarations"]

        backdrops = self.get_declaration(declarations, "#costume", [])
        sounds    = self.get_declaration(declarations, "#sound", [])

        self.add_assets(backdrops, "backdrop", self.project.stage)
        self.add_assets(sounds, "sound", self.project.stage)

        self.scripts["stage"] = stage_ast["statements"]

    def add_sprite(self, sprite_ast, filename):
        declarations = sprite_ast["declarations"]

        name           = self.get_declaration(declarations, "#name", filename[:-4])
        costumes       = self.get_declaration(declarations, "#costume", [])
        sounds         = self.get_declaration(declarations, "#sound", [])
        visible        = self.get_declaration(declarations, "#visible", True)
        x              = self.get_declaration(declarations, "#x", 0)
        y              = self.get_declaration(declarations, "#y", 0)
        size           = self.get_declaration(declarations, "#size", 100)
        direction      = self.get_declaration(declarations, "#direction", 90)
        draggable      = self.get_declaration(declarations, "#draggable", True)
        rotation_style = self.get_declaration(declarations, "#rotationstyle", ALL_AROUND)
        layer_order    = self.get_declaration(declarations, "#layer", 1)

        sprite = self.project.createSprite(
            name, visible, x, y, size, direction, draggable, rotation_style, layer_order
        )

        self.add_assets(costumes, "costume", sprite)
        self.add_assets(sounds, "sound", sprite)

        self.variables["local"]["sprites"][sprite.name] = {}
        self.scripts["sprites"][sprite.name] = sprite_ast["statements"]
        self.sprites[sprite.name] = sprite

        return sprite.name

    def add_assets(self, path_list, type, target):
        function = target.addSound if type == "sound" else target._addCostume

        # `path_list` is a list of filepaths and/or glob expressions
        for expression in path_list:
            for file in glob.glob(expression):
                function(file)
                debug(f'  Added asset "{file}"')

    def get_declaration(self, declarations, property, default_value=None):
        for declaration in declarations:
            if declaration["property"] == property:
                return declaration["value"]

        return default_value

    def build(self):
        if self.scripts["stage"]:
            statements = self.scripts["stage"]
            target = self.project.stage

            ScriptBuilder(self, statements, target).build()
            debug("  Built scripts in stage")

        else:
            warn("  No scripts were found in the stage")

        for sprite_name, sprite_object in self.sprites.items():
            statements = self.scripts["sprites"][sprite_name]
            target = sprite_object

            ScriptBuilder(self, statements, target).build()
            debug(f'  Built scripts in sprite "{sprite_name}"')

    def save(self, filename=None):
        filename = filename or self.filename
        self.project.save(filename)

        return filename
