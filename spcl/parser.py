# an attempt to remember how to write a recursive descent parser ... wish me luck!

from copy import deepcopy
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

# Types: int, float (double), string, bool
# Strict type checking, no implicit int->float type promotion.

from symbols import SymbolTable, FunctionTable
global_symbols = SymbolTable()
global_funcs = FunctionTable()

def compare_types(sym, a, b):
    if a is None or b is None:
        return None
    elif a == b:
        return a
    else:
        # print("Type mismatch:", a, b)
        return None

def resolve_types_expr(sym, expression):
    # print("expression:", expression)
    if "INTEGER" in expression:
        return "int"
    elif "FLOAT" in expression:
        return "float"
    elif "STRING" in expression:
        return "string"
    elif "BOOLEAN" in expression:
        return "bool"
    elif "op" in expression:
        op = expression["op"]
        lineno = expression["lineno"]
        left = resolve_types_expr(sym, expression["left"])
        right = resolve_types_expr(sym, expression["right"])
        result = compare_types(sym, left, right)
        if result is None:
            print("Type mismatch in expression line:", lineno, left, op, right)
        if op in ["EQ", "NE", "GT", "LT", "GTE", "LTE", "NOT"]:
            result = "bool"
        return result
    elif "call" in expression:
        return resolve_types_call(sym, expression["call"])
    elif "ID" in expression or "array_deref" in expression:
        if "array_deref" in expression:
            id = expression["array_deref"]["name"]
            lineno = expression["array_deref"]["lineno"]
            index_type = resolve_types_expr(sym, expression["array_deref"]["expr"])
            if index_type != "int":
                print("array index type must resolve to an integer type.")
        elif "ID" in expression:
            id = expression["ID"]
            lineno = expression["lineno"]
        if sym.check(id):
            print(id, sym.get_type(id))
            return sym.get_type(id)
        else:
            print("Symbol %s used before definition.  Line %d" % (id, lineno))
            # print("symbol table:", sym.symbols)
    elif "list" in expression:
        result = ""
        for item in expression["list"]["items"]:
            tmp = resolve_types_expr(sym, item)
            print("item:", item, "type:", tmp)
            if result == "":
                result = tmp
            else:
                if result != tmp:
                    print("Mismatched types in list on line: %d  %s vs %s" % (expression["list"]["lineno"], result, tmp))
        return result;
    else:
        print("unhandled expression:", expression)

def resolve_types_call(sym, call):
    calling_params = call["params"]
    function_params = global_funcs.get_params(call["name"])
    if type(function_params) is str and function_params == "any":
        # ok
        print("calling:", call["name"], "with any parameters ok.")
    elif len(calling_params) == len(function_params):
        # print("call:", call)
        for i in range(len(calling_params)):
            # print("  params %d" % i, function_params[i])
            p1 = resolve_types_expr(sym, call["params"][i])
            p2 = function_params[i]["type"]
            if p1 != p2:
                print("Parameter type mismatch in function call on line:", call["lineno"], "%s()" % call["name"], "parameter:", i, p1, "vs", p2)
                break
    else:
        print("Wrong number of parameters in function call on line:", call["lineno"], "%s()" % call["name"], len(function_params), "vs", len(calling_params))
    return global_funcs.get_type(call["name"])

def resolve_types_statement(sym, statement, function_type):
    # statements do not propagate a type up the syntax tree
    if "conditional" in statement:
        for c in statement["conditional"]:
            e = c["expression"]
            result = resolve_types_expr(sym, e)
            sub_sym = deepcopy(sym)  # variable assignments in this block aren't visible outside.
            for s in c["statements"]:
                result = resolve_types_statement(sub_sym, s, function_type)
    elif "assign" in statement:
        # print("assign right:", statement["assign"])
        lhs = statement["assign"]["left"]
        if "ID" in lhs:
            lhs_id = lhs["ID"]
        elif "array_deref" in lhs:
            lhs_id = lhs["array_deref"]["name"]
            index_type = resolve_types_expr(sym, lhs["array_deref"]["expr"])
            if index_type != "int":
                print("array index type must resolve to an integer type.")
        right = resolve_types_expr(sym, statement["assign"]["right"])
        lineno = statement["assign"]["lineno"]
        if sym.check(lhs_id):
            lhs_type = sym.get_type(lhs_id)
            if lhs_type != right:
                print("Type mismatch in expression line:", lineno, lhs_id, "=", right)
        else:
            sym.add(lhs_id, right)
    elif "call" in statement:
        resolve_types_call(sym, statement["call"])
        # calling_params = c["params"]
        # function_params = global_funcs.get_params(c["name"])
        # if type(function_params) is str and function_params == "any":
        #     # ok
        #     print("calling:", c["name"], "with any parameters ok.")
        #     pass
        # elif len(calling_params) == len(function_params):
        #     print("c:", c)
        #     for i in range(len(calling_params)):
        #         p1 = resolve_types_expr(sym, c["params"][i])
        #         p2 = function_params[i]["type"]
        #         if p1 != p2:
        #             print("Parameter type mismatch in function call on line:", c["lineno"], "%s()" % c["name"], "parameter:", i, p1, "vs", p2)
        #             break
        # else:
        #             print("Wrong number of parameters in function call on line:", c["lineno"], "%s()" % c["name"], len(function_params), "vs", len(calling_params))
    elif "return" in statement:
        result = resolve_types_expr(sym, statement["return"])
        if result != function_type:
            print("function of type: %s returns type: %s" % (function_type, result))
        else:
            print("function of type: %s returns the correct type!" % function_type)
    else:
        print("unhandled statement:", statement)

def resolve_types(ast):
    p = ast["program"]
    for f in p["functions"]:
        id = f["ID"]
        return_type = f["TYPE"]
        sym = SymbolTable()
        for param in f["parameters"]:
            key = next(iter(param))
            sym.add(key, param[key])
        for statement in f["statements"]:
            result = resolve_types_statement(sym, statement, return_type)
        global_funcs.add(id, return_type, f["parameters"])
    for statement in p["statements"]:
        result = resolve_types_statement(sym, statement, None)

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

    resolve_types(ast)