from ply import lex
from ast import literal_eval

tokens = [
    "VARIABLE", "EQUALS", "SEMICOLON",
    "STRING", "NUMBER",
    "PLUS", "MINUS", "TIMES", "DIVIDEDBY", "MODULO", "EXPONENT", "UMINUS",
    "LESSTHAN", "GREATERTHAN", "LESSTHANEQUAL", "GREATERTHANEQUAL", "EQUALTO", "NOTEQUALTO",
    "LBRACKET", "RBRACKET", "LPAREN", "RPAREN", "COMMA",
    "NEWLINE", "COMMENT"
]

reserved = {
    "project": "PROJECTDEC",
    "as":      "FILENAMEDEC",
    "and":     "AND",
    "or":      "OR",
    "true":    "TRUE",
    "false":   "FALSE"
}

tokens.extend(reserved.values())

t_EQUALS           = r"="
t_SEMICOLON        = r";"

t_PLUS             = r"\+"
t_MINUS            = r"-"
t_TIMES            = r"\*"
t_DIVIDEDBY        = r"/"
t_MODULO           = r"%"
t_EXPONENT         = r"\*\*"

t_LESSTHAN         = r"<"
t_GREATERTHAN      = r">"
t_LESSTHANEQUAL    = r"<="
t_GREATERTHANEQUAL = r">="
t_EQUALTO          = r"=="
t_NOTEQUALTO       = r"!="

t_LBRACKET         = r"\["
t_RBRACKET         = r"\]"
t_LPAREN           = r"\("
t_RPAREN           = r"\)"
t_COMMA            = r","

def t_VARIABLE(token):
    r"\b[a-zA-Z_]\w*\b"
    token.type = reserved.get(token.value, "VARIABLE")
    return token

def t_STRING(token):
    r"('(?:[^'\\\n]|\\.)*'|\"(?:[^\"\\\n]|\\.)*\")"
    token.value = literal_eval(token.value)
    return token

def t_NUMBER(token):
    r"[-+]?\d+(\.\d+)?"
    token.value = float(token.value)
    return token

def t_NEWLINE(token):
    r"\n"
    token.lexer.lineno += 1

def t_COMMENT(token):
    r"\/\/.*"

def t_error(token):
    ...

t_ignore = " \t"

lexer = lex.lex()
