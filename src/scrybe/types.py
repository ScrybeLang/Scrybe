from enum import Flag, auto
from itertools import cycle
from .logger import code_error
from ScratchGen.blocks import Block, Reporter, Boolean
from ScratchGen.datacontainer import DataContainer, Variable, List
from ScratchGen import *

class Types(Flag):
    NUMBER  = auto()
    STRING  = auto()
    BOOLEAN = auto()
    GENERAL = NUMBER | STRING | BOOLEAN
    LIST    = auto()

    # Returns the flag representation of the given object
    @staticmethod
    def get_type(obj):
        if isinstance(obj, Types):                  return obj  # Already flagged
        if isinstance(obj, (Block, DataContainer)): return obj.type  # ScratchGen block types declared later

        # We must check for booleans before integers because
        # booleans are instances of integers which is dumb
        if isinstance(obj, bool):          return Types.BOOLEAN
        if isinstance(obj, (int, float)):  return Types.NUMBER
        if isinstance(obj, str):           return Types.STRING
        if isinstance(obj, (list, tuple)): return Types.LIST

    @staticmethod
    def check_types(possible_types, objects, error_message):
        objects = list(map(Types.get_type, objects))
        for types in possible_types:
            if all(Types._is_type(object, type) for object, type in zip(objects, types)):
                return

        formatted_types = list(map(repr, objects))
        code_error(error_message.format(*formatted_types))

    @staticmethod
    def _is_type(flags, type_to_check):
        return bool(flags & type_to_check)

    def __repr__(self):
        match self:
            case self.NUMBER:  return "number"
            case self.STRING:  return "string"
            case self.BOOLEAN: return "boolean"
            case self.GENERAL: return "variable"
            case self.LIST:    return "list"

        types = []
        if self._is_type(self, self.NUMBER):  types.append("number")
        if self._is_type(self, self.STRING):  types.append("string")
        if self._is_type(self, self.BOOLEAN): types.append("boolean")
        if self._is_type(self, self.LIST):    types.append("list")

        return "/".join(types)

# Set the type of ScratchGen blocks

Reporter.type = Types.GENERAL
Boolean.type  = Types.BOOLEAN
Variable.type = Types.GENERAL
List.type     = Types.LIST

XPosition.type = Types.NUMBER
YPosition.type = Types.NUMBER
Direction.type = Types.NUMBER

Size.type = Types.NUMBER

Volume.type = Types.NUMBER

DistanceTo.type    = Types.NUMBER
Timer.type         = Types.NUMBER
MouseX.type        = Types.NUMBER
MouseY.type        = Types.NUMBER
Current.type       = Types.NUMBER
DaysSince2000.type = Types.NUMBER
Loudness.type      = Types.NUMBER
Answer.type        = Types.STRING
Username.type      = Types.STRING

Add.type        = Types.NUMBER
Subtract.type   = Types.NUMBER
Multiply.type   = Types.NUMBER
Divide.type     = Types.NUMBER
PickRandom.type = Types.NUMBER
Join.type       = Types.STRING
LetterOf.type   = Types.STRING
LengthOf.type   = Types.NUMBER
Modulo.type     = Types.NUMBER
Round.type      = Types.NUMBER
Operation.type  = Types.NUMBER

ListIndexOf.type = Types.NUMBER
ListLength.type  = Types.NUMBER
