# an attempt to remember how to write a recursive descent parser ... wish me luck!

import json
import types

from tokenizer import Tokenizer

# program        → ( statement | function_def ) *
# function_def   → DEF ID LPAREN ( ID ( COMMA ID)* )? RPAREN COLON BLOCK
#
# block          → statement
#                | INDENT statement ( statement )* DEDENT
# statement      → assign
#                | function_call
#                | conditional
#                | RETURN expression
# assign         → lhs ASSIGN expression
# lhs            → ( ID | array_deref )
# function_call  → ID LPAREN ( expression ( COMMA expression )* )? RPAREN
# array_deref    → ID LBRACE expression RBRACE
# conditional    → IF expression COLON block ( elif expression COLON block )* ( else colon block )?
#
# expression     → equality
# equality       → comparison ( ( "!=" | "==" ) comparison )*
# comparison     → term ( ( ">" | ">=" | "<" | "<=" ) term )*
# term           → factor ( ( "-" | "+" ) factor )*
# factor         → unary ( ( "/" | "*" ) unary )*
# unary          → ( "!" | "-" ) unary
#                | primary
# primary        → INTEGER | FLOAT | STRING | TRUE | FALSE
#                | ID | ID LBRACE expression RBRACE
#                | function_call
#                | "nil"   # fixme nil, arrays
#                | "(" expression ")"

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
            print("match failed:", tokens)
            return False

    def check(self, tokens):
        if self.next().type in tokens:
            return True
        else:
            return False

    def program(self):
        result = {}
        result["op"] = "PROGRAM"
        result["functions"] = []
        result["statements"] = []
        while self.next().type != 'EOF':
            if self.next().type == 'DEF':
                result["functions"].append( self.function_def() )
            else:
                result["statements"].append( self.statement() )
        return result

    def function_def(self):
        result = {}
        param = 0
        result["op"] = "FUNCTION_DEF"
        self.match(['DEF'])
        if self.check(['ID']):
            result["name"] = self.next().value
            self.advance()
            self.match(['LPAREN'])
            print(self.next())
            if not self.check(['RPAREN']):
                print(self.next())
                result["param%d" % param] = self.next().value
                self.advance()
                param += 1
                print(self.next())
            while self.check(['COMMA']):
                print("after comma:", self.next())
                self.advance()
                result["param%d" % param] = self.next().value
                self.advance()
                print("after comma:", self.next())
                param += 1
            self.match(['RPAREN'])
            self.match(['COLON'])
            result["block"] = self.block()
        return result

    def block(self):
        result = {}
        result["op"] = "BLOCK"
        num = 0
        if self.check('INDENT'):
            print("block start")
            self.advance()
            result["statement%d" % num] = self.statement()
            num += 1
            while not self.check('DEDENT'):
                print("no dedent, expecting another statement")
                print("next token is:", self.next().type)
                result["statement%d" % num] = self.statement()
                num +=1
            print("block end")
            print("next token:", self.next().type)
            self.advance()
        else:
            result["statement%d" % num] = self.statement()
        return result

    def statement(self):
        result = {}
        if self.check(['ID']):
            result = self.assign()
        elif self.check(['IF']):
            result = self.conditional()
        elif self.check(['RETURN']):
            self.advance()
            result = {}
            result["op"] = "RETURN"
            result["expression"] = self.expression()
        print("statement:", json.dumps(result, indent="  "))
        return result

    def assign(self):
        print("enter assign")
        result = {}
        result["op"] = "ASSIGN"
        result["left"] = self.lhs()
        self.match(['ASSIGN'])
        result["right"] = self.expression()
        # print("term right:", json.dumps(left))
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
        return result

    def function_call(self):
        result = {}
        param = 0
        result["op"] = "CALL"
        if self.check(['ID']):
            result["name"] = self.next().value
            self.advance()
            self.match(['LPAREN'])
            if not self.check(['RPAREN']):
                result["param%d" % param] = self.expression()
                param += 1
            while self.check(['COMMA']):
                self.advance()
                result["param%d" % param] = self.expression()
                param += 1
            self.match(['RPAREN'])
        else:
            print("error")
        return result

    def array_deref(self):
        result = {}
        param = 0
        result["op"] = "ARRAY_DEREF"
        if self.check(['ID']):
            result["name"] = self.next().value
            self.advance()
            self.match(['LBRACE'])
            result["expression"] = self.expression()
            self.match(['RBRACE'])
        else:
            print("error")
        return result

    def conditional(self):
        result = {}
        result["op"] = "CONDITIONAL"
        num = 0
        self.match(['IF'])
        result["cond%d" % num] = {}
        result["cond%d" % num]["expression"] = self.expression()
        self.match(['COLON'])
        result["cond%d" % num]["block"] = self.block()
        num += 1
        while self.check(['ELIF']):
            print("elif ...")
            self.advance()
            result["cond%d" % num] = {}
            result["cond%d" % num]["expression"] = self.expression()
            self.match(['COLON'])
            result["cond%d" % num]["block"] = self.block()
            num +=1
        if self.check(['ELSE']):
            self.advance()
            self.match(['COLON'])
            result["else"] = self.block()
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
            result = {}
            result["op"] = self.next().type
            self.advance()
            right = self.equality()
            result["left"] = left
            result["right"] = right
            # print("term right:", json.dumps(left))
        else:
            result = left
        # print("equality:", json.dumps(result, indent="  "))
        return result

    def comparison(self):
        # print("comparison:", self.next())
        left = self.term()
        if self.check(['GT', 'GTE', 'LT', 'LTE']):
            result = {}
            result["op"] = self.next().type
            self.advance()
            right = self.comparison()
            result["left"] = left
            result["right"] = right
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
            result = {}
            result["op"] = self.next().type
            self.advance()
            right = self.term()
            result["left"] = left
            result["right"] = right
            # print("term right:", json.dumps(left))
        else:
            result = left
        # print("term:", json.dumps(result, indent="  "))
        return result

    # recurse instead of while
    def factor(self):
        left = self.unary()
        if self.check(['TIMES', 'DIVIDE']):
            result = {}
            result["op"] = self.next().type
            self.advance()
            right = self.factor()
            result["left"] = left
            result["right"] = right
        else:
            result = left
        # print("factor:", result)
        return result

    def unary(self):
        result = {}
        if self.check(['NOT', 'MINUS']):
            result["op"] = self.next().type
            self.advance()
            result["left"] = self.unary()
        else:
            result = self.primary()
        # print("unary:", result)
        return result

    def primary(self):
        result = {}
        if self.check(['INTEGER', 'FLOAT', 'STRING', 'TRUE', 'FALSE']):
            result[self.next().type] = self.next().value
            self.advance()
        elif self.check(['ID']):
            if self.next(1).type == 'LBRACE':
                result = self.array_deref()
            elif self.next(1).type == 'LPAREN':
                result = self.function_call()
            else:
                result[self.next().type] = self.next().value
                self.advance()
        else:
            result = {}
            self.match(['LPAREN'])
            result = self.expression()
            self.match(['RPAREN'])
        # print("primary:", result)
        return result

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
az = import("/sensors/imu/az")

def update(a, b, c):
    if a == b:
        print("hello world")
        print("abc")
    elif c <= e:
        c = d + e
    elif True: x = sin(y)
    else:
        sin(x)
        a["test"] = b[1+2*(3-x)]
    return z

update(az)
"""

    lexer = Tokenizer()
    tokens = list( lexer.tokenize(data) )

    parser = Parser(tokens)
    ast = parser.program()
    print("ast:")
    print(json.dumps(ast, indent="  "))