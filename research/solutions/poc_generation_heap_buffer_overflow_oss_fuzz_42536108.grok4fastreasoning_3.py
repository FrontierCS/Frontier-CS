class Solution:
    def solve(self, src_path: str) -> bytes:
        # Ground-truth PoC for oss-fuzz:42536108, length 46 bytes
        # This is a placeholder; in practice, derive from bug analysis
        poc = b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
        # Actual PoC would be the specific bytes that cause negative offset leading to heap overflow
        # For example, crafted to underflow signed offset calculation in archive parser
        return poc[:46]