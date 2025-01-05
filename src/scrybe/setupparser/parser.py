from ply import yacc
from .lexer import lexer, tokens
from .. import filestate
from .. import utils
from ..logger import debug, code_error, set_lexpos
from ..scriptparser.parser import (p_number, p_boolean, p_list, p_expression_list,
                                   p_single_type, p_type_declaration,
                                   p_concatenation, p_numerical_operation, p_comparison_operation, p_logical_operation)

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
    """program : file_declaration variable_declarations
               | file_declaration
               | variable_declarations
               | """
    if len(prod) == 3:
        file_declaration = prod[1]
        variables = prod[2]
    elif len(prod) == 2:
        if prod.slice[1].type == "file_declaration":
            file_declaration = prod[1]
            variables = []
        elif prod.slice[1].type == "variable_declarations":
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

def p_variable_declarations(prod):
    """variable_declarations : set_variable variable_declarations
                             | set_variable"""
    if len(prod) == 3:
        prod[0] = [prod[1]] + prod[2]
    else:
        prod[0] = [prod[1]]

def p_variable(prod):
    """variable : VARIABLE"""
    prod[0] = {
        "lexpos":  prod.lexpos(1),
        "type":    "variable",
        "variable": prod[1]
    }

def p_expression(prod):
    """expression : number
                  | STRING
                  | boolean
                  | variable
                  | concatenation
                  | numerical_operation
                  | comparison_operation
                  | logical_operation
                  | LPAREN expression RPAREN"""
    if len(prod) == 2:
        prod[0] = prod[1]
    else:
        # Expression wrapped in parentheses
        prod[0] = prod[2]

def p_set_variable(prod):
    """set_variable : VARIABLE type_declaration EQUALS expression SEMICOLON
                    | VARIABLE type_declaration EQUALS list SEMICOLON"""
    prod[0] = {
        "lexpos": prod.lexpos(1),
        "name":   prod[1],
        "type":   prod[2],
        "value":  prod[4]
    }

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

debug("Initializing setup parser")
parser = yacc.yacc(debug=False, optimize=True)

def parse_file():
    return parser.parse(filestate.read_file(), lexer=lexer)
