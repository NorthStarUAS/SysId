# an attempt to remember how to write a recursive descent parser ... wish me luck!

import json
import types

from tokenator2 import Tokenator

# expression     → equality ;
# equality       → comparison ( ( "!=" | "==" ) comparison )* ;
# comparison     → term ( ( ">" | ">=" | "<" | "<=" ) term )* ;
# term           → factor ( ( "-" | "+" ) factor )* ;
# factor         → unary ( ( "/" | "*" ) unary )* ;
# unary          → ( "!" | "-" ) unary
#                | primary ;
# primary        → NUMBER | STRING | "true" | "false" | "nil"
#                | "(" expression ")" ;

class Parser():
    def __init__(self, tokens):
        self.tokens = tokens
        self.current_token = 0
        print("tokens:", self.tokens)

    # advance to the next token
    def advance(self):
        self.current_token += 1

    def next(self):
        if self.current_token < len(self.tokens):
            result = self.tokens[self.current_token]
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
            return False

    def check(self, tokens):
        if self.next().type in tokens:
            return True
        else:
            return False

    def expression(self):
        print("expression:", self.next())
        return self.equality()

    def equality(self):
        print("equality:", self.next())
        self.comparison()
        while self.match(["!=", "=="]):
            self.comparison()

    def comparison(self):
        print("comparison:", self.next())
        self.term()
        while self.match([">", ">=", "<", "<="]):
            self.term()

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
        print("term:", json.dumps(result, indent="  "))
        return result

    # def factor(self):
    #     print("factor:", self.next())
    #     self.unary()
    #     while self.match(['TIMES', 'DIVIDE']):
    #         self.unary()

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
        print("factor:", result)
        return result

    def unary(self):
        result = {}
        if self.check(['NOT', 'MINUS']):
            result["op"] = self.next().type
            self.advance()
            result["left"] = self.unary()
        else:
            result = self.primary()
        print("unary:", result)
        return result

    def primary(self):
        result = {}
        if self.check(['INTEGER', 'FLOAT', 'BOOL', 'STRING', 'ID']):
            result[self.next().type] = self.next().value
            self.advance()
        else:
            result = {}
            self.match(['LPAREN'])
            result = self.expression()
            self.match(['RPAREN'])
        print("primary:", result)
        return result

if __name__ == '__main__':

    data = """c * (-a + b)
        e
    """

    data = """a + b * -c * d / f + 2"""


    lexer = Tokenator()
    tokens = list( lexer.tokenize(data) )

    parser = Parser(tokens)
    parser.expression()

    lexer.ASSIGN
