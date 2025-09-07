# Symbol Table and Function Table

class SymbolTable():
    def __init__(self):
        self.symbols = {}

    def add(self, name, data_type):
        self.symbols["name"] = data_type

    def check(self, name):
        return name in self.symbols

    def get_type(self, name):
        if name in self.symbols:
            return self.symbols(name)
        else:
            return None