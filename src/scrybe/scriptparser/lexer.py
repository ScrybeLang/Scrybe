from ply import lex
from ast import literal_eval
from ..logger import logger

error = logger.error

tokens = [
    "SPRITENAMEDEC", "COSTUMEDEC", "SOUNDDEC", "XDEC", "YDEC", "VISIBILITYDEC", "SIZEDEC", "DIRECTIONDEC", "DRAGGABLEDEC", "ROTATIONSTYLEDEC", "LAYERDEC",
    "SEMICOLON", "VARIABLE", "SYMBOL", "EQUALS",
    "STRING", "NUMBER",
    "LPAREN", "RPAREN", "LBRACKET", "RBRACKET", "LBRACE", "RBRACE", "DOT", "COMMA", "CONCAT",
    "PLUS", "MINUS", "TIMES", "DIVIDEDBY", "MODULO", "EXPONENT", "UMINUS",
    "PLUSASSIGN", "MINUSASSIGN", "TIMESASSIGN", "DIVIDEDBYASSIGN", "MODULOASSIGN", "EXPONENTASSIGN",
    "LESSTHAN", "GREATERTHAN", "LESSTHANEQUAL", "GREATERTHANEQUAL", "EQUALTO", "NOTEQUALTO",
    "NEWLINE", "COMMENT"
]

reserved = {
    "scratch":  "SCRATCH",
    "this":     "THIS",
    "not":      "NOT",
    "and":      "AND",
    "or":       "OR",
    "in":       "IN",
    "if":       "IF",
    "else":     "ELSE",
    "for":      "FOR",
    "while":    "WHILE",
    "true":     "TRUE",
    "false":    "FALSE",
    "warp":     "WARP",
    "function": "FUNCTION",
    "return":   "RETURN"
}

tokens.extend(reserved.values())

t_SPRITENAMEDEC       = r"\#name"
t_COSTUMEDEC          = r"\#costume"
t_SOUNDDEC            = r"\#sound"
t_VISIBILITYDEC       = r"\#visible"
t_XDEC                = r"\#x"
t_YDEC                = r"\#y"
t_SIZEDEC             = r"\#size"
t_DIRECTIONDEC        = r"\#direction"
t_DRAGGABLEDEC        = r"\#draggable"
t_ROTATIONSTYLEDEC    = r"\#rotationstyle"
t_LAYERDEC            = r"\#layer"

t_SEMICOLON           = r"\;"
t_EQUALS              = r"\="

t_LPAREN              = r"\("
t_RPAREN              = r"\)"
t_LBRACKET            = r"\["
t_RBRACKET            = r"\]"
t_LBRACE              = r"\{"
t_RBRACE              = r"\}"
t_DOT                 = r"\."
t_COMMA               = r"\,"
t_CONCAT              = r"\.\."

t_PLUS                = r"\+"
t_MINUS               = r"\-"
t_TIMES               = r"\*"
t_DIVIDEDBY           = r"\/"
t_MODULO              = r"\%"
t_EXPONENT            = r"\*\*"

t_PLUSASSIGN          = r"\+="
t_MINUSASSIGN         = r"\-="
t_TIMESASSIGN         = r"\*="
t_DIVIDEDBYASSIGN     = r"\/="
t_MODULOASSIGN        = r"\%="
t_EXPONENTASSIGN      = r"\*\*="

t_LESSTHAN            = r"\<"
t_GREATERTHAN         = r"\>"
t_LESSTHANEQUAL       = r"\<="
t_GREATERTHANEQUAL    = r"\>="
t_EQUALTO             = r"\=="
t_NOTEQUALTO          = r"\!="

def t_SYMBOL(token):
    r"\b[a-zA-Z_]\w*\b"
    token.type = reserved.get(token.value, "VARIABLE")
    return token

def t_STRING(token):
    r"('(?:[^'\\\n]|\\.)*'|\"(?:[^\"\\\n]|\\.)*\")"
    token.value = literal_eval(token.value)
    return token

def t_NUMBER(token):
    r"[-\+]?\d+(\.\d+)?"
    if float(token.value) % 1 == 0:
        token.value = int(token.value)
    else:
        token.value = float(token.value)
    return token

def t_NEWLINE(token):
    r"\n"
    token.lexer.lineno += 1

def t_COMMENT(_):
    r"\/\/.*"

def t_error(token):
    if token.value[0] in ("'", '"'):
        error(token.lexpos, "String not closed")

    error(token.lexpos, "Invalid character")

t_ignore = " \t"

lexer = lex.lex()
