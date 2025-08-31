# an attempt to remember how to write a recursive descent parser ... wish me luck!

import json
import types

from tokenator2 import Tokenator

# statement      → assignment ( assignment )*
# assignment     → ID ( ASSIGN expression )*

# function       → ID LPAREN ( expression ( COMMA expression )* )? RPAREN

# expression     → equality
# equality       → comparison ( ( "!=" | "==" ) comparison )*
# comparison     → term ( ( ">" | ">=" | "<" | "<=" ) term )*
# term           → factor ( ( "-" | "+" ) factor )*
# factor         → unary ( ( "/" | "*" ) unary )*
# unary          → ( "!" | "-" ) unary
#                | primary
# primary        → NUMBER | STRING | ID | function | "true" | "false" | "nil"
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

    def function(self):
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

    def expression(self):
        # print("expression:", self.next())
        result = self.equality()
        print("expression:", json.dumps(result, indent="  "))
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
        if self.check(['INTEGER', 'FLOAT', 'BOOL', 'STRING']):
            result[self.next().type] = self.next().value
            self.advance()
        elif self.check(['ID']):
            if self.next(1).type != 'LPAREN':
                result[self.next().type] = self.next().value
                self.advance()
            else:
                result = self.function()
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


    lexer = Tokenator()
    tokens = list( lexer.tokenize(data) )

    parser = Parser(tokens)
    parser.expression()
