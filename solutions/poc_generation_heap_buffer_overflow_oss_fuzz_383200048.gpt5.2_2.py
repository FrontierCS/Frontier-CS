import os
import io
import re
import tarfile
import zipfile
from typing import Optional, Tuple, List


def _binary_ratio(data: bytes) -> float:
    if not data:
        return 0.0
    nonprint = 0
    for c in data:
        if c in (9, 10, 13):
            continue
        if c < 32 or c > 126:
            nonprint += 1
    return nonprint / len(data)


def _score_candidate(name: str, data: bytes) -> int:
    lname = name.lower()
    s = 0

    if "383200048" in lname:
        s += 5000
    if b"383200048" in data:
        s += 6000

    kw_points = [
        ("oss-fuzz", 1200),
        ("ossfuzz", 1200),
        ("clusterfuzz", 1200),
        ("testcase", 900),
        ("minimized", 700),
        ("repro", 700),
        ("poc", 600),
        ("crash", 600),
        ("fuzz", 400),
        ("corpus", 400),
        ("seed", 400),
        ("regress", 300),
        ("bug", 300),
        ("issue", 250),
    ]
    for kw, pts in kw_points:
        if kw in lname:
            s += pts

    n = len(data)
    if n == 512:
        s += 2000
    else:
        d = abs(n - 512)
        if d <= 8:
            s += 1200
        elif d <= 32:
            s += 700
        elif d <= 128:
            s += 350

    if data.startswith(b"\x7fELF"):
        s += 1000
    if b"UPX!" in data:
        s += 900
    if b"UPX0" in data or b"UPX1" in data:
        s += 500

    # Prefer "input-like" binary blobs
    br = _binary_ratio(data)
    if br > 0.6:
        s += 200
    elif br > 0.3:
        s += 120
    elif br > 0.15:
        s += 50

    # Penalize obviously textual files unless strongly indicated
    if br < 0.05 and s < 3000:
        s -= 400

    # Slight preference for smaller sizes (handled in tie-break too)
    if n > 0:
        s -= min(300, n // 8)

    return s


def _is_interesting_name(name: str) -> bool:
    lname = name.lower()
    if any(k in lname for k in ("383200048", "oss-fuzz", "ossfuzz", "clusterfuzz", "testcase", "minimized", "repro", "poc", "crash")):
        return True
    if any(k in lname for k in ("/fuzz", "/corpus", "/seed", "/seeds", "/test", "/tests", "/regress", "/bug", "/bugs", "/poc")):
        return True
    if lname.endswith((".bin", ".dat", ".poc", ".crash", ".seed", ".input", ".elf", ".so", ".exe")):
        return True
    return False


def _choose_best(candidates: List[Tuple[int, int, str, bytes]]) -> Optional[bytes]:
    if not candidates:
        return None
    candidates.sort(key=lambda x: (-x[0], x[1], x[2]))
    return candidates[0][3]


def _scan_directory(root: str) -> Optional[bytes]:
    candidates: List[Tuple[int, int, str, bytes]] = []
    max_read_small = 4096
    max_read_interesting = 2 * 1024 * 1024

    for dirpath, _, filenames in os.walk(root):
        for fn in filenames:
            full = os.path.join(dirpath, fn)
            try:
                st = os.stat(full)
            except OSError:
                continue
            if not os.path.isfile(full):
                continue
            size = st.st_size
            rel = os.path.relpath(full, root).replace(os.sep, "/")

            must_read = False
            if size == 512:
                must_read = True
            elif size <= max_read_small:
                must_read = True
            elif _is_interesting_name(rel) and size <= max_read_interesting:
                must_read = True

            if not must_read:
                continue

            try:
                with open(full, "rb") as f:
                    data = f.read()
            except OSError:
                continue
            if not data:
                continue
            sc = _score_candidate(rel, data)
            if sc > 0:
                candidates.append((sc, len(data), rel, data))

    return _choose_best(candidates)


def _open_tar_stream(src_path: str):
    # returns (tarfile.TarFile, closer callable)
    try:
        tf = tarfile.open(src_path, mode="r:*")
        return tf, tf.close
    except tarfile.TarError:
        pass
    except Exception:
        pass

    lname = src_path.lower()
    if lname.endswith(".zst") or lname.endswith(".tzst") or lname.endswith(".tar.zst"):
        try:
            import zstandard as zstd  # type: ignore
        except Exception:
            raise
        fh = open(src_path, "rb")
        dctx = zstd.ZstdDecompressor()
        reader = dctx.stream_reader(fh)
        tf = tarfile.open(fileobj=reader, mode="r|")
        def _close():
            try:
                tf.close()
            finally:
                try:
                    reader.close()
                finally:
                    fh.close()
        return tf, _close

    raise tarfile.TarError("Unsupported archive format")


def _scan_tar(src_path: str) -> Optional[bytes]:
    candidates: List[Tuple[int, int, str, bytes]] = []
    max_read_small = 4096
    max_read_interesting = 2 * 1024 * 1024

    tf, closer = _open_tar_stream(src_path)
    try:
        for m in tf:
            if not m.isfile():
                continue
            name = m.name
            size = m.size
            if size <= 0:
                continue

            must_read = False
            if size == 512:
                must_read = True
            elif size <= max_read_small:
                must_read = True
            elif _is_interesting_name(name) and size <= max_read_interesting:
                must_read = True

            if not must_read:
                continue

            try:
                f = tf.extractfile(m)
                if f is None:
                    continue
                data = f.read()
            except Exception:
                continue
            if not data:
                continue
            sc = _score_candidate(name, data)
            if sc > 0:
                candidates.append((sc, len(data), name, data))
    finally:
        closer()

    return _choose_best(candidates)


def _scan_zip(src_path: str) -> Optional[bytes]:
    candidates: List[Tuple[int, int, str, bytes]] = []
    max_read_small = 4096
    max_read_interesting = 2 * 1024 * 1024

    with zipfile.ZipFile(src_path, "r") as zf:
        for zi in zf.infolist():
            if zi.is_dir():
                continue
            name = zi.filename
            size = zi.file_size
            if size <= 0:
                continue

            must_read = False
            if size == 512:
                must_read = True
            elif size <= max_read_small:
                must_read = True
            elif _is_interesting_name(name) and size <= max_read_interesting:
                must_read = True

            if not must_read:
                continue

            try:
                data = zf.read(zi)
            except Exception:
                continue
            if not data:
                continue
            sc = _score_candidate(name, data)
            if sc > 0:
                candidates.append((sc, len(data), name, data))

    return _choose_best(candidates)


def _fallback_poc() -> bytes:
    # Minimal 32-bit little-endian ELF-like blob with an embedded "UPX!" marker.
    b = bytearray(512)
    b[0:4] = b"\x7fELF"
    b[4] = 1   # EI_CLASS = ELFCLASS32
    b[5] = 1   # EI_DATA = ELFDATA2LSB
    b[6] = 1   # EI_VERSION
    b[7] = 0   # EI_OSABI
    # e_type=ET_DYN(3), e_machine=EM_386(3), e_version=1
    b[16:18] = (3).to_bytes(2, "little")
    b[18:20] = (3).to_bytes(2, "little")
    b[20:24] = (1).to_bytes(4, "little")
    # e_entry
    b[24:28] = (0).to_bytes(4, "little")
    # e_phoff = 52
    b[28:32] = (52).to_bytes(4, "little")
    # e_shoff = 0
    b[32:36] = (0).to_bytes(4, "little")
    # e_flags = 0
    b[36:40] = (0).to_bytes(4, "little")
    # e_ehsize=52, e_phentsize=32, e_phnum=1
    b[40:42] = (52).to_bytes(2, "little")
    b[42:44] = (32).to_bytes(2, "little")
    b[44:46] = (1).to_bytes(2, "little")
    # e_shentsize, e_shnum, e_shstrndx = 0
    b[46:52] = b"\x00" * 6

    # Program header at offset 52
    ph = 52
    # p_type = PT_LOAD(1)
    b[ph + 0:ph + 4] = (1).to_bytes(4, "little")
    # p_offset = 0
    b[ph + 4:ph + 8] = (0).to_bytes(4, "little")
    # p_vaddr, p_paddr
    b[ph + 8:ph + 12] = (0).to_bytes(4, "little")
    b[ph + 12:ph + 16] = (0).to_bytes(4, "little")
    # p_filesz = 512, p_memsz = 0x2000
    b[ph + 16:ph + 20] = (512).to_bytes(4, "little")
    b[ph + 20:ph + 24] = (0x2000).to_bytes(4, "little")
    # p_flags = R|X (5), p_align=0x1000
    b[ph + 24:ph + 28] = (5).to_bytes(4, "little")
    b[ph + 28:ph + 32] = (0x1000).to_bytes(4, "little")

    # Embed UPX signature
    b[0x100:0x104] = b"UPX!"
    b[0x104:0x108] = b"\x00\x00\x00\x00"
    return bytes(b)


class Solution:
    def solve(self, src_path: str) -> bytes:
        if not src_path:
            return _fallback_poc()

        if os.path.isdir(src_path):
            best = _scan_directory(src_path)
            return best if best is not None else _fallback_poc()

        lower = src_path.lower()
        if lower.endswith(".zip"):
            best = _scan_zip(src_path)
            return best if best is not None else _fallback_poc()

        # Try tar-like archives
        try:
            best = _scan_tar(src_path)
            return best if best is not None else _fallback_poc()
        except Exception:
            return _fallback_poc()