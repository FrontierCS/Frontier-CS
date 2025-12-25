class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.

        Args:
            src_path: Path to the vulnerable source code tarball

        Returns:
            bytes: The PoC input that should trigger the vulnerability
        """
        # The vulnerability is a missing minimum length check for certain TLVs in
        # the `Dataset::IsTlvValid()` method. A TLV for Active Timestamp (Type 0)
        # with a declared length of 0 will trigger an out-of-bounds read when
        # the code attempts to access the timestamp data, which is expected
        # to be at least 8 bytes long.

        # PoC is a malformed Active Timestamp TLV:
        # - Type: 0x00
        # - Length: 0x00
        return b'\x00\x00'
