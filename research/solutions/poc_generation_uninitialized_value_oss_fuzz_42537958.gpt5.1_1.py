import typing


def _build_huffman_table(bits: typing.List[int], huffval: typing.List[int]) -> typing.Dict[int, typing.Tuple[int, int]]:
    # Based on JPEG spec / IJG implementation
    huffsize = []
    for l in range(1, 17):
        for _ in range(bits[l - 1]):
            huffsize.append(l)
    huffsize.append(0)

    huffcode = []
    code = 0
    k = 0
    si = huffsize[0]
    while True:
        while huffsize[k] == si:
            huffcode.append(code)
            code += 1
            k += 1
        if huffsize[k] == 0:
            break
        while huffsize[k] != si:
            code <<= 1
            si += 1

    table: typing.Dict[int, typing.Tuple[int, int]] = {}
    for i, sym in enumerate(huffval):
        table[sym] = (huffcode[i], huffsize[i])
    return table


def _build_minimal_jpeg() -> bytes:
    parts = bytearray()

    # SOI
    parts += b"\xff\xd8"

    # APP0 JFIF
    parts += b"\xff\xe0"
    parts += (16).to_bytes(2, "big")  # length (includes these 2 bytes)
    parts += b"JFIF\x00"  # identifier
    parts += b"\x01\x01"  # version 1.1
    parts += b"\x00"      # units: 0 (no units)
    parts += b"\x00\x01"  # X density
    parts += b"\x00\x01"  # Y density
    parts += b"\x00\x00"  # no thumbnail

    # DQT (one 8-bit table, all ones)
    qt = [1] * 64
    parts += b"\xff\xdb"
    parts += (2 + 1 + 64).to_bytes(2, "big")  # length
    parts += b"\x00"  # Pq=0 (8-bit), Tq=0
    parts += bytes(qt)

    # SOF0 (baseline, 1x1, 1 component - grayscale)
    parts += b"\xff\xc0"
    parts += (2 + 1 + 2 + 2 + 1 + 3).to_bytes(2, "big")  # length
    parts += b"\x08"              # precision = 8
    parts += (1).to_bytes(2, "big")  # height
    parts += (1).to_bytes(2, "big")  # width
    parts += b"\x01"              # number of components
    parts += b"\x01"              # component ID 1
    parts += b"\x11"              # H=1, V=1
    parts += b"\x00"              # uses quant table 0

    # DHT for DC (minimal: only symbol 0, length 1 -> code '0')
    bits_dc = [1] + [0] * 15  # one code of length 1
    val_dc = [0]              # category 0
    parts += b"\xff\xc4"
    parts += (2 + 1 + 16 + len(val_dc)).to_bytes(2, "big")
    parts += b"\x00"  # class=0 (DC), id=0
    parts += bytes(bits_dc)
    parts += bytes(val_dc)

    # DHT for AC (minimal: only EOB symbol 0x00, length 2 -> code '00')
    bits_ac = [0, 1] + [0] * 14  # one code of length 2
    val_ac = [0x00]              # EOB
    parts += b"\xff\xc4"
    parts += (2 + 1 + 16 + len(val_ac)).to_bytes(2, "big")
    parts += b"\x10"  # class=1 (AC), id=0
    parts += bytes(bits_ac)
    parts += bytes(val_ac)

    # SOS
    parts += b"\xff\xda"
    parts += (2 + 1 + 2 + 3).to_bytes(2, "big")  # length
    parts += b"\x01"  # number of components in scan
    parts += b"\x01"  # component ID 1
    parts += b"\x00"  # uses DC table 0, AC table 0
    parts += b"\x00"  # Ss
    parts += b"\x3f"  # Se
    parts += b"\x00"  # Ah/Al

    # Build Huffman tables to get codes
    dc_table = _build_huffman_table(bits_dc, val_dc)
    ac_table = _build_huffman_table(bits_ac, val_ac)
    dc_code, dc_len = dc_table[0]       # DC category 0
    eob_code, eob_len = ac_table[0x00]  # AC EOB

    # Build bit sequence: DC(0) then EOB
    bits_seq = []
    for i in range(dc_len - 1, -1, -1):
        bits_seq.append((dc_code >> i) & 1)
    for i in range(eob_len - 1, -1, -1):
        bits_seq.append((eob_code >> i) & 1)

    # Pack bits into bytes with 1-padding and byte stuffing after 0xFF
    cur = 0
    bit_count = 0
    data_bytes = bytearray()
    for b in bits_seq:
        cur = (cur << 1) | b
        bit_count += 1
        if bit_count == 8:
            data_bytes.append(cur)
            if cur == 0xFF:
                data_bytes.append(0x00)
            cur = 0
            bit_count = 0

    if bit_count > 0:
        # Pad remaining bits with 1s as per JPEG spec
        cur = (cur << (8 - bit_count)) | ((1 << (8 - bit_count)) - 1)
        data_bytes.append(cur)
        if cur == 0xFF:
            data_bytes.append(0x00)

    parts += data_bytes

    # EOI
    parts += b"\xff\xd9"

    return bytes(parts)


class Solution:
    def solve(self, src_path: str) -> bytes:
        # Prefix a few configuration bytes to handle fuzzers that
        # interpret initial bytes as parameters before the JPEG data.
        jpeg = _build_minimal_jpeg()
        prefix = b"\x00\x00\x00\x00"
        return prefix + jpeg