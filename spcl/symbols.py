# Symbol Table and Function Table

class SymbolTable():
    def __init__(self):
        self.symbols = {}

    def add(self, name, data_type):
        self.symbols[name] = data_type

    def check(self, name):
        return name in self.symbols

    def get_type(self, name):
        if name in self.symbols:
            return self.symbols[name]
        else:
            return None

class FunctionTable():
    def __init__(self):
        self.symbols = {}
        self.symbols["print"] = {"type": "bool", "params": "any"}
        self.symbols["cos"] = {"type": "float", "params": [{"type": "float"}]}
        self.symbols["sin"] = {"type": "float", "params": [{"type": "float"}]}

    def add(self, name, data_type, parameter_list):
        self.symbols[name] = {"type": data_type, "params": parameter_list}

    def check(self, name):
        return name in self.symbols

    def get_type(self, name):
        if name in self.symbols:
            return self.symbols[name]["type"]
        else:
            print("Unknown function:", name)
            return None

    def get_params(self, name):
        if name in self.symbols:
            return self.symbols[name]["params"]
        else:
            print("Unknown function:", name)
            return []