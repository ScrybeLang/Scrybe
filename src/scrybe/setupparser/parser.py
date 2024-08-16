from ply import yacc
from .lexer import lexer, tokens
from .. import filestate
from .. import utils
from ..logger import code_error, set_lexpos

precedence = (
    ("left", "OR"),
    ("left", "AND"),
    ("left", "EQUALTO", "NOTEQUALTO"),
    ("left", "LESSTHAN", "GREATERTHAN", "LESSTHANEQUAL", "GREATERTHANEQUAL"),
    ("left", "PLUS", "MINUS"),
    ("left", "TIMES", "DIVIDEDBY", "MODULO"),
    ("left", "EXPONENT"),
    ("right", "UMINUS")
)

def p_program(prod):
    """program : file_declaration variable_list
               | file_declaration
               | variable_list
               | """
    if len(prod) == 3:
        file_declaration = prod[1]
        variables = prod[2]
    elif len(prod) == 2:
        if prod.slice[1].type == "file_declaration":
            file_declaration = prod[1]
            variables = []
        elif prod.slice[1].type == "variable_list":
            file_declaration = {}
            variables = prod[1]
    else:
        file_declaration, variables = None, []

    prod[0] = {
        "file declaration": file_declaration,
        "variables":        variables
    }

def p_file_declaration(prod):
    """file_declaration : PROJECTDEC STRING SEMICOLON
                        | PROJECTDEC STRING FILENAMEDEC STRING SEMICOLON"""
    if len(prod) == 4:
        filename = utils.to_filename(prod[2]) + ".sb3"
    else:
        filename = prod[4]

    prod[0] = {
        "project name": prod[2],
        "filename":     filename
    }

def p_variable_list(prod):
    """variable_list : variable_dec variable_list
                     | variable_dec"""
    if len(prod) == 3:
        prod[0] = [prod[1]] + prod[2]
    else:
        prod[0] = [prod[1]]

def p_variable_dec(prod):
    """variable_dec : VARIABLE EQUALS expression SEMICOLON"""
    prod[0] = {
        "name":  prod[1],
        "value": prod[3]
    }

def p_expression(prod):
    """expression : expression PLUS expression
                  | expression MINUS expression
                  | expression TIMES expression
                  | expression DIVIDEDBY expression
                  | expression MODULO expression
                  | expression EXPONENT expression
                  | MINUS expression %prec UMINUS
                  | LPAREN expression RPAREN
                  | STRING
                  | NUMBER
                  | condition
                  | list"""
    if len(prod) == 2:
        prod[0] = prod[1]
    elif len(prod) == 3:
        # Unary minus
        prod[0] = -float(prod[2])
    else:
        if prod[1] == "(" and prod[3] == ")":
            # Expression WRAPPED in parentheses
            prod[0] = prod[2]
        else:
            # Binary operation
            prod[0] = utils.evaluate_expression({
                "type":     "binary operation",
                "operation": prod[2],
                "operand 1": prod[1],
                "operand 2": prod[3]
            })

def p_condition(prod):
    """condition : expression LESSTHAN expression
                 | expression GREATERTHAN expression
                 | expression LESSTHANEQUAL expression
                 | expression GREATERTHANEQUAL expression
                 | expression EQUALTO expression
                 | expression NOTEQUALTO expression
                 | expression AND expression
                 | expression OR expression
                 | boolean"""
    if isinstance(prod[1], bool):
        prod[0] = prod[1]
    else:
        prod[0] = utils.evaluate_expression({
            "type":     "binary operation",
            "operation": prod[2],
            "operand 1": prod[1],
            "operand 2": prod[3]
        })

def p_boolean(prod):
    """boolean : TRUE
               | FALSE"""
    prod[0] = prod[1] == "true"

def p_list(prod):
    """list : LBRACKET expression_list RBRACKET
            | LBRACKET RBRACKET"""
    if len(prod) == 4:
        prod[0] = prod[2]
    else:
        prod[0] = []

def p_expression_list(prod):
    """expression_list : expression
                       | expression_list COMMA expression"""
    if len(prod) == 2:
        prod[0] = [prod[1]]
    else:
        prod[0] = prod[1] + [prod[3]]

def p_error(token):
    stack = [sym.type for sym in parser.symstack[1:]]
    state = parser.state
    expected = parser.action[state].keys()
    current_token = token.type if token else "EOF"
    set_lexpos(token.lexpos if token else None)

    if stack[-1].endswith("DEC"):
        code_error("Invalid declaration type")

    if current_token.endswith("DEC"):
        code_error("Unexpected declaration")

    if "SEMICOLON" in expected:
        code_error("Expected semicolon")

    if "NUMBER" in expected:
        code_error("Expected expression")

    if "VARIABLE" in stack:
        code_error("Unexpected variable")

    print("Uncaught setup parsing error, please report in the repository")
    print("-" * 50)
    print(f"Syntax error at line {token.lineno if token else 'EOF'}")
    print(f"Token: {current_token}")
    print(f"Expected: {', '.join(expected)}")
    print(f"Symbol stack (state {state}): {stack}")

    exit()

# parser = yacc.yacc(debug=False, optimize=True, errorlog=utils.NullBuffer)
parser = yacc.yacc()

def parse_file(file_path):
    filestate.open_file(file_path)
    ast = parser.parse(filestate.read_file(), lexer=lexer)
    filestate.close_file()

    return ast
