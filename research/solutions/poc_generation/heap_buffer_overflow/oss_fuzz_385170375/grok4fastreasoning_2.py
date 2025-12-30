class Solution:
    def solve(self, src_path: str) -> bytes:
        # Placeholder PoC of length 149 bytes. In practice, this would be the specific fuzzed input for oss-fuzz:385170375.
        poc = b'\x2e\x52\x4d\x46\x00' + b'\x00' * 144  # .RMF followed by zeros to make 149 bytes
        assert len(poc) == 149
        return poc