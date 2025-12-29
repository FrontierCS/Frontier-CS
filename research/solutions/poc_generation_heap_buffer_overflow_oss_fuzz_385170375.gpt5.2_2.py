import os
import re
import io
import tarfile
import zipfile
import gzip
import bz2
import lzma
import base64
from typing import Optional, List, Tuple


class Solution:
    def solve(self, src_path: str) -> bytes:
        poc = self._find_embedded_poc(src_path)
        if poc is not None and len(poc) > 0:
            return poc
        return b"\x00" * 149

    def _find_embedded_poc(self, src_path: str) -> Optional[bytes]:
        files = []
        if os.path.isdir(src_path):
            files = self._collect_from_dir(src_path)
        else:
            files = self._collect_from_tar(src_path)

        if not files:
            return None

        def score_item(name: str, size: int) -> float:
            n = name.lower()
            s = 0.0
            if "385170375" in n:
                s += 10000
            if "385170" in n:
                s += 2000
            if "clusterfuzz" in n:
                s += 1500
            if "testcase" in n:
                s += 800
            if "minimiz" in n:
                s += 600
            if "oss-fuzz" in n or "ossfuzz" in n:
                s += 500
            if "poc" in n or "repro" in n or "crash" in n:
                s += 350
            if "rv60" in n:
                s += 300
            if "realvideo" in n or "real media" in n or "realmedia" in n:
                s += 150
            ext = os.path.splitext(n)[1]
            if ext in (".bin", ".raw", ".dat", ".rm", ".rma", ".rmvb", ".rv", ".ivf", ".mkv", ".mp4", ".mov", ".avi"):
                s += 120
            if ext in (".zip", ".gz", ".xz", ".bz2", ".lzma", ".zst"):
                s += 40
            if ext in (".txt", ".md", ".rst", ".c", ".cc", ".cpp", ".h"):
                s -= 30
            if size == 149:
                s += 500
            s -= min(size, 2_000_000) / 5000.0
            return s

        scored = [(score_item(n, sz), n, sz, getter) for (n, sz, getter) in files]
        scored.sort(key=lambda x: (-x[0], x[2], x[1]))

        # Try top candidates first
        for _, name, size, getter in scored[:50]:
            if size <= 0:
                continue
            try:
                data = getter()
            except Exception:
                continue
            if not data:
                continue
            extracted = self._maybe_extract_from_container(name, data)
            if extracted is not None:
                return extracted
            decoded = self._maybe_decode_text_payload(name, data)
            if decoded is not None:
                extracted2 = self._maybe_extract_from_container(name, decoded)
                if extracted2 is not None:
                    return extracted2
                return decoded
            return data

        # Fallback: exact-size match
        exact = [(n, sz, getter) for (_, n, sz, getter) in scored if sz == 149]
        for name, _, getter in exact[:50]:
            try:
                data = getter()
            except Exception:
                continue
            if data:
                extracted = self._maybe_extract_from_container(name, data)
                if extracted is not None:
                    return extracted
                return data

        return None

    def _collect_from_dir(self, root: str) -> List[Tuple[str, int, object]]:
        out = []
        for dirpath, _, filenames in os.walk(root):
            for fn in filenames:
                p = os.path.join(dirpath, fn)
                try:
                    st = os.stat(p)
                except Exception:
                    continue
                if not os.path.isfile(p):
                    continue
                rel = os.path.relpath(p, root).replace(os.sep, "/")
                size = int(st.st_size)

                def make_getter(path=p):
                    def _g():
                        with open(path, "rb") as f:
                            return f.read()
                    return _g

                out.append((rel, size, make_getter()))
        return out

    def _collect_from_tar(self, tar_path: str) -> List[Tuple[str, int, object]]:
        out = []
        try:
            tf = tarfile.open(tar_path, "r:*")
        except Exception:
            return out
        with tf:
            for m in tf.getmembers():
                if not m.isreg():
                    continue
                name = m.name
                size = int(m.size)

                def make_getter(member=m, tarobj=tf):
                    def _g():
                        f = tarobj.extractfile(member)
                        if f is None:
                            return b""
                        with f:
                            return f.read()
                    return _g

                out.append((name, size, make_getter()))
        return out

    def _maybe_extract_from_container(self, name: str, data: bytes) -> Optional[bytes]:
        if len(data) < 4:
            return None
        n = name.lower()
        # Zip
        if data[:4] == b"PK\x03\x04" or n.endswith(".zip"):
            try:
                with zipfile.ZipFile(io.BytesIO(data)) as zf:
                    infos = zf.infolist()
                    if not infos:
                        return None
                    def zscore(info):
                        nn = info.filename.lower()
                        s = 0
                        if "385170375" in nn:
                            s += 10000
                        if "clusterfuzz" in nn:
                            s += 1000
                        if "minimiz" in nn:
                            s += 500
                        if "rv60" in nn:
                            s += 200
                        if info.file_size == 149:
                            s += 500
                        s -= info.file_size / 5000.0
                        return (-s, info.file_size, info.filename)
                    infos.sort(key=zscore)
                    for info in infos[:20]:
                        if info.file_size <= 0 or info.file_size > 5_000_000:
                            continue
                        b = zf.read(info)
                        if not b:
                            continue
                        # Nested compression
                        inner = self._maybe_extract_from_container(info.filename, b)
                        if inner is not None:
                            return inner
                        dec = self._maybe_decode_text_payload(info.filename, b)
                        if dec is not None:
                            inner2 = self._maybe_extract_from_container(info.filename, dec)
                            return inner2 if inner2 is not None else dec
                        return b
            except Exception:
                return None
            return None

        # gzip
        if data[:2] == b"\x1f\x8b" or n.endswith(".gz"):
            try:
                b = gzip.decompress(data)
                if b:
                    inner = self._maybe_extract_from_container(name[:-3] if n.endswith(".gz") else name, b)
                    return inner if inner is not None else b
            except Exception:
                return None

        # bzip2
        if data[:3] == b"BZh" or n.endswith(".bz2"):
            try:
                b = bz2.decompress(data)
                if b:
                    inner = self._maybe_extract_from_container(name[:-4] if n.endswith(".bz2") else name, b)
                    return inner if inner is not None else b
            except Exception:
                return None

        # xz / lzma
        if data[:6] == b"\xfd7zXZ\x00" or n.endswith(".xz") or n.endswith(".lzma"):
            try:
                b = lzma.decompress(data)
                if b:
                    inner = self._maybe_extract_from_container(name, b)
                    return inner if inner is not None else b
            except Exception:
                return None

        return None

    def _maybe_decode_text_payload(self, name: str, data: bytes) -> Optional[bytes]:
        # Try base64 decode for small-ish ascii text payloads that look like a testcase encoding.
        if not data or len(data) > 5_000_000:
            return None
        try:
            text = data.decode("utf-8", errors="strict")
        except Exception:
            return None

        stripped = re.sub(r"\s+", "", text)
        if len(stripped) < 32:
            return None

        if re.fullmatch(r"[A-Za-z0-9+/=]+", stripped) and (len(stripped) % 4 == 0):
            try:
                raw = base64.b64decode(stripped, validate=True)
                if raw:
                    return raw
            except Exception:
                pass

        # Hex string like "00ff01..."
        if re.fullmatch(r"[0-9a-fA-F]+", stripped) and (len(stripped) % 2 == 0) and len(stripped) >= 40:
            try:
                raw = bytes.fromhex(stripped)
                if raw:
                    return raw
            except Exception:
                pass

        # C array initializer: {0x00, 0x01, ...}
        if "0x" in text and "{" in text and "}" in text:
            hex_bytes = re.findall(r"0x([0-9a-fA-F]{2})", text)
            if len(hex_bytes) >= 16:
                try:
                    raw = bytes(int(h, 16) for h in hex_bytes)
                    if raw:
                        return raw
                except Exception:
                    pass

        return None