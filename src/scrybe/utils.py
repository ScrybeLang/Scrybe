from ply.yacc import PlyLogger
from copy import deepcopy
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
    "==":  operator.eq
}

# Helper function to create a rule-abiding Windows file name
def to_filename(string):
    filtered_chars = "".join(
        char for char in string if char not in forbidden_chars
    )

    if filtered_chars[-1] in ". ":
        return filtered_chars[:-1]
    return filtered_chars

# For setup scripts, only supports literals
def evaluate_expression(expression):
    if not isinstance(expression, dict):
        return expression

    if expression["type"] == "unary minus":
        sub_expression = expression["expression"]
        return -evaluate_expression(sub_expression)

    elif expression["type"] == "binary operation":
        operation = expression["operation"]
        operand_1 = evaluate_expression(expression["operand 1"])
        operand_2 = evaluate_expression(expression["operand 2"])

        return literal_operations[operation](operand_1, operand_2)

# Begging forgiveness 🥺
def is_number(string):
    try:
        float(string)
        return True
    except:
        return False

# Check if expression is all strings and/or numbers
# NO VARIABLES ALLOWED!
def is_literal(expression):
    if isinstance(expression, (int, float, str)):
        return True

    if not isinstance(expression, list):
        return False

    for item in expression:
        if not is_literal(item):
            return False

    return True

def get_type(object):
    if isinstance(object, bool):         return "boolean"
    if isinstance(object, (int, float)): return "number"
    if isinstance(object, str):          return "string"
    if isinstance(object, list):         return "list"

    return object.type

# This function is kind of hard to explain, so look where it is used
def check_types(possibilities, message, *objects, is_types=False):
    # Create a function to check a given type against a possible type
    # Examples: check_match("string", "string|number") -> True
    #           check_match("boolean", "list")         -> False
    def check_match(given_type, possible_types):
        possible_types = possible_types.split("|")

        if "any" in possible_types and given_type != "list":
            return True
        return given_type in possible_types

    given_types = list(objects if is_types else map(get_type, objects))
    for possibility in possibilities:
        possible_types = possibility.split()
        if all(check_match(a, b) for a, b in zip(given_types, possible_types)):
            return True

    if message.startswith("{"):
        # Capitalize the first word of the sentence
        given_types[0] = given_types[0].title()
    code_error(message.format(*given_types))

def copy_and_apply_type(object, type):
    copy = deepcopy(object)
    copy.type = type

    return copy

# Prevent PLY warning/error logs from showing (so smart!)
class _NullBuffer:
    def write(self, *args, **kwargs):
        ...

NullBuffer = PlyLogger(_NullBuffer)
