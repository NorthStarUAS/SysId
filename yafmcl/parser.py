# an attempt to remember how to write a recursive descent parser ... wish me luck!

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
        print("term:", self.next())
        self.factor()
        while self.match(['PLUS', 'MINUS']):
            self.factor()

    def factor(self):
        print("factor:", self.next())
        self.unary()
        while self.match(['TIMES', 'DIVIDE']):
            self.unary()

    def unary(self):
        print("unary:", self.next())
        if self.match(["!", "-"]):
            self.unary()
        else:
            self.primary()

    def primary(self):
        print("primary:", self.next())
        if self.check(['INTEGER', 'FLOAT', 'BOOLEAN', 'STRING', 'ID']):
            result = self.next()
            self.advance()
        else:
            self.match(['LPAREN'])
            result = self.expression()
            self.match(['RPAREN'])
        return result

if __name__ == '__main__':

    data = """c * (a + b)
        e
    """

    data = """a + b * c"""


    lexer = Tokenator()
    tokens = list( lexer.tokenize(data) )

    parser = Parser(tokens)
    parser.expression()

    lexer.ASSIGN
