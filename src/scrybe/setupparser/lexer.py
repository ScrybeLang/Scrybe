from ply import lex
from ast import literal_eval
from ..scriptparser.lexer import (t_COLON, t_SEMICOLON, t_EQUALS,
                                  t_LPAREN, t_RPAREN, t_LBRACKET, t_RBRACKET, t_COMMA, t_CONCAT,
                                  t_PLUS, t_MINUS, t_TIMES, t_DIVIDEDBY, t_MODULO, t_EXPONENT,
                                  t_LESSTHAN, t_GREATERTHAN, t_LESSTHANEQUAL, t_GREATERTHANEQUAL, t_EQUALTO, t_NOTEQUALTO)

tokens = [
    "VARIABLE", "COLON", "SEMICOLON", "EQUALS", "STRING", "DECIMAL", "INTEGER",
    "LPAREN", "RPAREN", "LBRACKET", "RBRACKET", "COMMA", "CONCAT",
    "PLUS", "MINUS", "TIMES", "DIVIDEDBY", "MODULO", "EXPONENT", "UMINUS",
    "LESSTHAN", "GREATERTHAN", "LESSTHANEQUAL", "GREATERTHANEQUAL", "EQUALTO", "NOTEQUALTO",
    "NEWLINE", "COMMENT"
]

reserved = {
    "project": "PROJECTDEC",
    "as":      "FILENAMEDEC",
    "and":     "AND",
    "or":      "OR",
    "in":      "IN",
    "true":    "TRUE",
    "false":   "FALSE",
    "num":     "NUMTYPE",
    "str":     "STRTYPE",
    "bool":    "BOOLTYPE",
    "var":     "VARTYPE"
}

tokens.extend(reserved.values())

t_EQUALS           = r"\="
t_COLON            = r"\:"
t_SEMICOLON        = r"\;"

t_PLUS             = r"\+"
t_MINUS            = r"\-"
t_TIMES            = r"\*"
t_DIVIDEDBY        = r"\/"
t_MODULO           = r"\%"
t_EXPONENT         = r"\*\*"

t_LESSTHAN         = r"\<"
t_GREATERTHAN      = r"\>"
t_LESSTHANEQUAL    = r"\<\="
t_GREATERTHANEQUAL = r"\>\="
t_EQUALTO          = r"\=\="
t_NOTEQUALTO       = r"\!\="

t_LBRACKET         = r"\["
t_RBRACKET         = r"\]"
t_LPAREN           = r"\("
t_RPAREN           = r"\)"
t_COMMA            = r"\,"

def t_VARIABLE(token):
    r"\b[a-zA-Z_]\w*\b"
    token.type = reserved.get(token.value, "VARIABLE")
    return token

def t_STRING(token):
    r"('(?:[^'\\\n]|\\.)*'|\"(?:[^\"\\\n]|\\.)*\")"
    token.value = literal_eval(token.value)
    return token

def t_DECIMAL(token):
    r"\d*\.\d+"
    token.value = float(token.value)
    return token

def t_INTEGER(token):
    r"0(([xX][\da-fA-F]+)|([oO][0-7]+)|([bB][10]+))|\d+"
    token.value = literal_eval(token.value)
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
