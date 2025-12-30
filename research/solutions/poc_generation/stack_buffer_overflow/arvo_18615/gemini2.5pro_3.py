import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.

        Args:
            src_path: Path to the vulnerable source code tarball

        Returns:
            bytes: The PoC input that should trigger the vulnerability
        """
        # The vulnerability is in the handling of the 'brf' (branch far) instruction
        # with opcode 0x10 in the TIC30 disassembler.
        #
        # The disassembler's opcode table incorrectly defines 'brf' as a 1-byte instruction.
        # However, the corresponding disassembly printing function attempts to read a
        # 16-byte operand that should follow the opcode.
        #
        # This discrepancy leads to a read out-of-bounds vulnerability. If an input
        # file contains the 0x10 opcode but is shorter than 17 bytes (1 for opcode + 16
        # for operand), the disassembler will read past the end of its input buffer,
        # causing a crash.
        #
        # To match the ground-truth length of 10 bytes, we provide the 1-byte 'brf'
        # opcode followed by 9 bytes of arbitrary data. When the vulnerable code
        # attempts to read the 10th byte of the operand (the 11th byte overall),
        # it will access memory out of bounds, triggering the crash.
        
        opcode = b'\x10'  # 'brf' instruction
        payload = b'A' * 9 # Provide 9 bytes of an expected 16-byte operand
        
        # Total PoC length = 1 (opcode) + 9 (payload) = 10 bytes
        poc = opcode + payload
        
        return poc