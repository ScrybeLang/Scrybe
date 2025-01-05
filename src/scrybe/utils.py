from ply.yacc import PlyLogger
from copy import deepcopy

forbidden_chars = r'<>:"/\|?*'

# Helper function to create a rule-abiding Windows file name
def to_filename(string):
    filtered_chars = "".join(
        char for char in string if char not in forbidden_chars
    )

    # Trim trailing dots and spaces (technically not necessary)
    while filtered_chars[-1] in ". ":
        filtered_chars = filtered_chars[:-1]
    return filtered_chars

# Get the amount of objects this object represents
# For example: "Equals(Add(2, 2), 4)" => 2
#              "Divide(2, 3)"         => 1
#              "15"                   => 1
def get_depth(object):
    if isinstance(object, (int, float)) or not object.contained_blocks:
        return 1
    return sum(map(get_depth, object.contained_blocks)) + 1

def set_type(object, type):
    copy = deepcopy(object)
    copy.type = type

    return copy
