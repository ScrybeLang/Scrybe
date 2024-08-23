from ply import yacc
from .lexer import lexer, tokens, reserved
from .. import filestate
from .. import utils
from ..logger import code_error, set_lexpos

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

def p_single_statement(prod):
    """single_statement : set_variable
                        | in_place_assignment
                        | index_assign
                        | function_call"""
    prod[0] = prod[1]

def p_statement(prod):
    """statement : single_statement SEMICOLON
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

def p_number(prod):
    """number : DECIMAL
              | INTEGER"""
    print(prod.slice)
    prod[0] = prod[1]

def p_boolean(prod):
    """boolean : TRUE
               | FALSE"""
    prod[0] = (prod[1] == "true")

def p_expression_list(prod):
    """expression_list : expression
                       | expression COMMA expression_list"""
    if len(prod) == 2:
        prod[0] = [prod[1]]
    else:
        prod[0] = [prod[1]] + prod[3]

def p_variable_list(prod):
    """variable_list : VARIABLE
                     | VARIABLE COMMA variable_list"""
    if len(prod) == 2:
        prod[0] = [prod[1]]
    else:
        prod[0] = [prod[1]] + prod[3]

def p_list(prod):
    """list : LBRACKET expression_list RBRACKET
            | LBRACKET RBRACKET"""
    if len(prod) == 4:
        prod[0] = prod[2]
    else:
        prod[0] = []

def p_variable(prod):
    """variable : attribute_of
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
    prod[0] = {
        "lexpos": prod[1]["lexpos"],
        "type":   "index",
        "target": prod[1],
        "index":  prod[3]
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

def p_attribute_of(prod):
    """attribute_of : SCRATCH DOT VARIABLE
                    | THIS DOT VARIABLE
                    | VARIABLE DOT VARIABLE
                    | attribute_of DOT VARIABLE"""
    prod[0] = {
        "lexpos":    prod[1]["lexpos"] if isinstance(prod[1], dict) else prod.lexpos(1),
        "type":      "get attribute",
        "object":    prod[1],
        "attribute": prod[3]
    }

def p_concatenation(prod):
    """concatenation : expression CONCAT expression"""
    prod[0] = {
        "lexpos": prod[1]["lexpos"] if isinstance(prod[1], dict) else prod.lexpos(2),
        "type":   "concatenation",
        "one":    prod[1],
        "two":    prod[3]
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
                  | function_call
                  | condition
                  | concatenation
                  | STRING
                  | number
                  | variable
                  | index"""
    if len(prod) == 2:
        prod[0] = prod[1]
    elif len(prod) == 3:
        # Unary minus
        if utils.is_number(prod[2]):
            # Unary minus on a number is just negation ._.
            prod[0] = -float(prod[2])
        else:
            prod[0] = {
                "lexpos":     prod[2]["lexpos"],
                "type":       "unary minus",
                "expression": prod[2]
            }
    else:
        if prod[1] == "(" and prod[3] == ")":
            # Expression wrapped in parentheses
            prod[0] = prod[2]
        else:
            prod[0] = {
                "lexpos":    prod[1]["lexpos"] if isinstance(prod[1], dict) else prod.lexpos(2),
                "type":      "binary operation",
                "operation": prod[2],
                "operand 1": prod[1],
                "operand 2": prod[3]
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

def p_set_variable(prod):
    """set_variable : variable EQUALS expression
                    | variable EQUALS list"""
    prod[0] = {
        "lexpos":   prod[1]["lexpos"],
        "type":     "assignment",
        "variable": prod[1],
        "value":    prod[3]
    }

def p_function_call(prod):
    """function_call : variable function_arguments"""
    prod[0] = {
        "lexpos":    prod[1]["lexpos"],
        "type":      "function call",
        "function":  prod[1],
        "arguments": prod[2]
    }

def p_condition(prod):
    """condition : expression LESSTHAN expression
                 | expression GREATERTHAN expression
                 | expression LESSTHANEQUAL expression
                 | expression GREATERTHANEQUAL expression
                 | expression EQUALTO expression
                 | expression NOTEQUALTO expression
                 | expression AND expression
                 | expression OR expression
                 | expression IN expression
                 | NOT expression
                 | boolean"""
    if len(prod) == 4:
        prod[0] = {
            "lexpos":      prod[1]["lexpos"] if isinstance(prod[1], dict) else prod.lexpos(2),
            "type":        "condition",
            "condition":   prod[2],
            "comparand 1": prod[1],
            "comparand 2": prod[3]
        }
    elif len(prod) == 3:
        prod[0] = {
            "lexpos":    prod[2]["lexpos"] if isinstance(prod[2], dict) else prod.lexpos(1),
            "type":      "condition",
            "condition": "not",
            "comparand": prod[2]
        }
    else:
        prod[0] = prod[1]

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
    """for : FOR LPAREN set_variable SEMICOLON expression SEMICOLON single_statement RPAREN container_body"""
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

def p_hat(prod):
    """hat : variable function_arguments container_body"""
    prod[0] = {
        "lexpos":     prod[1]["lexpos"],
        "type":       "hat",
        "event":      prod[1],
        "arguments":  prod[2],
        "body":       prod[3]
    }

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

def p_function_dec(prod):
    """function_dec : FUNCTION VARIABLE function_parameters container_body
                    | WARP FUNCTION VARIABLE function_parameters container_body"""
    if len(prod) == 5:
        name = prod[2]
        parameters = prod[3]
        warp = False
        body = prod[4]
    else:
        name = prod[3]
        parameters = prod[4]
        warp = True
        body = prod[5]

    prod[0] = {
        "lexpos":     prod.lexpos(1),
        "type":       "function declaration",
        "name":       name,
        "parameters": parameters,
        "warp":       warp,
        "body":       body
    }

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

parser = yacc.yacc(debug=False, optimize=True, errorlog=utils.NullBuffer)

def parse_file(file_path):
    filestate.open_file(file_path)
    ast = parser.parse(filestate.read_file(), lexer=lexer)
    filestate.close_file()

    return ast
