from sly import Lexer  # dnf install python3-sly; pip install --break-system-packages git+https://github.com/dabeaz/sly.git

# examples: https://github.com/amontalenti/compiler/blob/master/exprlex.py

# python style indent syntax:
#   https://github.com/dabeaz/ply/blob/master/example/GardenSnake/GardenSnake.py
#   http://dalkescientific.com/writings/diary/archive/2006/08/30/gardensnake_language.html

class Tokenizer(Lexer):
    # Set of token names.   This is always required
    tokens = {
              # Literals
              FLOAT, INTEGER, STRING, BOOLEAN,

              # Arithmetic
              TIMES, DIVIDE, PLUS, MINUS, EXPONENT,

              # Boolean
              EQ, NE, GTE, LTE, GT, LT, NOT,

              # Expressions
              ASSIGN, LPAREN, RPAREN, LBRACE, RBRACE,

              # Syntax
              COMMA, COLON, ARROW, PIPE,
              INDENT, DEDENT,
              COMMENT,

              # Symbols
              ID, TYPE,

              # Keywords
              DEF, RETURN,
              IF, ELIF, ELSE

            }

    # String containing ignored characters between tokens
    # ignore = ' \t'

    # Regular expression rules for tokens
    ARROW   = r'->'
    EXPONENT = r'\^'
    EQ      = r'=='
    NE      = r'!='
    GTE     = r'>='
    LTE     = r'<='
    GT      = r'>'
    LT      = r'<'
    NOT     = r'\!'
    ASSIGN  = r'='
    LPAREN  = r'\('
    RPAREN  = r'\)'
    LBRACE  = r'\['
    RBRACE  = r'\]'
    COMMA   = r','
    COLON   = r':'
    PIPE    = r'\|'
    TIMES   = r'\*'
    DIVIDE  = r'/'
    PLUS    = r'\+'
    MINUS   = r'-'

    ID      = r'[a-zA-Z_][a-zA-Z0-9_]*'
    ID["def"] = DEF
    ID["return"] = RETURN
    ID["if"] = IF
    ID["elif"] = ELIF
    ID["else"] = ELSE
    ID["True"] = BOOLEAN
    ID["False"] = BOOLEAN
    ID["int"] = TYPE
    ID["float"] = TYPE
    ID["string"] = TYPE
    ID["bool"] = TYPE

    # # Define a rule so we can track line numbers
    # @_(r'\n+')
    # def ignore_newline(self, t):
    #     self.lineno += len(t.value)
    #     print("line:", self.lineno)

    # Define a rule so we can track line numbers
    @_(r'\n[ \t]*\n')
    def EMPTY_LINE(self, t):
        self.lineno += 2
        print("empty line:", self.lineno)

    # Define a rule so we can track line numbers
    last_indent = 0
    @_(r'\n[ \t]*')
    def LEADING_WHITESPACE(self, t):
        self.lineno += 1
        indent = len(t.value)-1
        print("indent:", indent, "line:", self.lineno)
        if indent > self.last_indent:
            t.type = 'INDENT'
            t.value = indent
            self.last_indent = indent
            return t
        elif indent < self.last_indent:
            t.type = 'DEDENT'
            t.value = indent
            self.last_indent = indent
            return t

    @_(r'[ \t]+')
    def IGNORE_WHITESPACE(self, t):
        print("ignored whitespace ...")
        pass

    # Floating point literals.  ex: 1.23, 1.23e1, 1.23e+1, 1.23e-1, 123., .123, 1e1, 0.
    @_(r'\d+[eE][-+]?\d+',
       r'(\.\d+|\d+\.\d*)([eE][-+]?\d+)?')
    def FLOAT(self, t):
        t.value = float(t.value)
        return t

    # Integer literals. ex: 1234, 0x12AF, 0177
    @_(r'0[Xx][\dA-Fa-f]+',
       r'0[0-7]+',
       r'\d+')
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
    @_(r'\".*?\"',
       r'\'.*?\'')
    def STRING(self, t):
        return t

    # Whitespace indent (python style)
    @_(r'[ \t]+')
    def INDENT(self, t):
        return t

    # Comment (python / bash style)
    @_(r'\#.*')
    def COMMENT(self, t):
        print("ignoring comment")
        # return t

if __name__ == '__main__':
    # data = 'x = 3 + 42 * (s - t)'
    data = \
"""
1.23
0x45 01234 08234



1. .2 1.2 1.e-4 .2e6 2.3e-97 42
     # indented comment
# comment
1 2 +3 -4 +7872098 -123456 987654321
"abc" "g'h'i" "def" 'jk"lm"no'
+ - : >= ">=" / | += *= ^    # comment to end of line

# comment

if a + b:    # comment
   y = a or (b and c)
elif d >= n:
   z = 5.0e-5 / (5 ^ 5)
else:
   x_25 = 42

def my_function(a, b=3, c=None):
    return a + b

"""
    tokenator = Tokenizer()
    for token in tokenator.tokenize(data):
        print('type=%r, value=%r' % (token.type, token.value), token)