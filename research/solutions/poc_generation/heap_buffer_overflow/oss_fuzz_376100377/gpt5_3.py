import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        sdp_lines = [
            "v=0",
            "o=- 0 0 IN IP4 127.0.0.1",
            "s=-",
            "t=0 0",
            "c=IN IP4 127.0.0.1",
            "m=video 54312 RTP/AVP 96",
            "a=rtpmap:96 H264/90000",
            "a=rtcp:9 IN IP4 0.0.0.0",
            "a=fmtp:96 profile-level-id="
        ]
        # Join with CRLF, but ensure there is no trailing CRLF after the last line
        sdp = ("\r\n".join(sdp_lines)).encode("ascii")
        return sdp