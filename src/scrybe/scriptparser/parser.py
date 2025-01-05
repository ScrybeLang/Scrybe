from ply import yacc
from .lexer import lexer, tokens, reserved
from .. import filestate
from .. import utils
from ..logger import debug, code_error, set_lexpos
from ..types import Types

precedence = (
    ("left", "OR"),
    ("left", "AND"),
    ("right", "NOT"),
    ("left", "IN"),
    ("left", "EQUALTO", "NOTEQUALTO"),
    ("left", "LESSTHAN", "GREATERTHAN", "LESSTHANEQUAL", "GREATERTHANEQUAL"),
    ("left", "PLUS", "MINUS"),
    ("left", "TIMES", "DIVIDEDBY", "MODULO"),
    ("left", "EXPONENT"),
    ("right", "UMINUS")
)

# Program structure

def p_program(prod):
    """program : meta_declaration_list top_level_statement_list
               | meta_declaration_list
               | top_level_statement_list
               | """
    if len(prod) == 3:
        declarations = prod[1]
        statements = prod[2]
    elif len(prod) == 2:
        if prod.slice[1].type == "meta_declaration_list":
            declarations = prod[1]
            statements = []
        elif prod.slice[1].type == "top_level_statement_list":
            declarations = []
            statements = prod[1]
    else:
        declarations, statements = [], []

    prod[0] = {
        "declarations": declarations,
        "statements":   statements
    }

def p_meta_declaration_list(prod):
    """meta_declaration_list : meta_declaration meta_declaration_list
                             | meta_declaration"""
    if len(prod) == 3:
        prod[0] = [prod[1]] + prod[2]
    elif len(prod) == 2:
        prod[0] = [prod[1]]
    else:
        prod[0] = []

def p_meta_declaration(prod):
    """meta_declaration : SPRITENAMEDEC STRING
                        | COSTUMEDEC STRING
                        | COSTUMEDEC list
                        | SOUNDDEC STRING
                        | SOUNDDEC list
                        | VISIBILITYDEC boolean
                        | XDEC number
                        | YDEC number
                        | SIZEDEC number
                        | DIRECTIONDEC number
                        | DRAGGABLEDEC boolean
                        | ROTATIONSTYLEDEC STRING
                        | LAYERDEC number"""
    if prod.slice[1].type in ("COSTUMEDEC", "SOUNDDEC"):
        value = prod[2] if isinstance(prod[2], list) else [prod[2]]
    else:
        value = prod[2]

    prod[0] = {
        "lexpos":   prod.lexpos(1),
        "type":     "meta declaration",
        "property": prod[1],
        "value":    value
    }

def p_top_level_statement_list(prod):
    """top_level_statement_list : top_level_statement
                                | top_level_statement top_level_statement_list"""
    if len(prod) == 2:
        prod[0] = [prod[1]]
    else:
        prod[0] = [prod[1]] + prod[2]

def p_top_level_statement(prod):
    """top_level_statement : set_variable SEMICOLON
                           | hat
                           | function_dec"""
    prod[0] = prod[1]

# Inner code statements

def p_fundamental_statement(prod):
    """fundamental_statement : set_variable
                             | in_place_assignment
                             | index_assign
                             | function_call"""
    prod[0] = prod[1]

def p_statement(prod):
    """statement : fundamental_statement SEMICOLON
                 | if
                 | if_else
                 | for
                 | while
                 | return"""
    prod[0] = prod[1]

def p_statement_list(prod):
    """statement_list : statement
                      | statement statement_list"""
    if len(prod) == 2:
        prod[0] = [prod[1]]
    else:
        prod[0] = [prod[1]] + prod[2]

def p_set_variable(prod):
    """set_variable : variable type_declaration EQUALS expression
                    | variable type_declaration EQUALS list"""
    prod[0] = {
        "lexpos":        prod[1]["lexpos"],
        "type":          "assignment",
        "variable":      prod[1],
        "variable type": prod[2],
        "value":         prod[4]
    }

def p_in_place_assignment(prod):
    """in_place_assignment : variable PLUSASSIGN expression
                           | variable MINUSASSIGN expression
                           | variable TIMESASSIGN expression
                           | variable DIVIDEDBYASSIGN expression
                           | variable MODULOASSIGN expression
                           | variable EXPONENTASSIGN expression
                           | variable CONCATASSIGN expression"""
    prod[0] = {
        "lexpos":    prod[1]["lexpos"],
        "type":      "in-place assignment",
        "operation": prod[2],
        "variable":  prod[1],
        "operand":   prod[3]
    }

def p_index_assign(prod):
    """index_assign : index EQUALS expression"""
    prod[0] = {
        "lexpos": prod[1]["lexpos"],
        "type":   "index assign",
        "target": prod[1]["target"],
        "index":  prod[1]["index"],
        "value":  prod[3]
    }

def p_function_call(prod):
    """function_call : variable function_arguments"""
    prod[0] = {
        "lexpos":    prod[1]["lexpos"],
        "type":      "function call",
        "function":  prod[1],
        "arguments": prod[2]
    }

# Data and accessors

def p_number(prod):
    """number : DECIMAL
              | INTEGER"""
    prod[0] = prod[1]

def p_boolean(prod):
    """boolean : TRUE
               | FALSE"""
    prod[0] = (prod[1] == "true")

def p_list(prod):
    """list : LBRACKET expression_list RBRACKET
            | LBRACKET RBRACKET"""
    if len(prod) == 4:
        prod[0] = prod[2]
    else:
        prod[0] = []

def p_variable_list(prod):
    """variable_list : VARIABLE
                     | VARIABLE COMMA variable_list"""
    if len(prod) == 2:
        prod[0] = [prod[1]]
    else:
        prod[0] = [prod[1]] + prod[3]

def p_variable(prod):
    """variable : get_attribute
                | VARIABLE"""
    if isinstance(prod[1], str):
        prod[0] = {
            "lexpos":   prod.lexpos(1),
            "type":     "variable",
            "variable": prod[1]
        }
    else:
        prod[0] = prod[1]

def p_index(prod):
    """index : expression LBRACKET expression RBRACKET"""
    if isinstance(prod[1], dict):
        lexpos = prod[1]["lexpos"]
    elif hasattr(parser.symstack[-1], "lexpos"):
        lexpos = parser.symstack[-1].lexpos
    else:
        lexpos = parser.symstack[-1].value["lexpos"]

    prod[0] = {
        "lexpos": lexpos,
        "type":   "index",
        "target": prod[1],
        "index":  prod[3]
    }

def p_get_attribute(prod):
    """get_attribute : SCRATCH DOT VARIABLE
                     | THIS DOT VARIABLE
                     | VARIABLE DOT VARIABLE
                     | get_attribute DOT VARIABLE"""
    prod[0] = {
        "lexpos":    prod[1]["lexpos"] if isinstance(prod[1], dict) else prod.lexpos(1),
        "type":      "get attribute",
        "object":    prod[1],
        "attribute": prod[3]
    }

def p_expression_list(prod):
    """expression_list : expression
                       | expression COMMA expression_list"""
    if len(prod) == 2:
        prod[0] = [prod[1]]
    else:
        prod[0] = [prod[1]] + prod[3]

def p_expression(prod):
    """expression : number
                  | STRING
                  | boolean
                  | variable
                  | index
                  | function_call
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

# Types

def p_single_type(prod):
    """single_type : NUMTYPE
                   | STRTYPE
                   | BOOLTYPE
                   | VARTYPE"""
    match prod[1]:
        case "num":  prod[0] = Types.NUMBER
        case "str":  prod[0] = Types.STRING
        case "bool": prod[0] = Types.BOOLEAN
        case "var":  prod[0] = Types.GENERAL

def p_type_declaration(prod):
    """type_declaration : COLON single_type
                        | LBRACKET RBRACKET
                        | """
    if len(prod) == 1:
        prod[0] = Types.GENERAL
    elif prod[1] == ":":
        prod[0] = prod[2]
    else:
        prod[0] = Types.LIST

# Operations

def p_concatenation(prod):
    """concatenation : expression CONCAT expression"""
    prod[0] = {
        "lexpos":    prod[1]["lexpos"] if isinstance(prod[1], dict) else prod.lexpos(2),
        "type":      "concatenation",
        "operands":  [prod[1], prod[3]]
    }

def p_numerical_operation(prod):
    """numerical_operation : expression PLUS expression
                           | expression MINUS expression
                           | expression TIMES expression
                           | expression DIVIDEDBY expression
                           | expression MODULO expression
                           | expression EXPONENT expression
                           | MINUS expression %prec UMINUS"""
    prod[0] = {
        "lexpos":    prod[1]["lexpos"] if isinstance(prod[1], dict) else prod.lexpos(2),
        "type":      "numerical operation",
        "operation": prod[2] if len(prod) == 4 else "negation",
        "operands":  [prod[1], prod[3]] if len(prod) == 4 else [prod[2]]
    }

def p_comparison_operation(prod):
    """comparison_operation : expression LESSTHAN expression
                            | expression GREATERTHAN expression
                            | expression LESSTHANEQUAL expression
                            | expression GREATERTHANEQUAL expression
                            | expression EQUALTO expression
                            | expression NOTEQUALTO expression"""
    prod[0] = {
        "lexpos":    prod[1]["lexpos"],
        "type":      "comparison operation",
        "condition": prod[2],
        "operands":  [prod[1], prod[3]]
    }

def p_logical_operation(prod):
    """logical_operation : NOT expression
                         | expression AND expression
                         | expression OR expression
                         | expression IN expression"""
    prod[0] = {"type": "logical operation"}
    if len(prod) == 3:
        prod[0]["lexpos"] = prod.lexpos(1)
        prod[0]["condition"] = prod[1]
        prod[0]["comparands"] = [prod[2]]
    else:
        prod[0]["lexpos"] = prod[1]["lexpos"] if isinstance(prod[1], dict) else prod.lexpos(2)
        prod[0]["condition"] = prod[2]
        prod[0]["comparands"] = [prod[1], prod[3]]

# Control flow

def p_container_body(prod):
    """container_body : statement
                      | LBRACE RBRACE
                      | LBRACE statement_list RBRACE"""
    if len(prod) == 2:
        prod[0] = [prod[1]]
    elif len(prod) == 3:
        prod[0] = []
    else:
        prod[0] = prod[2]

def p_if(prod):
    """if : IF LPAREN expression RPAREN container_body"""
    prod[0] = {
        "lexpos":     prod.lexpos(1),
        "type":       "if",
        "expression": prod[3],
        "body":       prod[5]
    }

def p_if_else(prod):
    """if_else : if ELSE container_body"""
    prod[0] = {
        "lexpos":     prod[1]["lexpos"],
        "type":       "if-else",
        "expression": prod[1]["expression"],
        "body 1":     prod[1]["body"],
        "body 2":     prod[3]
    }

def p_for(prod):
    """for : FOR LPAREN set_variable SEMICOLON expression SEMICOLON fundamental_statement RPAREN container_body"""
    prod[0] = {
        "lexpos":         prod.lexpos(1),
        "type":           "for",
        "initializer":    prod[3],
        "expression":     prod[5],
        "post-iteration": prod[7],
        "body":           prod[9]
    }

def p_while(prod):
    """while : WHILE LPAREN expression RPAREN container_body"""
    prod[0] = {
        "lexpos":     prod.lexpos(1),
        "type":       "while",
        "expression": prod[3],
        "body":       prod[5]
    }

def p_return(prod):
    """return : RETURN SEMICOLON
              | RETURN expression SEMICOLON"""
    if len(prod) == 3:
        expression = None
    else:
        expression = prod[2]

    prod[0] = {
        "lexpos":     prod.lexpos(1),
        "type":       "return",
        "expression": expression
    }

# Functions

def p_function_arguments(prod):
    """function_arguments : LPAREN RPAREN
                          | LPAREN expression_list RPAREN"""
    if len(prod) == 3:
        prod[0] = []
    else:
        prod[0] = prod[2]

def p_function_parameters(prod):
    """function_parameters : LPAREN RPAREN
                           | LPAREN variable_list RPAREN"""
    if len(prod) == 3:
        prod[0] = []
    else:
        prod[0] = prod[2]

def p_function_dec(prod):
    """function_dec : FUNCTION VARIABLE function_parameters container_body
                    | single_type FUNCTION VARIABLE function_parameters container_body
                    | WARP FUNCTION VARIABLE function_parameters container_body
                    | WARP single_type FUNCTION VARIABLE function_parameters container_body"""
    warp = prod[1] == "warp"
    is_long = len(prod) == (7 if warp else 6)

    return_type = prod[2] if warp and is_long else prod[1] if is_long else None
    name        = prod[4] if warp and is_long else prod[3] if is_long or warp else prod[2]
    parameters  = prod[5] if warp and is_long else prod[4] if is_long or warp else prod[3]
    body        = prod[6] if warp and is_long else prod[5] if is_long else prod[4]

    prod[0] = {
        "lexpos":      prod.lexpos(1),
        "type":        "function declaration",
        "return type": return_type,
        "name":        name,
        "parameters":  parameters,
        "warp":        warp,
        "body":        body
    }

def p_hat(prod):
    """hat : variable function_arguments container_body"""
    prod[0] = {
        "lexpos":     prod[1]["lexpos"],
        "type":       "hat",
        "event":      prod[1],
        "arguments":  prod[2],
        "body":       prod[3]
    }

# Parser setup

def p_error(token):
    stack = [sym.type for sym in parser.symstack[1:]]
    state = parser.state
    expected = parser.action[state].keys()
    current_token = token.type if token else "EOF"
    set_lexpos(token.lexpos if token else None)

    if not stack:
        set_lexpos(0)
        code_error("Expected declaration")

    if current_token.endswith("DEC"):
        code_error("Expected declaration value")

    if stack[-1].endswith("DEC"):
        code_error("Invalid declaration value")

    if current_token in reserved.values():
        code_error("Can't use that keyword here")

    if "NUMTYPE" in expected and current_token == "VARIABLE":
        code_error("Invalid variable type")

    if "NUMTYPE" in expected:
        code_error("Expected variable type")

    if stack[-1] == "expression":
        code_error("Unexpected expression")

    if stack[-1] == "DOT":
        code_error("Invalid attribute name")

    if current_token == "RPAREN":
        code_error("Unfinished argument")

    if "SEMICOLON" in expected:
        code_error("Expected semicolon")

    if "BRACE" in current_token:
        code_error("Unexpected brace")

    if current_token == "SEMICOLON" and ("EQUALS" in expected or "STRING" in expected):
        code_error("Expected expression")

    if "FUNCTION" in stack and "VARIABLE" in stack and "LPAREN" in expected:
        code_error("Missing function parentheses")

    if "LPAREN" in expected:
        code_error("Expected parenthesis")

    if "IF" in expected:
        code_error("Expected statement")

    if current_token == "SEMICOLON":
        code_error("Unexpected semicolon")

    print("Uncaught script parsing code_error, please report in the repository")
    print("-" * 50)
    print(f"Syntax code_error at line {token.lineno if token else 'EOF'}")
    print(f"Token: {current_token}")
    print(f"Expected: {', '.join(expected)}")
    print(f"Symbol stack (state {state}): {stack}")

    exit()

debug("Initializing script parser")
parser = yacc.yacc(debug=False, optimize=True)

def parse_file():
    return parser.parse(filestate.read_file(), lexer=lexer)
