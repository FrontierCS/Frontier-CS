import os


class Solution:
    def solve(self, src_path: str) -> bytes:
        def be16(n: int) -> bytes:
            return bytes([(n >> 8) & 0xFF, n & 0xFF])

        def add_segment(buf: bytearray, marker: int, payload: bytes) -> None:
            buf.append(0xFF)
            buf.append(marker & 0xFF)
            length = len(payload) + 2
            buf.extend(be16(length))
            buf.extend(payload)

        buf = bytearray()

        # SOI
        buf.extend(b"\xFF\xD8")

        # APP0 (JFIF)
        app0 = bytearray()
        app0.extend(b"JFIF\x00")      # Identifier
        app0.extend(b"\x01\x01")      # Version 1.01
        app0.append(0x00)             # Units: 0 = none
        app0.extend(be16(1))          # X density
        app0.extend(be16(1))          # Y density
        app0.append(0x00)             # X thumbnail
        app0.append(0x00)             # Y thumbnail
        add_segment(buf, 0xE0, bytes(app0))

        # DQT (Quantization table 0, all ones)
        dqt = bytearray()
        dqt.append(0x00)              # Pq=0 (8-bit), Tq=0
        dqt.extend([1] * 64)          # 8x8 table, all ones
        add_segment(buf, 0xDB, bytes(dqt))

        # SOF0 (Baseline DCT, 3 components, 8x8 image)
        sof0 = bytearray()
        sof0.append(8)                # Sample precision
        height = 8
        width = 8
        sof0.extend(be16(height))     # Number of lines
        sof0.extend(be16(width))      # Number of samples per line
        sof0.append(3)                # Number of components (Y, Cb, Cr)

        # Component 1: Y
        sof0.append(1)                # Component ID
        sof0.append(0x11)             # H=1, V=1
        sof0.append(0)                # Quant table 0

        # Component 2: Cb
        sof0.append(2)                # Component ID
        sof0.append(0x11)             # H=1, V=1
        sof0.append(0)                # Quant table 0

        # Component 3: Cr
        sof0.append(3)                # Component ID
        sof0.append(0x11)             # H=1, V=1
        sof0.append(0)                # Quant table 0

        add_segment(buf, 0xC0, bytes(sof0))

        # DHT (Define minimal DC and AC Huffman tables, both table 0)
        dht = bytearray()

        # DC table 0: single symbol (category 0) with 1-bit code
        dht.append(0x00)              # Tc=0 (DC), Th=0
        bits_dc = [1] + [0] * 15      # One code of length 1
        dht.extend(bits_dc)
        dht.append(0x00)              # Huffman value: 0 (category 0)

        # AC table 0: single symbol (EOB 0x00) with 1-bit code
        dht.append(0x10)              # Tc=1 (AC), Th=0
        bits_ac = [1] + [0] * 15      # One code of length 1
        dht.extend(bits_ac)
        dht.append(0x00)              # Huffman value: 0x00 (EOB)

        add_segment(buf, 0xC4, bytes(dht))

        # SOS (Start of Scan: 3 components, single interleaved scan)
        sos = bytearray()
        sos.append(3)                 # Number of components in scan

        # Component 1: Y uses DC/AC table 0
        sos.append(1)                 # Component ID
        sos.append(0x00)              # Td=0, Ta=0

        # Component 2: Cb
        sos.append(2)
        sos.append(0x00)

        # Component 3: Cr
        sos.append(3)
        sos.append(0x00)

        sos.append(0x00)              # Ss (start of spectral selection)
        sos.append(0x3F)              # Se (end of spectral selection)
        sos.append(0x00)              # Ah/Al (successive approximation)

        add_segment(buf, 0xDA, bytes(sos))

        # Entropy-coded data:
        # One MCU, 3 components, each one 8x8 block:
        # For each block: DC diff = 0 (category 0), AC coefficients all zero -> EOB.
        # DC symbol 0 has code '0', AC EOB also '0'; 2 bits per block.
        # 3 blocks * 2 bits = 6 bits; pad to full byte with zeros.
        buf.append(0x00)

        # EOI
        buf.extend(b"\xFF\xD9")

        return bytes(buf)
