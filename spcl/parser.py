# an attempt to remember how to write a recursive descent parser ... wish me luck!

import json
import types

from tokenizer import Tokenizer

# program        → ( statement | function ) *
# function       → DEF ID LPAREN ( ID COLON type_specifier ( COMMA ID COLON type_specifyer)* )? RPAREN ARROW type_specifier COLON BLOCK
# type_specifier → ( INT | FLOAT | STRING | BOOL )
#
# block          → statement
#                | INDENT statement ( statement )* DEDENT
# statement      → assign
#                | call
#                | conditional
#                | RETURN expression
# assign         → lhs ASSIGN expression
# lhs            → ( ID | array_deref )
# call           → ID LPAREN ( expression ( COMMA expression )* )? RPAREN
# conditional    → IF expression COLON block ( elif expression COLON block )* ( else colon block )?
#
# expression     → equality
# equality       → comparison ( ( "!=" | "==" ) comparison )*
# comparison     → term ( ( ">" | ">=" | "<" | "<=" ) term )*
# term           → factor ( ( "-" | "+" ) factor )*
# factor         → unary ( ( "/" | "*" ) unary )*
# unary          → ( "!" | "-" ) unary
#                | primary
# primary        → ID
#                | array_deref
#                | list
#                | call
#                | "(" expression ")"
#                | literal
#                | "nil"   # fixme nil
# array_deref    → ID LBRACE expression RBRACE
# list           → LBRACE ( expression ( COMMA expression )* )? RBRACE
# literal        → INTEGER | FLOAT | STRING | BOOLEAN

class Parser():
    def __init__(self, tokens):
        self.tokens = tokens
        self.current_token = 0
        print("tokens:", self.tokens)

    # advance to the next token
    def advance(self):
        self.current_token += 1

    def next(self, n=0):
        if self.current_token + n < len(self.tokens):
            result = self.tokens[self.current_token + n]
        else:
            result = types.SimpleNamespace()
            result.type = 'EOF'
            result.value = None
        return result

    # test if next token is in the given list
    def match(self, tokens):
        if self.next().type in tokens:
            print("match:", self.next())
            self.advance()
            return True
        else:
            print("match failed, looking for:", tokens, "found:", self.next())
            return False

    def check(self, tokens):
        if self.next().type in tokens:
            return True
        else:
            return False

    def program(self):
        functions = []
        statements = []
        while self.next().type != 'EOF':
            if self.next().type == 'DEF':
                functions.append( self.function() )
            else:
                statements.append( self.statement() )
        result = {"program": {"functions": functions, "statements": statements}}
        return result

    def function(self):
        params = []
        self.match(['DEF'])
        if self.check(['ID']):
            function_name = self.next().value
            self.advance()
            self.match(['LPAREN'])
            print(self.next())
            if not self.check(['RPAREN']):
                print("first param:", self.next())
                id = self.next().value
                self.advance()
                self.match(['COLON'])
                if self.check(['TYPE']):
                    param_type = self.next().value
                self.advance()
                params.append({"id": id, "type": param_type})
                print(self.next())
            while self.check(['COMMA']):
                print("after comma:", self.next())
                self.advance()
                id = self.next().value
                self.advance()
                self.match(['COLON'])
                if self.check(['TYPE']):
                    param_type = self.next().value
                self.advance()
                params.append({"id": "id", "type": param_type})
                print("after comma:", self.next())
            self.match(['RPAREN'])
            self.match(['ARROW'])
            if self.check(['TYPE']):
                function_type = self.next().value
            self.advance()
            self.match(['COLON'])
            statements = self.block()
        print(id)
        result = {"ID": function_name, "TYPE": function_type, "parameters": params, "statements": statements}
        return result

    def block(self):
        statements = []
        if self.check('INDENT'):
            print("block start")
            self.advance()
            statements.append(self.statement())
            while not self.check('DEDENT'):
                print("no dedent, expecting another statement")
                print("next token is:", self.next().type)
                statements.append(self.statement())
            print("block end")
            print("next token:", self.next().type)
            self.advance()
        else:
            statements.append(self.statement())
        result = statements
        return result

    def statement(self):
        if self.check(['ID']):
            if self.next(1).type == 'LPAREN':
                result = self.call()
            else:
                result = self.assign()
        elif self.check(['IF']):
            result = self.conditional()
        elif self.check(['RETURN']):
            self.advance()
            expr = self.expression()
            result = {"return": expr}
        print("statement:", json.dumps(result, indent="  "))
        return result

    def assign(self):
        print("enter assign")
        left = self.lhs()
        lineno = self.next().lineno
        self.match(['ASSIGN'])
        right = self.expression()
        result = {"assign": {"left": left, "right": right, "lineno": lineno}}
        return result

    def lhs(self):
        print("enter lhs")
        if self.check(['ID']):
            if self.next(1).type == 'LBRACE':
                result = self.array_deref()
            else:
                result = {}
                result[self.next().type] = self.next().value
                self.advance()
            return result
        else:
            print("error")

    def call(self):
        params = []
        if self.check(['ID']):
            name = self.next().value
            lineno = self.next().lineno
            self.advance()
            self.match(['LPAREN'])
            if not self.check(['RPAREN']):
                params.append(self.expression())
            while self.check(['COMMA']):
                self.advance()
                params.append(self.expression())
            self.match(['RPAREN'])
        else:
            print("error")
        result = {"call": {"name": name, "params": params, "lineno": lineno}}
        return result

    def conditional(self):
        conditionals = []
        self.match(['IF'])
        expr = self.expression()
        self.match(['COLON'])
        statements = self.block()
        conditionals.append({"expression": expr, "statements": statements})
        while self.check(['ELIF']):
            print("elif ...")
            self.advance()
            expr = self.expression()
            self.match(['COLON'])
            statements = self.block()
            conditionals.append({"expression": expr, "statements": statements})
        if self.check(['ELSE']):
            self.advance()
            self.match(['COLON'])
            expr = {"BOOLEAN": "True"}
            statements = self.block()
            conditionals.append({"expression": expr, "statements": statements})
        result = {"conditional": conditionals}
        return result

    def expression(self):
        # print("expression:", self.next())
        result = self.equality()
        # print("expression:", json.dumps(result, indent="  "))
        return result

    def equality(self):
        # print("equality:", self.next())
        left = self.comparison()
        if self.check(['EQ', 'NEQ']):
            op = self.next().type
            lineno = self. next().lineno
            self.advance()
            right = self.equality()
            result = {"op": op, "lineno": lineno, "left": left, "right": right}
            # print("term right:", json.dumps(left))
        else:
            result = left
        # print("equality:", json.dumps(result, indent="  "))
        return result

    def comparison(self):
        # print("comparison:", self.next())
        left = self.term()
        if self.check(['GT', 'GTE', 'LT', 'LTE']):
            op = self.next().type
            lineno = self. next().lineno
            self.advance()
            right = self.comparison()
            result = {"op": op, "lineno": lineno, "left": left, "right": right}
            # print("term right:", json.dumps(left))
        else:
            result = left
        # print("comparison:", json.dumps(result, indent="  "))
        return result

    def term(self):
        # print("term:", self.next())
        left = self.factor()
        # print("term left:", json.dumps(left))
        if self.check(['PLUS', 'MINUS']):
            op = self.next().type
            lineno = self. next().lineno
            self.advance()
            right = self.term()
            result = {"op": op, "lineno": lineno, "left": left, "right": right}
            # print("term right:", json.dumps(left))
        else:
            result = left
        # print("term:", json.dumps(result, indent="  "))
        return result

    # recurse instead of while
    def factor(self):
        left = self.unary()
        if self.check(['TIMES', 'DIVIDE']):
            op = self.next().type
            lineno = self. next().lineno
            self.advance()
            right = self.factor()
            result = {"op": op, "lineno": lineno, "left": left, "right": right}
        else:
            result = left
        # print("factor:", result)
        return result

    def unary(self):
        result = {}
        if self.check(['NOT', 'MINUS']):
            op = self.next().type
            lineno = self.next().lineno
            self.advance()
            left = self.unary()
            result = {"op": op, "lineno": lineno, "left": left}
        else:
            result = self.primary()
        # print("unary:", result)
        return result

    def primary(self):
        if self.check(['ID']):
            if self.next(1).type == 'LBRACE':
                result = self.array_deref()
            elif self.next(1).type == 'LPAREN':
                result = self.call()
            else:
                result = {self.next().type: self.next().value, "lineno": self.next().lineno}
                self.advance()
        elif self.check(['LBRACE']):
            result = self.list()
        elif self.check(['LPAREN']):
            self.match(['LPAREN'])
            result = self.expression()
            self.match(['RPAREN'])
        else:
            result = self.literal()
        # print("primary:", result)
        return result

    def array_deref(self):
        if self.check(['ID']):
            name = self.next().value
            lineno = self.next().lineno
            self.advance()
            self.match(['LBRACE'])
            expr = self.expression()
            self.match(['RBRACE'])
            result = {"array_deref": {"name": name, "expr": expr, "lineno": lineno}}
        else:
            print("error")
        return result

    def list(self):
        items = []
        lineno = self.next().lineno
        self.match(['LBRACE'])
        if not self.check(['RBRACE']):
            items.append(self.expression())
        while self.check(['COMMA']):
            self.advance()
            items.append(self.expression())
        self.match(['RBRACE'])
        result = {"list": {"items": items, "lineno": lineno}}
        return result

    def literal(self):
        if self.check(['INTEGER', 'FLOAT', 'STRING', 'BOOLEAN']):
            result = {self.next().type: self.next().value, "lineno": self.next().lineno}
            self.advance()
            return result
        else:
            print("error")



if __name__ == '__main__':

    data = """c * (-a + b)
        e
    """

    data = """(a + b * -c * d / f + 2 <= 25 - 2 == g)"""

    data = """a + sin(x) + 2*cos(y, 3-x, (4+sin(z)))"""

    data = "a = a1 = a2 = b + c = d * e()"
    data = "d = print(abc)"

    data = """if a == b:
    print("hello world")
    print("abc")
elif c <= e:
    c = d + e
else:
    sin(x)
"""

    data = """
az = getDouble("/sensors/imu/az")

def update(a: int, b: float, c: bool) -> bool:
    y = 2.0
    z = 3.0
    if a == 2.0:
        print("hello world")
        print("abc")
    elif c <= e:
        c = d + e
    elif True: x = sin(y+z)
    else:
        sin(x)
        a["test"] = b[1+2*(3-x)]
    return z
    return y > z

vals = [1, 2, 3, 4.0, "test", cos(x), sin(y/z)]
vals[2+3*(4-x)] = 2.0
update(1, 2., True)
"""

    lexer = Tokenizer()
    tokens = list( lexer.tokenize(data) )

    parser = Parser(tokens)
    ast = parser.program()
    print("ast:")
    print(json.dumps(ast, indent="  "))
