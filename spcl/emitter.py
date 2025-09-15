from copy import deepcopy
import json

from tokenizer import Tokenizer
from parser import Parser

class EmitterCxx():
    def __init__():
        pass

    def gen_code(self, ast):
        program = ast["program"]
        for function in program["functions"]:
            self.gen_function(function)

    def gen_function(self, function):
        pass

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
            print("symbol table:", sym.symbols)
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
            sym.add(param["id"], param["type"])
        print("function:", sym.symbols)
        for statement in f["statements"]:
            result = resolve_types_statement(sym, statement, return_type)
        global_funcs.add(id, return_type, f["parameters"])
    for statement in p["statements"]:
        result = resolve_types_statement(sym, statement, None)

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