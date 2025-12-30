import os
import sys

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.

        Args:
            src_path: Path to the vulnerable source code tarball

        Returns:
            bytes: The PoC input that should trigger the vulnerability
        """
        # The vulnerability, identified in binutils bug #18615, is a stack buffer
        # overflow in the `print_branch` function of `opcodes/tic30-dis.c`.
        # It occurs when disassembling a malformed parallel branch instruction.
        #
        # A 32-bit instruction word composed of repeating 0x0c bytes (i.e., 0x0c0c0c0c)
        # is misinterpreted. The disassembler logic for parallel instructions correctly
        # identifies two operands (one from the high 16 bits, one from the low 16 bits),
        # filling two slots in a local operand array.
        #
        # Due to a logic flaw (lack of a proper `else` block), the code execution
        # falls through to the non-parallel instruction parsing logic. This logic
        # re-parses the entire 32-bit word and finds a third operand.
        #
        # The attempt to store this third operand into the operand array, which is
        # only sized for two entries (`char op[2][10]`), results in an out-of-bounds
        # write, causing the stack buffer overflow.
        #
        # The PoC consists of the byte 0x0c repeated 10 times. The first four bytes
        # form the malicious instruction. The extra bytes ensure the program does not
        # encounter a premature EOF during subsequent reads, allowing the sanitizer to
        # reliably detect the crash upon the function's return.
        return b'\x0c' * 10