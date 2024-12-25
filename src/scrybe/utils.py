from ply.yacc import PlyLogger
from .logger import code_error
import operator

forbidden_chars = r'<>:"/\|?*'
literal_operations = {
    "+":   operator.add,
    "-":   operator.sub,
    "*":   operator.mul,
    "/":   operator.truediv,
    "%":   operator.mod,
    "**":  operator.pow,
    "<":   operator.lt,
    ">":   operator.gt,
    "<=":  operator.le,
    ">=":  operator.ge,
    "==":  operator.eq,
    "!=":  operator.ne
}

# Helper function to create a rule-abiding Windows file name
def to_filename(string):
    filtered_chars = "".join(
        char for char in string if char not in forbidden_chars
    )

    if filtered_chars[-1] in ". ":
        return filtered_chars[:-1]
    return filtered_chars

# Get the amount of objects this object represents
# For example: "Equals(Add(2, 2), 4)" => 2
#              "Divide(2, 3)"         => 1
#              "15"                   => 1
def get_depth(object):
    if isinstance(object, (int, float)) or not object.contained_blocks:
        return 1
    return sum(map(get_depth, object.contained_blocks)) + 1

# Begging forgiveness 🥺
def is_number(string):
    try:
        float(string)
        return True
    except:
        return False

def set_type(object, type):
    object.type = type
    return object

# Prevent PLY warning/error logs from showing (so smart!)
class _NullBuffer:
    def write(self, *args, **kwargs):
        ...

NullBuffer = PlyLogger(_NullBuffer)
