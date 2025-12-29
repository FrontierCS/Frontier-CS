class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generates a PoC input that triggers a Heap Use After Free vulnerability
        in libsepol/cil.

        The vulnerability is a double free that occurs during the destruction of the
        CIL Abstract Syntax Tree (AST). It can be triggered by creating a specific
        structure in the CIL policy:

        1.  An anonymous `classpermission` is created. This happens when a
            `classpermission` is used directly in an expression without being
            assigned a name, e.g., `(file (read))`.

        2.  This anonymous `classpermission` is passed as an argument to a macro.

        3.  The macro uses this argument to define a `classpermissionset`. The
            `classpermissionset` stores a pointer to the `classpermission` object.

        During AST destruction, two separate cleanup processes lead to the double
        free:
        - First, a general cleanup function frees all anonymous AST nodes, including
          the `classpermission` created in step 1.
        - Later, the `classpermissionset` defined in the macro is destroyed. Its
          destructor iterates through its members and frees them, attempting to
          free the same `classpermission` object a second time.

        This PoC constructs the minimal CIL code to create this scenario.
        """
        poc = (
            b"(class c (p)) "
            b"(macro m ((classpermission cp)) (classpermissionset s (cp))) "
            b"(call m ((cp (c (p)))))"
        )
        return poc