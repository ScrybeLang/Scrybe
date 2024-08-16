from ScratchGen import Project
from ScratchGen.constants import *
from .scriptbuilder import ScriptBuilder
from .logger import debug, warn, code_error, set_lexpos
from . import filestate
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
        #     },
        #    ...
        # }
        self.broadcasts = {}
        # Variables: {
        #     "global": {
        #         <variable name>: {                    \
        #             "type":   <"variable" or "list">, | Single variable schema
        #             "object": <variable object>       |
        #         },                                    /
        #         ...
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
        #         <sprite name>: <list of AST statements>,
        #         ...
        #     }
        # }
        self.scripts = {
            "stage":   [],
            "sprites": {}
        }
        # Sprites: {
        #     <sprite name>: {
        #         "object":   <sprite object>,
        #         "filename": <sprite filename>
        #     },
        #     ...
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

    def add_sprite(self, sprite_ast, filename):
        declarations = self.get_declarations(
            sprite_ast["declarations"], filename, False
        )

        sprite = self.project.createSprite(
            declarations["name"],
            declarations["visible"],
            declarations["x"],
            declarations["y"],
            declarations["size"],
            declarations["direction"],
            declarations["draggable"],
            declarations["rotationstyle"],
            declarations["layer"]
        )

        self.add_assets(declarations["costume"], "costume", sprite)
        self.add_assets(declarations["sound"], "sound", sprite)

        self.variables["local"]["sprites"][sprite.name] = {}
        self.scripts["sprites"][sprite.name] = sprite_ast["statements"]
        self.sprites[sprite.name] = {
            "object":   sprite,
            "filename": filename
        }

        return sprite.name

    def add_stage(self, stage_ast):
        declarations = self.get_declarations(
            stage_ast["declarations"], "stage.sbs", True
        )

        self.add_assets(declarations["costume"], "backdrop", self.project.stage)
        self.add_assets(declarations["sound"], "sound", self.project.stage)

        self.scripts["stage"] = stage_ast["statements"]

    # This would be a constant top-level tuple but "filename" has to be set each time
    def generate_declaration_info(self, filename):
        # Info: (
        #     (<declaration name>, <default value>, <sprite-specific>),
        #     ...
        # )
        return (
            ("name",          filename[:-4], True),
            ("costume",       [],            False),
            ("sound",         [],            False),
            ("visible",       True,          True),
            ("x",             0,             True),
            ("y",             0,             True),
            ("size",          100,           True),
            ("direction",     90,            True),
            ("draggable",     True,          True),
            ("rotationstyle", ALL_AROUND,    True),
            ("layer",         1,             True)
        )

    # Get declarations as a dictionary
    # Declaration dictionary: {
    #     <declaration name>: <declaration value>,
    #     ...
    # }
    def get_declarations(self, declaration_statements, filename, is_stage):
        declaration_info = self.generate_declaration_info(filename)

        # Cut off the third element of each item (the sprite-specific tag)
        # to get a dictionary with default values
        declarations = dict([item[:-1] for item in declaration_info])
        defined_declarations = []

        for declaration_name, _, sprite_specific in declaration_info:
            for declaration in declaration_statements:
                set_lexpos(declaration["lexpos"])

                if declaration["property"] == f"#{declaration_name}":
                    if sprite_specific and is_stage:
                        code_error("This declaration can only be used in a sprite")

                    if declaration_name in defined_declarations:
                        code_error("Redefined declaration")

                    declarations[declaration_name] = declaration["value"]
                    defined_declarations.append(declaration_name)

        return declarations

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

            filestate.current_entry = "stage.sbs"
            ScriptBuilder(self, statements, target).build()
            debug("  Built scripts in stage")

        else:
            warn("  No scripts were found in the stage")

        for sprite_name, dict_entry in self.sprites.items():
            sprite_object = dict_entry["object"]
            sprite_filename = dict_entry["filename"]

            statements = self.scripts["sprites"][sprite_name]
            target = sprite_object

            filestate.current_entry = f"sprites/{sprite_filename}"
            ScriptBuilder(self, statements, target).build()
            debug(f'  Built scripts in sprite "{sprite_name}"')

    def save(self, filename=None):
        filename = filename or self.filename
        self.project.save(filename)

        return filename
