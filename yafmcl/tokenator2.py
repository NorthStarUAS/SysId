from sly import Lexer

# examples: https://github.com/amontalenti/compiler/blob/master/exprlex.py

class Tokenator(Lexer):
    # Set of token names.   This is always required
    tokens = {
              # Symbols
              ID,

              # Literals
              FLOAT, INTEGER, STRING, BOOL,

              # Arithmetic
              TIMES, DIVIDE, PLUS, MINUS, EXPONENT,

              # Boolean
              EQ, NE, GTE, LTE, GT, LT,

              # Expressions
              ASSIGN, LPAREN, RPAREN,

              # Syntax
              COMMA, COLON, PIPE,
            }

    # String containing ignored characters between tokens
    ignore = ' \t'

    # Regular expression rules for tokens
    ID      = r'[a-zA-Z_][a-zA-Z0-9_]*'
    TIMES   = r'\*'
    DIVIDE  = r'/'
    PLUS    = r'\+'
    MINUS   = r'-'
    EXPONENT = r'\^'
    EQ      = r'=='
    NE      = r'!='
    GTE     = r'>='
    LTE     = r'<='
    GT      = r'>'
    LT      = r'<'
    ASSIGN  = r'='
    LPAREN  = r'\('
    RPAREN  = r'\)'
    COMMA   = r','
    COLON   = r':'
    PIPE    = r'\|'

    # Define a rule so we can track line numbers
    @_(r'\n+')
    def ignore_newline(self, t):
        self.lineno += len(t.value)
        print("line:", self.lineno)

    # Floating point literals.  ex: 1.23, 1.23e1, 1.23e+1, 1.23e-1, 123., .123, 1e1, 0.
    @_(r'\d+[eE][-+]?\d+|(\.\d+|\d+\.\d*)([eE][-+]?\d+)?')
    def FLOAT(self, t):
        t.value = float(t.value)
        return t

    # Integer literals. ex: 1234, 0x12AF, 0177
    @_(r'0[Xx][\dA-Fa-f]+|0[0-7]+|\d+')
    def INTEGER(self, t):
        if t.value.startswith("0x") or t.value.startswith("0X"):
            print("hex literal:", t.value)
            t.value = int(t.value, 16)
        elif t.value.startswith("0") and not "8" in t.value and not "9" in t.value:
            print("oct literal:", t.value)
            t.value = int(t.value, 8)
        else:
            if t.value.startswith("0"):
                print("Warning: leading zero implies octal literal, but value includes non-octal digits, value is interpreted as a base 10 int:", t.value)
            t.value = int(t.value)
        return t

    # String literals. ex: "abc 'd' efg", 'abc "d" efg'
    @_(r'\".*?\"|\'.*?\'')
    def STRING(self, t):
        return t

if __name__ == '__main__':
    # data = 'x = 3 + 42 * (s - t)'
    data = \
"""
1.23
0x45 01234 08234
1. .2 1.2 1.e-4 .2e6 2.3e-97 42

1 2 +3 -4 +7872098 -123456 987654321
"abc" "g'h'i" "def" 'jk"lm"no'
+ - : >= ">=" / | += *= ^

if a + b:
   y = a or (b and c)
elif d >= n:
   z = 5.0e-5 / (5 ^ 5)
else:
   x_25 = 42

def my_function(a, b=3, c=None):
    return a + b

"""
    lexer = Tokenator()
    for tok in lexer.tokenize(data):
        print('type=%r, value=%r' % (tok.type, tok.value))