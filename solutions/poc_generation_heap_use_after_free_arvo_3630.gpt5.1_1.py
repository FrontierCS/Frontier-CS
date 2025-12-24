import os


class Solution:
    def solve(self, src_path: str) -> bytes:
        return b"+proj=longlat +ellps=WGS84\n+proj=lsat +lsat=0 +path=0\n"
