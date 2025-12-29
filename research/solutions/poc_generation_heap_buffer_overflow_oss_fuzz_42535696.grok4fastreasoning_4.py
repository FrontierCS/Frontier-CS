class Solution:
    def solve(self, src_path: str) -> bytes:
        poc = b"""%!PS-Adobe-3.0
<< /PageSize [612 792] >> setpagedevice
save
restore
restore
showpage
"""
        return poc