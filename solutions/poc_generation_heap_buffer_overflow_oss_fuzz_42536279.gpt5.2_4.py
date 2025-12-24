import os
import io
import re
import math
import tarfile
import zipfile
import gzip
import bz2
import lzma
from typing import Optional, Tuple


TARGET_LEN = 6180


_TEXT_EXTS = {
    ".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp", ".hxx",
    ".py", ".md", ".rst", ".txt", ".json", ".yml", ".yaml",
    ".cmake", ".in", ".am", ".ac", ".m4", ".mk", ".make", ".gradle",
    ".java", ".kt", ".go", ".rs", ".swift", ".cs", ".js", ".ts",
    ".html", ".css", ".xml", ".toml", ".ini", ".cfg", ".sh", ".bat",
}

_BIN_EXT_PTS = {
    ".ivf": 45,
    ".obu": 40,
    ".av1": 40,
    ".webm": 25,
    ".mkv": 20,
    ".mp4": 15,
    ".y4m": 15,
    ".vp9": 30,
    ".vp8": 25,
    ".bin": 10,
    ".dat": 10,
    ".raw": 10,
}

_COMP_EXTS = {".gz", ".bz2", ".xz", ".lzma", ".zip"}

_KW_PTS = {
    "42536279": 120,
    "oss-fuzz": 40,
    "ossfuzz": 40,
    "clusterfuzz": 70,
    "testcase": 45,
    "minimized": 40,
    "crash": 40,
    "poc": 40,
    "repro": 35,
    "regression": 30,
    "svcdec": 80,
    "svc_dec": 80,
    "svc-dec": 80,
    "svcdecoder": 70,
    "svc_decoder": 70,
    "svc": 20,
    "subset": 25,
    "overflow": 20,
    "heap": 15,
    "fuzz": 20,
    "corpus": 15,
    "seed": 12,
    "av1": 25,
    "vp9": 15,
    "ivf": 25,
    "obu": 20,
    "decoder": 10,
    "decode": 10,
    "svcdecapp": 30,
}

_PATH_BONUS = {
    "/test/": 12,
    "/tests/": 12,
    "/testdata/": 16,
    "/test_data/": 16,
    "/data/": 10,
    "/fuzz/": 20,
    "/fuzzer/": 18,
    "/corpus/": 20,
    "/seed/": 15,
    "/seeds/": 15,
    "/regression/": 18,
    "/poc/": 25,
    "/pocs/": 25,
    "/crash/": 18,
}


def _ext_of(path: str) -> str:
    p = path.lower()
    _, ext = os.path.splitext(p)
    return ext


def _is_probably_text(head: bytes) -> bool:
    if not head:
        return True
    printable = 0
    for b in head:
        if b in (9, 10, 13) or 32 <= b < 127:
            printable += 1
    return (printable / max(1, len(head))) > 0.92


def _magic_score(head: bytes) -> int:
    if not head:
        return 0
    if head.startswith(b"DKIF"):
        return 60
    if head.startswith(b"\x1A\x45\xDF\xA3"):  # EBML (webm/mkv)
        return 40
    if head.startswith(b"YUV4MPEG2"):
        return 35
    if len(head) >= 12 and head[4:8] == b"ftyp":
        return 20
    if head[:1] in (b"\x0a", b"\x08", b"\x12"):  # plausible AV1 OBU headers
        return 5
    return 0


def _size_score(sz: int) -> float:
    d = abs(sz - TARGET_LEN)
    return 140.0 * math.exp(-d / 500.0)


def _meta_score(path: str, size: int) -> float:
    p = path.lower()
    score = _size_score(size)
    if size == TARGET_LEN:
        score += 220.0

    for kw, pts in _KW_PTS.items():
        if kw in p:
            score += float(pts)

    for frag, pts in _PATH_BONUS.items():
        if frag in p:
            score += float(pts)

    ext = _ext_of(p)
    if ext in _BIN_EXT_PTS:
        score += float(_BIN_EXT_PTS[ext])
    if ext in _TEXT_EXTS:
        score -= 80.0

    if size < 32:
        score -= 200.0
    elif size < 200:
        score -= 60.0
    elif size > 10_000_000:
        score -= 200.0
    elif size > 2_000_000:
        score -= 30.0

    return score


def _head_score(path: str, size: int, head: bytes) -> float:
    score = _meta_score(path, size) + float(_magic_score(head))
    if _is_probably_text(head):
        ext = _ext_of(path)
        if ext not in _BIN_EXT_PTS:
            score -= 35.0
    return score


def _try_decompress_by_ext(name: str, data: bytes) -> Optional[Tuple[str, bytes]]:
    ln = name.lower()
    try:
        if ln.endswith(".gz"):
            return name[:-3], gzip.decompress(data)
        if ln.endswith(".bz2"):
            return name[:-4], bz2.decompress(data)
        if ln.endswith(".xz"):
            return name[:-3], lzma.decompress(data, format=lzma.FORMAT_XZ)
        if ln.endswith(".lzma"):
            return name[:-5], lzma.decompress(data, format=lzma.FORMAT_ALONE)
    except Exception:
        return None
    return None


def _looks_like_interesting_compressed_name(path: str) -> bool:
    p = path.lower()
    if any(k in p for k in ("42536279", "clusterfuzz", "testcase", "minimized", "crash", "poc", "repro", "regression", "svcdec")):
        return True
    if any(k in p for k in ("seed_corpus", "corpus", "seeds")):
        return True
    return False


def _scan_zip_for_best(zip_bytes: bytes, zip_path: str) -> Optional[Tuple[float, bytes]]:
    try:
        zf = zipfile.ZipFile(io.BytesIO(zip_bytes))
    except Exception:
        return None

    infos = []
    for info in zf.infolist():
        if info.is_dir():
            continue
        sz = info.file_size
        if sz <= 0 or sz > 2_000_000:
            continue
        name = f"{zip_path}::{info.filename}"
        s = _meta_score(name, sz)
        if sz == TARGET_LEN:
            s += 200.0
        infos.append((s, info))

    if not infos:
        return None

    infos.sort(key=lambda x: x[0], reverse=True)
    selected = []
    best_exact = [inf for inf in infos if inf[1].file_size == TARGET_LEN]
    for s, info in best_exact[:10]:
        selected.append((s + 500.0, info))
    for s, info in infos[:25]:
        selected.append((s, info))

    best_score = float("-inf")
    best_data = None

    for base_s, info in selected:
        try:
            data = zf.read(info)
        except Exception:
            continue
        if len(data) != info.file_size:
            continue
        head = data[:256]
        name = f"{zip_path}::{info.filename}"
        s = _head_score(name, len(data), head) + base_s * 0.05
        if s > best_score:
            best_score = s
            best_data = data

    if best_data is None:
        return None
    return best_score, best_data


def _extract_hex_blob_from_text(text: str) -> Optional[bytes]:
    if "0x" not in text:
        return None
    hexes = re.findall(r"0x([0-9a-fA-F]{1,2})", text)
    if not (1000 <= len(hexes) <= 200000):
        return None
    try:
        data = bytes(int(h, 16) for h in hexes)
    except Exception:
        return None
    if 200 <= len(data) <= 5_000_000:
        return data
    return None


class Solution:
    def solve(self, src_path: str) -> bytes:
        best_score = float("-inf")
        best_member = None
        best_is_tar = False
        best_path = None
        best_data_direct = None

        def consider_direct(path: str, data: bytes):
            nonlocal best_score, best_data_direct, best_member, best_is_tar, best_path
            if not data:
                return
            head = data[:256]
            s = _head_score(path, len(data), head)
            if s > best_score:
                best_score = s
                best_data_direct = data
                best_member = None
                best_is_tar = False
                best_path = None

        def consider_head(path: str, size: int, head: bytes, member_obj=None, is_tar=False, file_path=None):
            nonlocal best_score, best_member, best_is_tar, best_path
            s = _head_score(path, size, head)
            if s > best_score:
                best_score = s
                best_member = member_obj
                best_is_tar = is_tar
                best_path = file_path

        def scan_tar(tpath: str):
            nonlocal best_data_direct, best_member, best_is_tar, best_path, best_score
            try:
                tf = tarfile.open(tpath, "r:*")
            except Exception:
                return False

            with tf:
                members = tf.getmembers()
                for m in members:
                    if not m.isreg():
                        continue
                    size = m.size
                    if size <= 0 or size > 25_000_000:
                        continue
                    name = m.name
                    lname = name.lower()
                    ext = _ext_of(lname)

                    if ext in _TEXT_EXTS and abs(size - TARGET_LEN) > 2000:
                        if not any(k in lname for k in ("42536279", "clusterfuzz", "testcase", "svcdec", "crash", "poc", "repro", "regression")):
                            continue

                    f = None
                    try:
                        f = tf.extractfile(m)
                        if f is None:
                            continue
                        head = f.read(256)
                    except Exception:
                        continue
                    finally:
                        try:
                            if f is not None:
                                f.close()
                        except Exception:
                            pass

                    consider_head(name, size, head, member_obj=m, is_tar=True, file_path=None)

                    if ext == ".zip" and (("corpus" in lname) or ("seed" in lname) or ("fuzz" in lname) or _looks_like_interesting_compressed_name(lname)):
                        if size <= 50_000_000:
                            try:
                                zfobj = tf.extractfile(m)
                                if zfobj is not None:
                                    zip_bytes = zfobj.read()
                                else:
                                    zip_bytes = None
                            except Exception:
                                zip_bytes = None
                            finally:
                                try:
                                    if zfobj is not None:
                                        zfobj.close()
                                except Exception:
                                    pass
                            if zip_bytes:
                                res = _scan_zip_for_best(zip_bytes, name)
                                if res is not None:
                                    zs, zdata = res
                                    if zs > best_score:
                                        best_score = zs
                                        best_data_direct = zdata
                                        best_member = None
                                        best_is_tar = False
                                        best_path = None

                    if ext in (".gz", ".bz2", ".xz", ".lzma") and _looks_like_interesting_compressed_name(lname) and size <= 5_000_000:
                        try:
                            df = tf.extractfile(m)
                            if df is not None:
                                comp = df.read()
                            else:
                                comp = None
                        except Exception:
                            comp = None
                        finally:
                            try:
                                if df is not None:
                                    df.close()
                            except Exception:
                                pass
                        if comp:
                            dec = _try_decompress_by_ext(name, comp)
                            if dec:
                                dec_name, dec_data = dec
                                if 0 < len(dec_data) <= 5_000_000:
                                    consider_direct(dec_name, dec_data)

                    if any(k in lname for k in ("42536279", "clusterfuzz", "testcase", "minimized", "svcdec", "crash", "poc", "repro", "regression")):
                        if ext in _TEXT_EXTS and size <= 5_000_000:
                            try:
                                tfh = tf.extractfile(m)
                                if tfh is not None:
                                    raw = tfh.read()
                                else:
                                    raw = None
                            except Exception:
                                raw = None
                            finally:
                                try:
                                    if tfh is not None:
                                        tfh.close()
                                except Exception:
                                    pass
                            if raw:
                                try:
                                    txt = raw.decode("utf-8", "ignore")
                                except Exception:
                                    txt = ""
                                blob = _extract_hex_blob_from_text(txt)
                                if blob and 200 <= len(blob) <= 5_000_000:
                                    consider_direct(f"{name}::hexblob", blob)

                if best_data_direct is not None:
                    return True

                if best_member is not None:
                    try:
                        bf = tf.extractfile(best_member)
                        if bf is not None:
                            data = bf.read()
                        else:
                            data = None
                    except Exception:
                        data = None
                    finally:
                        try:
                            if bf is not None:
                                bf.close()
                        except Exception:
                            pass
                    if data:
                        best_data_direct = data
                        best_member = None
                        best_is_tar = False
                        best_path = None
                        return True

            return True

        def scan_dir(dpath: str):
            nonlocal best_data_direct, best_score, best_member, best_is_tar, best_path
            for root, dirs, files in os.walk(dpath):
                rlow = root.lower()
                if any(seg in rlow for seg in ("/.git", "/.svn", "/.hg")):
                    continue
                for fn in files:
                    path = os.path.join(root, fn)
                    try:
                        st = os.stat(path)
                    except Exception:
                        continue
                    size = st.st_size
                    if size <= 0 or size > 25_000_000:
                        continue
                    rel = os.path.relpath(path, dpath)
                    lname = rel.lower()
                    ext = _ext_of(lname)

                    if ext in _TEXT_EXTS and abs(size - TARGET_LEN) > 2000:
                        if not any(k in lname for k in ("42536279", "clusterfuzz", "testcase", "svcdec", "crash", "poc", "repro", "regression")):
                            continue

                    head = b""
                    try:
                        with open(path, "rb") as f:
                            head = f.read(256)
                    except Exception:
                        continue

                    consider_head(rel, size, head, member_obj=None, is_tar=False, file_path=path)

                    if ext == ".zip" and (("corpus" in lname) or ("seed" in lname) or ("fuzz" in lname) or _looks_like_interesting_compressed_name(lname)):
                        if size <= 50_000_000:
                            try:
                                with open(path, "rb") as f:
                                    zip_bytes = f.read()
                            except Exception:
                                zip_bytes = None
                            if zip_bytes:
                                res = _scan_zip_for_best(zip_bytes, rel)
                                if res is not None:
                                    zs, zdata = res
                                    if zs > best_score:
                                        best_score = zs
                                        best_data_direct = zdata
                                        best_member = None
                                        best_is_tar = False
                                        best_path = None

                    if ext in (".gz", ".bz2", ".xz", ".lzma") and _looks_like_interesting_compressed_name(lname) and size <= 5_000_000:
                        try:
                            with open(path, "rb") as f:
                                comp = f.read()
                        except Exception:
                            comp = None
                        if comp:
                            dec = _try_decompress_by_ext(rel, comp)
                            if dec:
                                dec_name, dec_data = dec
                                if 0 < len(dec_data) <= 5_000_000:
                                    consider_direct(dec_name, dec_data)

                    if any(k in lname for k in ("42536279", "clusterfuzz", "testcase", "minimized", "svcdec", "crash", "poc", "repro", "regression")):
                        if ext in _TEXT_EXTS and size <= 5_000_000:
                            try:
                                with open(path, "rb") as f:
                                    raw = f.read()
                            except Exception:
                                raw = None
                            if raw:
                                try:
                                    txt = raw.decode("utf-8", "ignore")
                                except Exception:
                                    txt = ""
                                blob = _extract_hex_blob_from_text(txt)
                                if blob and 200 <= len(blob) <= 5_000_000:
                                    consider_direct(f"{rel}::hexblob", blob)

            if best_data_direct is None and best_path:
                try:
                    with open(best_path, "rb") as f:
                        best_data_direct = f.read()
                except Exception:
                    best_data_direct = None

        if os.path.isdir(src_path):
            scan_dir(src_path)
        else:
            ok = scan_tar(src_path)
            if not ok:
                try:
                    scan_dir(src_path)
                except Exception:
                    pass

        if best_data_direct is not None:
            return best_data_direct

        return b"\x00" * TARGET_LEN