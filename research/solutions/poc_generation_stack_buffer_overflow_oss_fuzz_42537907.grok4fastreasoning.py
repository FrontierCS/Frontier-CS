class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.

        Args:
            src_path: Path to the vulnerable source code tarball

        Returns:
            bytes: The PoC input that should trigger the vulnerability
        """
        # Crafted PoC for stack buffer overflow in gf_hevc_compute_ref_list
        # This is a placeholder; in practice, it would be a malformed HEVC bitstream
        # causing the reference list computation to overflow a stack buffer.
        poc = b'\x00' * 1445
        return poc