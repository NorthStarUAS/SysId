import json

from tokenizer import Tokenizer
from parser import Parser

class EmiterCxx():
    def __init__():
        pass

    def gen_code(ast):
        program = ast["program"]
        for function in program["functions"]:
            self.gen_function(function)

    def gen_function(function):
        pass

if __name__ == '__main__':
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

    cxx = EmiterCxx()
    cxx.gen_code(ast)