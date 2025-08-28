import re

# Syntax notes:
#
# No escaped characters, illegal: "abc\"def\"ghi", ok: 'abc"def"ghi'
# 'abc' and "abc" are legal string literals
# integers and floating point numbers are standard as expected
# reserved keywords for langauge syntax
# boolean "and" and "or" are spelled out, not handled with c++ style operators.
# not bit-wise operations at this point


class Tokenator():
    def __init__(self):
        self.input_string = ""
        # self.next_input = ""
        self.reset()

    def reset(self):
        self.line_number = 1
        self.character_index = 0
        # self.next_input = self.input_string[self.character_index:]

    def update_index(self, re_match):
        if re_match is not None:
            span = re_match.span()[1] - re_match.span()[0]
            self.character_index += span
            # self.next_input = self.input_string[self.character_index:]

    def set_input_string(self, input_string):
        self.input_string = input_string
        self.reset()

    def set_input_file(self, file_name):
        with open(file_name, "r") as f:
            self.input_string = f.read()
            self.reset()

    def next_token(self):
        input = self.input_string[self.character_index:]
        # print("input:", input)
        # print("input[0]", ord(input[0]))

        # skip leading white space and/or newlines (and count lines)
        done = False
        while not done:
            done = True

            # leading white space
            x = re.search(r"^ +", input)
            if x is not None:
                # print("whitespace...", len(x.group()))
                self.update_index(x)
                input = self.input_string[self.character_index:]
                done = False

            # trailing new line and count line numbers
            # print("input[0]:", ord(input[0]), ord(input[1]))
            x = re.search(r"^\r\n|^\n|^\r", input)
            if x is not None:
                print("end of line")
                self.line_number += 1
                self.update_index(x)
                input = self.input_string[self.character_index:]
                done = False

        # check for end of input
        if input == "":
            return None

        # comment
        pattern = r"^\#.*" # comment
        x = re.search(pattern, input)
        if x is not None:
            comment = x.group()
            self.update_index(x)
            return "comment", comment

        # floating point number variations
        pattern1 = r"^[+-]?\d+\.\d+" # -1.2
        pattern2 = r"^[+-]?\d+\."    # -1.
        pattern3 = r"^[+-]?\.\d+"    # -.1
        pattern = pattern1 + "|" + pattern2 + "|" + pattern3
        x = re.search(pattern, input)
        if x is not None:
            float_number = x.group()
            self.update_index(x)
            input = self.input_string[self.character_index:]
            # check for exponential notation suffix
            x = re.search(r"^[eE][-+]?\d+", input)
            if x is not None:
                exponent = x.group()
                float_number += exponent
                self.update_index(x)
                input = self.input_string[self.character_index:]
            return "fp_number", float_number

        # integer number
        pattern = r"^[+-]?\d+" # -1
        x = re.search(pattern, input)
        if x is not None:
            int_number = x.group()
            self.update_index(x)
            return "int_number", int_number

        # string constants with " (double quotes)
        x = re.search("^\".*?\"", input)
        if x is not None:
            string_constant = x.group()
            self.update_index(x)
            return "string_constant", string_constant[1:-1]

        # string constants with ' (single quotes)
        x = re.search("^'.*?'", input)
        if x is not None:
            string_constant = x.group()
            self.update_index(x)
            return "string_constant", string_constant[1:-1]

        # multi-character operators
        for pattern in ["<=", ">=", "==", "!=", "\+=", "-=", "\*=", "/="]:
            rep = "^" + pattern
            # print("pattern:", rep)
            x = re.search(rep, input)
            if x is not None:
                operator = x.group()
                self.update_index(x)
                return "operator", operator

        # single character operators
        patterns = [":", ",", "(", ")", "[", "]", "{", "}", ">", "<", "=", "+", "-", "*", "/", "^", "%", "|", "&", "."]
        if input[0] in patterns:
            self.character_index += 1
            return "operator", input[0]

        # reserved keywords
        for pattern in ["if", "elif", "else", "def", "return", "and", "or", "True", "False"]:
            rep = "^" + pattern
            # print("rep:", rep)
            x = re.search(rep, input)
            if x is not None:
                keyword = x.group()
                self.update_index(x)
                return "keyword", keyword

        # symbols
        pattern = r"^\w+"
        x = re.search(pattern, input)
        if x is not None:
            symbol = x.group()
            self.update_index(x)
            return "symbol", symbol

        print("Line:", self.line_number, "unknown input token:", input[0:20], "...")

if __name__ == "__main__" and __package__ is None:
    tokenator = Tokenator()
    input = \
"""
0x45
1. .2 1.2 1.e-4 .2e6 2.3e-97 42

1 2 +3 -4 +7872098 -123456 987654321
"abc" "g'h'i" "def" 'jk"lm"no'
+ - : >= ">=" / | += *= ^

if a + b:
   y = a or (b and c)
elif d >= n:
   z = 5.0e-5 / (5 ^ 5)
else:
   x_25 = 42

def my_function(a, b=3, c=None):
    return a + b

"""
    tokenator.set_input_string(input)
    t = tokenator.next_token()
    while t is not None:
        print("line:", tokenator.line_number, t)
        t = tokenator.next_token()

    tokenator.set_input_file("lib/state_mgr.py")
    t = tokenator.next_token()
    while t is not None:
        print("line:", tokenator.line_number, t)
        t = tokenator.next_token()
