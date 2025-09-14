# SPCL - Simple Pythonic Control and Logic

This project follows (pretty much mostly?) the standard approach to writing
parsers and compilers.

1. Tokenizer: Slits the input stream up into atomic tokens. This is the first
   step that converts the raw input stream into symbols, key words, int vs.
   float literals, etc.  The tokenizer doesn't care about the order or structure
   of the tokens.

2. Parser:  I have implemented a recursive descent parser (languages are
   recursive.)  This step iterates through the token stream, validates the input
   follows the grammar rules of the language, and builds an abstract syntax tree
   (AST).  The AST captures and represents the recursive structure of the input
   program.  Here we resolve order of operations of expression evaluation and
   separate them out into "binary" (left op right) operations executed in the
   proper order.  The program can be "executed" in proper order by doing a dept
   first traversal of the AST.  The parser does not care about the data types of
   literals and variables, it only ensures the grammar rules are satisfied.

3. Type validator: This step iterates through the abstract syntax Tree (AST) and
   validates the data types of variables and literals.  Here is where the system
   catches if a program attempt to multiply an integer by a string or return a
   floating point number from a function marked as returning a boolean.  Here we
   can build up the block symbol tables dynamically and determin if a variable
   is used before it is defined.

   Because iterating through the AST and type checking the code is so parallel
   to the process of emitting output code, these steps are merged.

4. Emiter: Currently the output target is C++ code.  In some future time frame
   I'm interested in developing an interpreter so the output would be byte code.
   This is still a hobby project and I'm puzzling my way through the steps.  In
   the back of my head as I'm designging and building forwards, I am trying to
   allow for this to also be a script language.
