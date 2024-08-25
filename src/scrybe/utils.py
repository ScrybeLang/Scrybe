from ply.yacc import PlyLogger
from .translations import operations

forbidden_chars = r'<>:"/\|?*'

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

        return operations[operation](operand_1, operand_2)

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

# Prevent PLY warning/error logs from showing (so smart!)
class _NullBuffer:
    def write(self, *args, **kwargs):
        ...

NullBuffer = PlyLogger(_NullBuffer)
