from ply import lex
from ..scriptparser.lexer import (t_COLON, t_SEMICOLON, t_EQUALS,
                                  t_STRING, t_DECIMAL, t_INTEGER,
                                  t_LPAREN, t_RPAREN, t_LBRACKET, t_RBRACKET, t_COMMA,
                                  t_PLUS, t_MINUS, t_TIMES, t_DIVIDEDBY, t_MODULO, t_EXPONENT, t_CONCAT,
                                  t_PLUSASSIGN, t_MINUSASSIGN, t_TIMESASSIGN, t_DIVIDEDBYASSIGN, t_MODULOASSIGN, t_EXPONENTASSIGN, t_CONCATASSIGN,
                                  t_LESSTHAN, t_GREATERTHAN, t_LESSTHANEQUAL, t_GREATERTHANEQUAL, t_EQUALTO, t_NOTEQUALTO,
                                  t_NEWLINE, t_COMMENT, t_error, t_ignore)

tokens = [
    "COLON", "SEMICOLON", "VARIABLE", "EQUALS",
    "STRING", "DECIMAL", "INTEGER",
    "LPAREN", "RPAREN", "LBRACKET", "RBRACKET", "DOT", "COMMA",
    "PLUS", "MINUS", "TIMES", "DIVIDEDBY", "MODULO", "EXPONENT", "CONCAT",
    "PLUSASSIGN", "MINUSASSIGN", "TIMESASSIGN", "DIVIDEDBYASSIGN", "MODULOASSIGN", "EXPONENTASSIGN", "CONCATASSIGN",
    "LESSTHAN", "GREATERTHAN", "LESSTHANEQUAL", "GREATERTHANEQUAL", "EQUALTO", "NOTEQUALTO"
]

reserved = {
    "project": "PROJECTDEC",
    "as":      "FILENAMEDEC",
    "not":     "NOT",
    "and":     "AND",
    "or":      "OR",
    "in":      "IN",
    "true":    "TRUE",
    "false":   "FALSE",
    "const":   "CONST",
    "num":     "NUMTYPE",
    "str":     "STRTYPE",
    "bool":    "BOOLTYPE",
    "var":     "VARTYPE"
}

tokens.extend(reserved.values())

def t_SYMBOL(token):
    r"\b[a-zA-Z_]\w*\b"
    token.type = reserved.get(token.value, "VARIABLE")
    return token

lexer = lex.lex()
